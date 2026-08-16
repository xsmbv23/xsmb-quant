from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from data.ingestion.full27_validator import validate_prize_groups

EXPECTED = (1, 1, 2, 6, 4, 6, 3, 4)
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

    @property
    def tails27(self) -> tuple[str, ...]:
        return tuple(x[-2:] for x in self.full_prizes)

    @property
    def full_fingerprint(self) -> str:
        payload = json.dumps({'date': self.draw_date, 'full_prizes': self.full_prizes}, separators=(',', ':'), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()


def url_for(source_id: str, day: date) -> str:
    template = DEFAULT_SOURCES[source_id]
    return template.format(dd=f'{day.day:02d}', mm=f'{day.month:02d}', d=day.day, m=day.month, yyyy=day.year)


def _label(text: str) -> str:
    text = re.sub(r'\s+', ' ', text.strip().lower())
    if text in {'đb', 'g.đb', 'g.db', 'db', 'đặc biệt', 'g đặc biệt'}: return 'DB'
    m = re.search(r'(?:giải|g)\s*[.:]?\s*([1-7])\b', text)
    if m: return f'G{m.group(1)}'
    if text in {'1', '2', '3', '4', '5', '6', '7'}: return f'G{text}'
    return ''


def _tokens(cell) -> list[str]:
    out=[]
    for s in cell.stripped_strings:
        out.extend(NUMBER_RE.findall(s))
    return out


def extract_groups(html: str) -> dict[str, list[str]] | None:
    soup = BeautifulSoup(html, 'html.parser')
    candidates=[]
    for table in soup.find_all('table'):
        groups={}
        for tr in table.find_all('tr'):
            cells=tr.find_all(['th','td'])
            if not cells: continue
            name=_label(' '.join(cells[0].stripped_strings))
            if not name: continue
            vals=[]
            for cell in cells[1:]: vals.extend(_tokens(cell))
            if not vals: vals=_tokens(cells[0])
            if name in groups and groups[name] != vals: groups[name]=[]; continue
            groups[name]=vals
        if all(n in groups for n in NAMES):
            try:
                validate_prize_groups(groups)
                candidates.append(groups)
            except ValueError:
                continue
    if not candidates: return None
    first=candidates[0]
    if any(c != first for c in candidates[1:]):
        raise ValueError('MULTIPLE_FULL27_TABLES_CONFLICT')
    return first


def _verify_page_date(html: str, day: date) -> bool:
    # The URL is date-specific, but the page must also contain the target date.
    forms=(day.strftime('%d/%m/%Y'), day.strftime('%d-%m-%Y'), day.strftime('%-d/%-m/%Y') if hasattr(day,'strftime') else '')
    text=BeautifulSoup(html,'html.parser').get_text(' ',strip=True)
    return any(f in text for f in forms if f)


def fetch_one(source_id: str, day: date, timeout: int = 20) -> SourceRecord | None:
    url=url_for(source_id, day)
    headers={'User-Agent':'XSMB-ForensicCrawler/2.0','Accept':'text/html,application/xhtml+xml'}
    r=requests.get(url,headers=headers,timeout=timeout)
    if r.status_code != 200: return None
    html_sha=hashlib.sha256(r.content).hexdigest()
    if not _verify_page_date(r.text, day): return None
    groups=extract_groups(r.text)
    if groups is None: return None
    full=validate_prize_groups(groups)
    table_sha=hashlib.sha256(json.dumps(groups,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
    return SourceRecord(day.isoformat(),full,source_id,url,html_sha,table_sha)


def crawl(days: Iterable[date], sources: Iterable[str] = DEFAULT_SOURCES, workers: int = 6, timeout: int = 20):
    tasks=[(s,d) for s in sources for d in days]
    records=[]
    errors=[]
    with ThreadPoolExecutor(max_workers=max(1,min(workers,len(tasks) or 1))) as pool:
        futs={pool.submit(fetch_one,s,d,timeout):(s,d) for s,d in tasks}
        for f in as_completed(futs):
            s,d=futs[f]
            try:
                rec=f.result()
                if rec: records.append(rec)
            except Exception as e:
                errors.append({'source_id':s,'date':d.isoformat(),'error':type(e).__name__+': '+str(e)})
    return records, errors


def reconcile(records: Iterable[SourceRecord], quorum: int = 2):
    by_date={}
    for r in records:
        by_date.setdefault(r.draw_date,{}).setdefault(r.full_prizes,set()).add(r.source_id)
    consensus=[]; conflicts={}
    for draw_date,variants in sorted(by_date.items()):
        ranked=sorted(variants.items(),key=lambda x:(-len(x[1]),x[0]))
        winner,sources=ranked[0]
        if len(sources) >= quorum:
            consensus.append({'date':draw_date,'full_27':list(winner),'sources':sorted(sources),'promotion':'ALLOW_CANDIDATE'})
        if len(variants)>1:
            conflicts[draw_date]={'variants':{' '.join(v):sorted(s) for v,s in variants.items()},'promotion':'DENY'}
    return consensus,conflicts
