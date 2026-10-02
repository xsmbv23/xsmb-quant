from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from data.ingestion.full27_validator import validate_prize_groups

SOURCE_ID = "xsmb"
SOURCE_URL = "https://www.xsmb.com.vn/so-ket-qua-xsmb"
DATE_RE = re.compile(r"XSMB\s+(?:Thứ|Chủ nhật)[^\n]*?(\d{2})/(\d{2})/(\d{4})", re.IGNORECASE)
LABELS = ("ĐB", "G1", "G2", "G3", "G4", "G5", "G6", "G7")
COUNTS = {"ĐB": 1, "G1": 1, "G2": 2, "G3": 6, "G4": 4, "G5": 6, "G6": 3, "G7": 4}
NUMBER_RE = re.compile(r"(?<!\d)\d{2,5}(?!\d)")

_PAGE_CACHE_LOCK = __import__("threading").Lock()
_PAGE_CACHE = None

def clear_page_cache():
    global _PAGE_CACHE
    with _PAGE_CACHE_LOCK:
        _PAGE_CACHE = None

def _extract_group_values(text: str, width: int, expected: int) -> list[str]:
    tokens = re.findall(r"\d+", text)
    values: list[str] = []
    carry = ""
    for token in tokens:
        carry += token
        while len(carry) >= width and len(values) < expected:
            values.append(carry[:width])
            carry = carry[width:]
        if len(values) >= expected:
            break
    return values

@dataclass(frozen=True)
class SourceBRecord:
    draw_date: str
    full_prizes: tuple[str, ...]
    source_id: str
    source_url: str
    source_html_sha256: str
    raw_artifact_path: str
    parse_block_sha256: str

    @property
    def tails27(self) -> tuple[str, ...]:
        return tuple(value[-2:] for value in self.full_prizes)

def _normalise(text: str) -> str:
    return re.sub(r"\s+"," ",text).strip()

def extract_date_block(text: str, target: date) -> str:
    target_header = re.compile(rf"XSMB\s+(?:Thứ|Chủ nhật)[^\n]*?{target.day:02d}/{target.month:02d}/{target.year}\b", re.IGNORECASE)
    match = target_header.search(text)
    if not match:
        raise ValueError("DATE_NOT_OBSERVED")
    remainder = text[match.start():]
    next_match = re.search(r"\nXSMB\s+(?:Thứ|Chủ nhật)\b", remainder[1:], re.IGNORECASE)
    return remainder if not next_match else remainder[:next_match.start()+1]

def _parse_flat_prizes(block: str) -> tuple[str, ...] | None:
    match = re.search(r"(?m)^(?:ĐB|G1|G2|G3|G4|G5|G6|G7)(?:\s*\|)?(?:\s+|$)", block)
    if not match:
        return None

    # BeautifulSoup/table markup can split one prize arbitrarily (e.g. 402 + 08).
    # Ignore token boundaries completely: concatenate all digit runs in the prize
    # area, then slice the canonical 27 prizes by their fixed widths.
    area = re.split(r"(?m)^Đầu(?:\s*\|)?", block[match.start():], maxsplit=1)[0]
    prize_area = re.sub(r"(?m)^(?:ĐB|G1|G2|G3|G4|G5|G6|G7)(?:\s*\|)?\s*", "", area)
    digits = "".join(re.findall(r"\d+", prize_area))
    widths = [5] * 10 + [4] * 10 + [3] * 3 + [2] * 4
    total_digits = sum(widths)
    if len(digits) < total_digits:
        return None

    values = []
    cursor = 0
    for width in widths:
        values.append(digits[cursor:cursor + width])
        cursor += width

    return validate_prize_groups({
        "DB": values[0:1], "G1": values[1:2], "G2": values[2:4],
        "G3": values[4:10], "G4": values[10:14], "G5": values[14:20],
        "G6": values[20:23], "G7": values[23:27],
    })
def parse_full27_block(block: str) -> tuple[str, ...]:
    flat = _parse_flat_prizes(block)
    if flat is not None:
        return flat
    lines = [_normalise(line) for line in block.splitlines() if _normalise(line)]
    groups: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        label = next((c for c in LABELS if re.match(rf"^{re.escape(c)}(?:\s*\|)?(?:\s+|$)", line)), None)
        if label is None:
            continue
        width = 5 if label in ("ĐB", "G1", "G2", "G3") else 4 if label in ("G4", "G5") else 3 if label == "G6" else 2
        remainder = re.sub(rf"^{re.escape(label)}(?:\s*\|)?\s*", "", line, count=1)
        values = _extract_group_values(remainder, width, COUNTS[label])
        cursor = index + 1
        while len(values) < COUNTS[label] and cursor < len(lines):
            next_line = lines[cursor]
            if any(re.match(rf"^{re.escape(c)}(?:\s*\|)?(?:\s+|$)", next_line) for c in LABELS):
                break
            values.extend(_extract_group_values(next_line, width, COUNTS[label] - len(values)))
            cursor += 1
        groups[label] = values[:COUNTS[label]]

    if set(groups) == set(LABELS) and all(
        len(groups[label]) == expected for label, expected in COUNTS.items()
    ):
        return validate_prize_groups({
            "DB": groups["ĐB"], "G1": groups["G1"], "G2": groups["G2"], "G3": groups["G3"],
            "G4": groups["G4"], "G5": groups["G5"], "G6": groups["G6"], "G7": groups["G7"],
        })

    # The site can change table markup while preserving visible prize order.
    # In a date block the first 27 numeric tokens after the first prize label
    # are the 27 prize values; the later "Đầu/Lô tô" numbers are ignored.
    first_label_match = re.search(r"(?m)^(?:ĐB|G1|G2|G3|G4|G5|G6|G7)(?:\s*\|)?(?:\s+|$)", block)
    first_label = first_label_match.start() if first_label_match else -1
    if first_label >= 0:
        prize_tokens = NUMBER_RE.findall(block[first_label:])
        if len(prize_tokens) >= 27:
            candidate = prize_tokens[:27]
            return validate_prize_groups({
                "DB": candidate[0:1], "G1": candidate[1:2], "G2": candidate[2:4],
                "G3": candidate[4:10], "G4": candidate[10:14], "G5": candidate[14:20],
                "G6": candidate[20:23], "G7": candidate[23:27],
            })

    if set(groups) != set(LABELS):
        raise ValueError(f"FULL27_GROUP_MISSING:{','.join(sorted(set(LABELS) - set(groups)))}")
    for label, expected in COUNTS.items():
        if len(groups[label]) != expected:
            raise ValueError(f"FULL27_GROUP_COUNT:{label}:{len(groups[label])}!={expected}")
    return validate_prize_groups({
        "DB": groups["ĐB"], "G1": groups["G1"], "G2": groups["G2"], "G3": groups["G3"],
        "G4": groups["G4"], "G5": groups["G5"], "G6": groups["G6"], "G7": groups["G7"],
    })

def fetch_source_b(day: date, raw_root: str | Path = "runtime/raw", timeout: int = 20, parse_window_bytes: int = 32 * 1024 * 1024) -> SourceBRecord:
    raw_dir=Path(raw_root)/SOURCE_ID/day.isoformat()
    raw_dir.mkdir(parents=True,exist_ok=True)
    tmp_path=raw_dir/".capture.html"
    global _PAGE_CACHE
    with _PAGE_CACHE_LOCK:
        cached=_PAGE_CACHE
        if cached is None:
            digest=hashlib.sha256(); chunks=[]
            with requests.get(SOURCE_URL,headers={"User-Agent":"XSMB-ForensicCrawler/2.1","Accept":"text/html,application/xhtml+xml"},timeout=timeout,stream=True) as response:
                response.raise_for_status(); encoding=response.encoding or "utf-8"
                for chunk in response.iter_content(chunk_size=64*1024):
                    if chunk:
                        digest.update(chunk); chunks.append(chunk)
            content=b"".join(chunks); cached=(content,encoding,digest.hexdigest()); _PAGE_CACHE=cached
    content,encoding,html_sha=cached
    byte_length=len(content); tmp_path.write_bytes(content)
    raw_path=raw_dir/f"{html_sha}.html"; tmp_path.replace(raw_path)
    text=content.decode(encoding,errors="replace")
    visible=BeautifulSoup(text,"html.parser").get_text("\n",strip=True)
    block=extract_date_block(visible,day); full=parse_full27_block(block)
    block_sha=hashlib.sha256(block.encode("utf-8")).hexdigest()
    meta_path=raw_dir/f"{html_sha}.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps({"schema":"XSMB-SOURCE-CAPTURE-V1","source_id":SOURCE_ID,"source_url":SOURCE_URL,"observed_date":day.isoformat(),"raw_sha256":html_sha,"parse_block_sha256":block_sha,"byte_length":byte_length,"durability":"LOCAL_EPHEMERAL","promotion_eligible":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return SourceBRecord(day.isoformat(),full,SOURCE_ID,SOURCE_URL,html_sha,str(raw_path),block_sha)
