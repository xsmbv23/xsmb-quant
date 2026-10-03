from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import PurePosixPath

try:
    import dropbox
    from dropbox.files import WriteMode
except Exception:
    dropbox = None
    WriteMode = None

ROOT_ENV = "DROPBOX_ROOT"
TOKEN_ENV = "DROPBOX_ACCESS_TOKEN"
REFRESH_ENV = "DROPBOX_REFRESH_TOKEN"
APP_KEY_ENV = "DROPBOX_APP_KEY"
APP_SECRET_ENV = "DROPBOX_APP_SECRET"
DEFAULT_ROOT = "/Data goc/XSMB_QUANT"


class CrawlDatabase:
    """Dropbox-backed durable evidence store."""

    @classmethod
    def enabled(cls) -> bool:
        if dropbox is None:
            return False
        if os.getenv(TOKEN_ENV):
            return True
        return bool(os.getenv(REFRESH_ENV) and os.getenv(APP_KEY_ENV) and os.getenv(APP_SECRET_ENV))

    @classmethod
    def _root(cls) -> str:
        return (os.getenv(ROOT_ENV) or DEFAULT_ROOT).rstrip("/")

    @classmethod
    def _client(cls):
        if not cls.enabled():
            raise RuntimeError("DROPBOX_NOT_CONFIGURED")
        token = os.getenv(TOKEN_ENV)
        if token:
            return dropbox.Dropbox(token)
        return dropbox.Dropbox(
            oauth2_refresh_token=os.environ[REFRESH_ENV],
            app_key=os.environ[APP_KEY_ENV],
            app_secret=os.environ[APP_SECRET_ENV],
        )

    @classmethod
    def _mkdir(cls, dbx, path: str) -> None:
        parts = [p for p in PurePosixPath(path).parts if p not in ("/", "")]
        current = ""
        for part in parts:
            current += "/" + part
            try:
                dbx.files_create_folder_v2(current, autorename=False)
            except Exception as exc:
                if "conflict" not in str(exc).lower():
                    raise

    @classmethod
    def _put_json(cls, dbx, path: str, payload) -> None:
        cls._mkdir(dbx, str(PurePosixPath(path).parent))
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        dbx.files_upload(body, path, mode=WriteMode.overwrite, mute=True)

    @classmethod
    def _get_json(cls, dbx, path: str):
        try:
            _, response = dbx.files_download(path)
        except Exception:
            return None
        return json.loads(response.content.decode("utf-8"))

    @classmethod
    def ensure_schema(cls) -> bool:
        if not cls.enabled():
            return False
        dbx = cls._client()
        cls._mkdir(dbx, cls._root())
        for child in ("CRAWL_RAW", "CANONICAL", "MANIFEST"):
            cls._mkdir(dbx, f"{cls._root()}/{child}")
        return True

    @classmethod
    def persist_crawl(cls, records, errors: list[dict], consensus: list[dict], conflicts: dict) -> bool:
        if not cls.enabled():
            return False
        records = list(records)
        cls.ensure_schema()
        dbx = cls._client()
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")
        root = cls._root()
        for rec in records:
            draw_date = str(rec.draw_date)
            source = str(rec.source_id)
            fingerprint = str(rec.table_fingerprint or "unknown")
            path = f"{root}/CRAWL_RAW/{draw_date}/{source}/{fingerprint}.json"
            cls._put_json(dbx, path, {
                "run_id": run_id,
                "draw_date": draw_date,
                "source_id": source,
                "full_prizes": list(rec.full_prizes),
                "tails27": list(rec.tails27),
                "source_url": rec.source_url,
                "source_html_sha256": rec.source_html_sha256,
                "table_fingerprint": fingerprint,
                "raw_artifact_path": rec.raw_artifact_path,
                "fetched_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            })
        if errors:
            cls._put_json(dbx, f"{root}/CRAWL_RAW/{run_id}/errors.json", errors)

        canonical = cls._get_json(dbx, f"{root}/CANONICAL/canonical.json")
        if not isinstance(canonical, dict):
            canonical = {}
        for row in consensus:
            canonical[row["date"]] = {
                "date": row["date"],
                "full_prizes": list(row["full_27"]),
                "tails27": [int(v[-2:]) for v in row["full_27"]],
                "source_set": sorted(row["sources"]),
                "calendar_state": "DRAW_CONFIRMED",
                "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
        cls._put_json(dbx, f"{root}/CANONICAL/canonical.json", canonical)
        cls._put_json(dbx, f"{root}/MANIFEST/latest.json", {
            "run_id": run_id,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "records_count": len(records),
            "errors_count": len(errors),
            "conflicts_count": len(conflicts),
            "canonical_dates": len(canonical),
        })
        return True

    @classmethod
    def load_canonical(cls) -> dict:
        if not cls.enabled():
            return {}
        dbx = cls._client()
        payload = cls._get_json(dbx, f"{cls._root()}/CANONICAL/canonical.json")
        if not isinstance(payload, dict):
            return {}
        db = {}
        for date_str, row in payload.items():
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                continue
            tails = [int(x) for x in row.get("tails27", [])]
            if len(tails) != 27:
                continue
            db[dt.strftime("%d/%m/%Y")] = {
                "date_obj": dt,
                "prizes_int": tails,
                "raw_str": " ".join(f"{x:02d}" for x in tails),
                "calendar_state": row.get("calendar_state", "DRAW_CONFIRMED"),
                "source_set": list(row.get("source_set", [])),
            }
        return db

    @classmethod
    def seed_from_db_rows(cls, rows: list[dict]) -> int:
        if not cls.enabled() or not rows:
            return 0
        cls.ensure_schema()
        dbx = cls._client()
        path = f"{cls._root()}/CANONICAL/canonical.json"
        canonical = cls._get_json(dbx, path)
        if not isinstance(canonical, dict):
            canonical = {}
        inserted = 0
        for row in rows:
            dt = row["date_obj"]
            tails = [int(x) for x in row["prizes_int"]]
            if len(tails) != 27:
                continue
            key = dt.strftime("%Y-%m-%d")
            if key in canonical:
                continue
            canonical[key] = {
                "date": key,
                "full_prizes": [f"{x:02d}" for x in tails],
                "tails27": tails,
                "source_set": row.get("source_set") or ["legacy_excel"],
                "calendar_state": row.get("calendar_state") or "DRAW_CONFIRMED",
                "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
            inserted += 1
        cls._put_json(dbx, path, canonical)
        return inserted
