from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from data.ingestion.full27_validator import validate_prize_groups

NAMES = ('DB', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7')
NUMBER_RE = re.compile(r'(?<!\d)\d{2,5}(?!\d)')
DEFAULT_SOURCES = {
    'minhngoc_mb': 'https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/{dd}-{mm}-{yyyy}.html',
    'xoso_mb': 'https://xoso.com.vn/xsmb-{dd}-{mm}-{yyyy}.html',
    'xskt_mb': 'https://xskt.com.vn/xsmb/ngay-{d}-{m}-{yyyy}',
}

@dataclass(frozen=True)
class SourceRecord:
    draw_date: str
    full_prizes: tuple[str, ...]
    source_id: str
    source_url: str
    source_html_sha256: str
    table_fingerprint: str
    raw_artifact_path: str

    @property
    def tails27(self) -> tuple[str, ...]:
        return tuple(x[-2:] for x in self.full_prizes)

    @property
    def full_fingerprint(self) -> str:
        payload = json.dumps({'date': self.draw_date, 'full_prizes': self.full_prizes}, separators=(',', ':'), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()


def url_for(source_id: str, day: date) -> str:
    return DEFAULT_SOURCES[source_id].format(dd=f'{day.day:02d}', mm=f'{day.month:02d}', d=day.day, m=day.month, yyyy=day.year)


def _label(text: str) -> str:
    text = re.sub(r'\s+', ' ', text.strip().lower())
    if text in {'đb', 'g.đb', 'g.db', 'db', 'đặc biệt', 'g đặc biệt'}:
        return 'DB'
    match = re.search(r'(?:giải|g)\s*[.:]?\s*([1-7])\b', text)
    if match:
        return f'G{match.group(1)}'
    if text in {'1', '2', '3', '4', '5', '6', '7'}:
        return f'G{text}'
    return ''


def _tokens(cell) -> list[str]:
    out: list[str] = []
    for text in cell.stripped_strings:
        out.extend(NUMBER_RE.findall(text))
    return out


def extract_groups(html: str) -> dict[str, list[str]] | None:
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []
    for table in soup.find_all('table'):
        groups: dict[str, list[str]] = {}
        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue
            name = _label(' '.join(cells[0].stripped_strings))
            if not name:
                continue
            values: list[str] = []
            for cell in cells[1:]:
                values.extend(_tokens(cell))
            if not values:
                values = _tokens(cells[0])
            if name in groups and groups[name] != values:
                groups[name] = []
                continue
            groups[name] = values
        if all(name in groups for name in NAMES):
            try:
                validate_prize_groups(groups)
                candidates.append(groups)
            except ValueError:
                continue
    if not candidates:
        return None
    first = candidates[0]
    if any(candidate != first for candidate in candidates[1:]):
        raise ValueError('MULTIPLE_FULL27_TABLES_CONFLICT')
    return first


def _verify_page_date(html: str, day: date) -> bool:
    text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
    forms = {
        day.strftime('%d/%m/%Y'),
        day.strftime('%d-%m-%Y'),
        f'{day.day}/{day.month}/{day.year}',
        f'{day.day}-{day.month}-{day.year}',
    }
    return any(form in text for form in forms)


def fetch_one(source_id: str, day: date, timeout: int = 20, raw_root: str | Path = 'runtime/raw') -> SourceRecord | None:
    url = url_for(source_id, day)
    response = requests.get(url, headers={'User-Agent': 'XSMB-ForensicCrawler/2.1', 'Accept': 'text/html,application/xhtml+xml'}, timeout=timeout)
    if response.status_code != 200:
        return None

    content = response.content
    html_sha = hashlib.sha256(content).hexdigest()
    if not _verify_page_date(response.text, day):
        raise ValueError('PAGE_DATE_MISMATCH')

    raw_dir = Path(raw_root) / source_id / day.isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f'{html_sha}.html'
    meta_path = raw_dir / f'{html_sha}.json'
    if not raw_path.exists():
        raw_path.write_bytes(content)
    if not meta_path.exists():
        meta_path.write_text(json.dumps({'source_id': source_id, 'url': url, 'date': day.isoformat(), 'sha256': html_sha, 'byte_length': len(content)}, ensure_ascii=False, indent=2), encoding='utf-8')

    groups = extract_groups(response.text)
    if groups is None:
        return None
    full = validate_prize_groups(groups)
    table_sha = hashlib.sha256(json.dumps(groups, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()).hexdigest()
    return SourceRecord(day.isoformat(), full, source_id, url, html_sha, table_sha, str(raw_path))


def crawl(days: Iterable[date], sources: Iterable[str] = DEFAULT_SOURCES, workers: int = 6, timeout: int = 20):
    tasks = [(source, day) for source in sources for day in days]
    records: list[SourceRecord] = []
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(tasks) or 1))) as pool:
        futures = {pool.submit(fetch_one, source, day, timeout): (source, day) for source, day in tasks}
        for future in as_completed(futures):
            source, day = futures[future]
            try:
                record = future.result()
                if record:
                    records.append(record)
            except Exception as exc:
                errors.append({'source_id': source, 'date': day.isoformat(), 'error': f'{type(exc).__name__}: {exc}'})
    return records, errors


def reconcile(records: Iterable[SourceRecord], quorum: int = 2):
    by_date: dict[str, dict[tuple[str, ...], set[str]]] = {}
    for record in records:
        by_date.setdefault(record.draw_date, {}).setdefault(record.full_prizes, set()).add(record.source_id)

    consensus = []
    conflicts = {}
    for draw_date, variants in sorted(by_date.items()):
        ranked = sorted(variants.items(), key=lambda item: (-len(item[1]), item[0]))
        winner, sources = ranked[0]
        if len(sources) >= quorum and len(variants) == 1:
            consensus.append({'date': draw_date, 'full_27': list(winner), 'sources': sorted(sources), 'promotion': 'ALLOW_CANDIDATE'})
        elif len(variants) > 1:
            conflicts[draw_date] = {'variants': [{'full_27': list(values), 'sources': sorted(source_ids)} for values, source_ids in variants.items()], 'promotion': 'DENY'}
        else:
            conflicts[draw_date] = {'reason': 'QUORUM_NOT_MET', 'sources': sorted(sources), 'promotion': 'DENY'}
    return consensus, conflicts
