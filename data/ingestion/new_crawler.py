from __future__ import annotations

import concurrent.futures
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup


VN_TZ = "Asia/Ho_Chi_Minh"
REQUEST_TIMEOUT = 5
MAX_RUN_SECONDS = 18
SOURCE_QUORUM = 2

SOURCES = {
    "ketqua16": [
        "https://ketqua16.net/",
        "https://ketqua16.net/so-ket-qua",
    ],
    "xsmb": [
        "https://www.xsmb.com.vn/so-ket-qua-xsmb",
    ],
}

EXPECTED_COUNTS = (1, 1, 2, 6, 4, 6, 3, 4)
DATE_RE = re.compile(r"(?<!\\d)(\\d{1,2})[-/.](\\d{1,2})[-/.](\\d{4})(?!\\d)")
NUMBER_RE = re.compile(r"(?<!\\d)(\\d{2,5})(?!\\d)")


@dataclass(frozen=True)
class Result:
    source: str
    draw_date: str
    full_prizes: tuple[str, ...]
    tails27: tuple[int, ...]
    source_url: str
    html_sha256: str


def _normal_date(value: str) -> str | None:
    m = DATE_RE.search(value or "")
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        dt = date(y, mth, d)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def _tail27(values: Iterable[str]) -> tuple[str, ...] | None:
    vals = tuple(str(v).strip() for v in values)
    if len(vals) != 27 or any(not re.fullmatch(r"\\d{2,5}", v) for v in vals):
        return None
    return tuple(vals)


def _table_result(table: BeautifulSoup) -> tuple[str, ...] | None:
    rows: dict[int, list[str]] = {}
    names = {
        "đb": 0, "db": 0, "đặc biệt": 0, "giải đặc biệt": 0,
        "g1": 1, "g2": 2, "g3": 3, "g4": 4, "g5": 5, "g6": 6, "g7": 7,
        "giải 1": 1, "giải 2": 2, "giải 3": 3, "giải 4": 4,
        "giải 5": 5, "giải 6": 6, "giải 7": 7,
        "giải nhất": 1, "giải nhì": 2, "giải ba": 3, "giải tư": 4,
        "giải năm": 5, "giải sáu": 6, "giải bảy": 7,
    }
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = " ".join(cells[0].stripped_strings).strip().lower()
        label = re.sub(r"\\s+", " ", label)
        idx = names.get(label)
        if idx is None:
            m = re.search(r"(?:g|giải)\\s*[.:]?\\s*([1-7])\\b", label)
            idx = int(m.group(1)) if m else None
        if idx is None:
            continue
        vals: list[str] = []
        for cell in cells[1:]:
            vals.extend(NUMBER_RE.findall(" ".join(cell.stripped_strings)))
        if len(vals) == EXPECTED_COUNTS[idx]:
            rows[idx] = vals
    if set(rows) != set(range(8)):
        return None
    ordered = [v for i in range(8) for v in rows[i]]
    return _tail27(ordered)


def _parse_html(source: str, url: str, body: bytes) -> list[Result]:
    soup = BeautifulSoup(body, "html.parser")
    html_sha = hashlib.sha256(body).hexdigest()
    out: list[Result] = []
    for table in soup.find_all("table"):
        table_text = " ".join(table.stripped_strings)
        dates = DATE_RE.findall(table_text)
        if not dates:
            continue
        draw_date = _normal_date("/".join(dates[0]))
        if not draw_date:
            continue
        parsed = _table_result(table)
        if parsed is None:
            continue
        out.append(Result(
            source=source,
            draw_date=draw_date,
            full_prizes=parsed,
            tails27=tuple(int(v[-2:]) for v in parsed),
            source_url=url,
            html_sha256=html_sha,
        ))
    return out


def _fetch_source(source: str, urls: list[str]) -> list[Result]:
    headers = {
        "User-Agent": "Mozilla/5.0 XSMB-Quant-Crawler/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    for url in urls:
        started = time.monotonic()
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                continue
            rows = _parse_html(source, url, response.content)
            if rows:
                print(f"[NEW-CRAWLER] source={source} url={url} rows={len(rows)} ms={int((time.monotonic()-started)*1000)}", flush=True)
                return rows
        except requests.RequestException as exc:
            print(f"[NEW-CRAWLER] source={source} url={url} error={type(exc).__name__}", flush=True)
    return []


def _consensus(rows: list[Result]) -> dict[str, dict]:
    votes: dict[str, dict[tuple[int, ...], set[str]]] = {}
    raw: dict[tuple[str, str], Result] = {}
    for row in rows:
        votes.setdefault(row.draw_date, {}).setdefault(row.tails27, set()).add(row.source)
        raw[(row.draw_date, row.source)] = row
    out: dict[str, dict] = {}
    for draw_date, variants in votes.items():
        eligible = [(tails, sources) for tails, sources in variants.items() if len(sources) >= SOURCE_QUORUM]
        if len(eligible) != 1:
            continue
        tails, sources = eligible[0]
        full = next(raw[(draw_date, src)].full_prizes for src in sorted(sources))
        out[draw_date] = {
            "date": draw_date,
            "full_27": list(full),
            "tails27": list(tails),
            "sources": sorted(sources),
        }
    return out


def crawl(days: int = 3) -> tuple[dict[str, dict], dict]:
    """Fresh two-source crawler. No legacy crawler/database code is used."""
    started = time.monotonic()
    cutoff = __import__('datetime').datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    futures = {pool.submit(_fetch_source, source, urls): source for source, urls in SOURCES.items()}
    rows: list[Result] = []
    done, _pending = concurrent.futures.wait(futures, timeout=MAX_RUN_SECONDS)
    for future in done:
        try:
            rows.extend(future.result())
        except Exception as exc:
            print(f"[NEW-CRAWLER] worker={futures[future]} error={type(exc).__name__}:{exc}", flush=True)
    pool.shutdown(wait=False, cancel_futures=True)
    cutoff_date = cutoff - timedelta(days=max(1, int(days)) - 1)
    rows = [r for r in rows if cutoff_date <= date.fromisoformat(r.draw_date) <= cutoff]
    data = _consensus(rows)
    errors = {
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "records": len(rows),
        "dates": len(data),
        "sources": sorted({r.source for r in rows}),
        "quorum": SOURCE_QUORUM,
    }
    print(f"[NEW-CRAWLER] DONE records={len(rows)} dates={len(data)} sources={errors['sources']} elapsed_ms={errors['elapsed_ms']}", flush=True)
    return data, errors
