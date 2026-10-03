from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Iterable

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None

DATABASE_URL_ENV = "CRAWL_DATABASE_URL"


class CrawlDatabase:
    """Durable store for raw two-source crawl evidence and canonical results."""

    @classmethod
    def enabled(cls) -> bool:
        return bool(os.getenv(DATABASE_URL_ENV)) and psycopg is not None

    @classmethod
    def connect(cls):
        if not cls.enabled():
            raise RuntimeError("CRAWL_DATABASE_NOT_CONFIGURED")
        return psycopg.connect(os.environ[DATABASE_URL_ENV], connect_timeout=5)

    @classmethod
    def ensure_schema(cls) -> bool:
        if not cls.enabled():
            return False
        ddl = """
        CREATE TABLE IF NOT EXISTS crawl_runs (
            id BIGSERIAL PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL,
            records_count INTEGER NOT NULL DEFAULT 0,
            errors_count INTEGER NOT NULL DEFAULT 0,
            conflicts_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS source_records (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT REFERENCES crawl_runs(id) ON DELETE SET NULL,
            draw_date DATE NOT NULL,
            source_id TEXT NOT NULL,
            full_prizes JSONB NOT NULL,
            tails27 JSONB NOT NULL,
            source_url TEXT NOT NULL,
            source_html_sha256 TEXT NOT NULL,
            table_fingerprint TEXT NOT NULL,
            raw_artifact_path TEXT,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(draw_date, source_id, table_fingerprint)
        );
        CREATE INDEX IF NOT EXISTS idx_source_records_date ON source_records(draw_date);
        CREATE INDEX IF NOT EXISTS idx_source_records_source_date ON source_records(source_id, draw_date);

        CREATE TABLE IF NOT EXISTS crawl_errors (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT REFERENCES crawl_runs(id) ON DELETE SET NULL,
            draw_date DATE,
            source_id TEXT,
            error TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS canonical_results (
            draw_date DATE PRIMARY KEY,
            full_prizes JSONB NOT NULL,
            tails27 JSONB NOT NULL,
            source_set JSONB NOT NULL,
            calendar_state TEXT NOT NULL DEFAULT 'DRAW_CONFIRMED',
            first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_canonical_results_date ON canonical_results(draw_date);
        """
        with cls.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()
        return True

    @classmethod
    def persist_crawl(cls, records: Iterable, errors: list[dict], consensus: list[dict], conflicts: dict) -> bool:
        if not cls.enabled():
            return False
        cls.ensure_schema()
        records = list(records)
        with cls.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO crawl_runs(status, records_count, errors_count, conflicts_count) "
                    "VALUES (%s,%s,%s,%s) RETURNING id",
                    ("RUNNING", len(records), len(errors), len(conflicts)),
                )
                run_id = cur.fetchone()[0]
                for rec in records:
                    cur.execute(
                        """
                        INSERT INTO source_records(
                            run_id, draw_date, source_id, full_prizes, tails27,
                            source_url, source_html_sha256, table_fingerprint, raw_artifact_path
                        )
                        VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
                        ON CONFLICT (draw_date, source_id, table_fingerprint) DO UPDATE SET
                            run_id=EXCLUDED.run_id,
                            source_url=EXCLUDED.source_url,
                            source_html_sha256=EXCLUDED.source_html_sha256,
                            raw_artifact_path=EXCLUDED.raw_artifact_path,
                            fetched_at=now()
                        """,
                        (
                            run_id, rec.draw_date, rec.source_id,
                            json.dumps(list(rec.full_prizes)),
                            json.dumps(list(rec.tails27)),
                            rec.source_url, rec.source_html_sha256,
                            rec.table_fingerprint, rec.raw_artifact_path,
                        ),
                    )
                for err in errors:
                    cur.execute(
                        "INSERT INTO crawl_errors(run_id, draw_date, source_id, error) VALUES (%s,%s,%s,%s)",
                        (run_id, err.get("date"), err.get("source_id"), err.get("error", "UNKNOWN")),
                    )
                for row in consensus:
                    cur.execute(
                        """
                        INSERT INTO canonical_results(
                            draw_date, full_prizes, tails27, source_set,
                            calendar_state, last_seen_at, updated_at
                        )
                        VALUES (%s,%s::jsonb,%s::jsonb,%s::jsonb,'DRAW_CONFIRMED',now(),now())
                        ON CONFLICT (draw_date) DO UPDATE SET
                            full_prizes=EXCLUDED.full_prizes,
                            tails27=EXCLUDED.tails27,
                            source_set=EXCLUDED.source_set,
                            calendar_state='DRAW_CONFIRMED',
                            last_seen_at=now(),
                            updated_at=now()
                        """,
                        (
                            row["date"],
                            json.dumps(list(row["full_27"])),
                            json.dumps([int(v[-2:]) for v in row["full_27"]]),
                            json.dumps(list(row["sources"])),
                        ),
                    )
                cur.execute(
                    "UPDATE crawl_runs SET status=%s, finished_at=now() WHERE id=%s",
                    ("COMPLETE", run_id),
                )
            conn.commit()
        return True

    @classmethod
    def load_canonical(cls) -> dict:
        if not cls.enabled():
            return {}
        cls.ensure_schema()
        db = {}
        with cls.connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT draw_date, tails27, source_set, calendar_state "
                    "FROM canonical_results ORDER BY draw_date"
                )
                for row in cur.fetchall():
                    dt = row["draw_date"]
                    key = dt.strftime("%d/%m/%Y")
                    tails = [int(x) for x in row["tails27"]]
                    db[key] = {
                        "date_obj": datetime(dt.year, dt.month, dt.day),
                        "prizes_int": tails,
                        "raw_str": " ".join(f"{x:02d}" for x in tails),
                        "calendar_state": row["calendar_state"],
                        "source_set": list(row["source_set"] or []),
                    }
        return db

    @classmethod
    def seed_from_db_rows(cls, rows: list[dict]) -> int:
        """One-time migration of the existing 27-tail Excel history."""
        if not cls.enabled() or not rows:
            return 0
        cls.ensure_schema()
        inserted = 0
        with cls.connect() as conn:
            with conn.cursor() as cur:
                for row in rows:
                    dt = row["date_obj"]
                    tails = [int(x) for x in row["prizes_int"]]
                    if len(tails) != 27:
                        continue
                    full = [f"{x:02d}" for x in tails]
                    cur.execute(
                        """
                        INSERT INTO canonical_results(
                            draw_date, full_prizes, tails27, source_set, calendar_state
                        )
                        VALUES (%s,%s::jsonb,%s::jsonb,%s::jsonb,%s)
                        ON CONFLICT (draw_date) DO NOTHING
                        """,
                        (
                            dt.date(), json.dumps(full), json.dumps(tails),
                            json.dumps(row.get("source_set") or ["legacy_excel"]),
                            row.get("calendar_state") or "DRAW_CONFIRMED",
                        ),
                    )
                    inserted += cur.rowcount
            conn.commit()
        return inserted
