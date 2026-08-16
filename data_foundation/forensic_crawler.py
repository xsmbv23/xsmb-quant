from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import requests
from bs4 import BeautifulSoup

EXPECTED = (1, 1, 2, 6, 4, 6, 3, 4)
TOTAL_PRIZES = sum(EXPECTED)
DEFAULT_DOMAINS = ["ketqua16.net", "ketqua.net", "ketqua.vn", "ketquaxoso.net"] + [f"ketqua{i}.net" for i in range(1, 51)]
DATE_RE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
NUMBER_RE = re.compile(r"(?<!\d)\d{2,5}(?!\d)")

@dataclass(frozen=True)
class SourceRecord:
    draw_date: str
    full_prizes: tuple[str, ...]
    source_domain: str
    source_url: str
    source_html_sha256: str
    table_fingerprint: str

    @property
    def tails27(self) -> tuple[str, ...]:
        return tuple(x[-2:] for x in self.full_prizes)

    @property
    def full_fingerprint(self) -> str:
        payload = json.dumps({"date": self.draw_date, "full_prizes": self.full_prizes}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

def normalize_date(text: str) -> str | None:
    m = DATE_RE.search(text or "")
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d).isoformat()
    except ValueError:
        return None

def cell_tokens(cell) -> list[str]:
    values = []
    for text in cell.stripped_strings:
        values.extend(NUMBER_RE.findall(text))
    return values

def extract_full_27(table) -> list[str] | None:
    """Extract exactly the full prize values from one DOM result table."""
    rows = {}
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        label = " ".join(cells[0].stripped_strings).strip().lower()
        label = re.sub(r"\s+", " ", label)
        if label in {"đb", "g.đb", "g.db", "db", "đặc biệt", "g đặc biệt"}:
            idx = 0
        else:
            m = re.search(r"g\s*[.:]?\s*([1-7])\b", label)
            if not m:
                continue
            idx = int(m.group(1))
        vals = []
        for cell in cells[1:]:
            vals.extend(cell_tokens(cell))
        if not vals:
            vals = [x for x in cell_tokens(cells[0]) if x != label]
        if len(vals) != EXPECTED[idx]:
            continue
        if idx in rows and rows[idx] != vals:
            return None
        rows[idx] = vals
    if len(rows) != 8 or any(len(rows[i]) != EXPECTED[i] for i in range(8)):
        return None
    return [v for i in range(8) for v in rows[i]]

def validate_full_27(values: Iterable[str]) -> tuple[str, ...]:
    values = tuple(str(v).strip() for v in values)
    if len(values) != TOTAL_PRIZES:
        raise ValueError(f"expected {TOTAL_PRIZES} full prizes, got {len(values)}")
    for i, value in enumerate(values, 1):
        if not re.fullmatch(r"\d{2,5}", value):
            raise ValueError(f"invalid prize token #{i}: {value!r}")
    return values

def tails27(values: Iterable[str]) -> tuple[str, ...]:
    full = validate_full_27(values)
    return tuple(v[-2:] for v in full)

def canonical_dataset_sha(records: Iterable[SourceRecord]) -> str:
    rows = [{"draw_date": r.draw_date, "full_prizes": list(r.full_prizes)} for r in sorted(records, key=lambda x: (x.draw_date, x.full_fingerprint))]
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()

def _table_fingerprint(table) -> str:
    return hashlib.sha256(" ".join(table.stripped_strings).encode("utf-8")).hexdigest()

class ForensicCrawler:
    def __init__(self, domains=None, timeout=10, workers=12, quorum=2):
        self.domains = list(dict.fromkeys(domains or DEFAULT_DOMAINS))
        self.timeout = timeout
        self.workers = max(1, min(workers, len(self.domains)))
        self.quorum = quorum

    def _urls(self, domain, target_dates=None):
        urls = []
        for iso in sorted(set(target_dates or [])):
            try:
                d = date.fromisoformat(iso)
                urls.append(f"https://{domain}/xsmb-ngay-{d:%d-%m-%Y}.html")
            except ValueError:
                pass
        today = datetime.now().date()
        urls += [f"https://{domain}/xsmb-ngay-{today:%d-%m-%Y}.html", f"https://{domain}/so-ket-qua-truyen-thong/300", f"https://{domain}/"]
        return list(dict.fromkeys(urls))

    def _fetch_domain(self, domain, target_dates=None):
        session = requests.Session()
        headers = {"User-Agent": "XSMB-ForensicCrawler/1.0", "Accept": "text/html,application/xhtml+xml"}
        records, seen = [], set()
        for url in self._urls(domain, target_dates):
            try:
                response = session.get(url, headers=headers, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                html_sha = hashlib.sha256(response.content).hexdigest()
                soup = BeautifulSoup(response.text, "html.parser")
                for table in soup.find_all("table"):
                    node = table.find_previous(string=DATE_RE)
                    if not node:
                        continue
                    draw_date = normalize_date(str(node))
                    if not draw_date:
                        continue
                    full = extract_full_27(table)
                    if not full:
                        continue
                    full = validate_full_27(full)
                    table_sha = _table_fingerprint(table)
                    key = (draw_date, table_sha)
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(SourceRecord(draw_date, full, domain, url, html_sha, table_sha))
            except requests.RequestException:
                continue
        return records

    def crawl(self, target_dates=None):
        all_records = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = [pool.submit(self._fetch_domain, d, target_dates) for d in self.domains]
            for future in as_completed(futures):
                try:
                    all_records.extend(future.result())
                except Exception:
                    continue
        return all_records

    def reconcile(self, records):
        by_date = {}
        for r in records:
            by_date.setdefault(r.draw_date, {}).setdefault(r.full_prizes, set()).add(r.source_domain)
        consensus, conflicts = [], {}
        for draw_date, variants in sorted(by_date.items()):
            ranked = sorted(variants.items(), key=lambda item: (-len(item[1]), item[0]))
            winner, sources = ranked[0]
            if len(sources) >= self.quorum:
                contributors = ";".join(sorted(sources))
                consensus.append(SourceRecord(draw_date, winner, f"QUORUM:{contributors}", "", "", hashlib.sha256((draw_date + "|" + " ".join(winner)).encode()).hexdigest()))
            if len(variants) > 1:
                conflicts[draw_date] = {"|".join(v): sorted(s) for v, s in variants.items()}
        return consensus, conflicts
