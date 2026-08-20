from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from data.ingestion.full27_validator import validate_prize_groups

SOURCE_ID = "ketqua16"
SOURCE_URL = "https://ketqua16.net/so-ket-qua-truyen-thong/200"
LABELS = ("Đặc biệt", "Giải nhất", "Giải nhì", "Giải ba", "Giải tư", "Giải năm", "Giải sáu", "Giải bảy")
COUNTS = {"Đặc biệt": 1, "Giải nhất": 1, "Giải nhì": 2, "Giải ba": 6, "Giải tư": 4, "Giải năm": 6, "Giải sáu": 3, "Giải bảy": 4}
NUMBER_RE = re.compile(r"(?<!\d)\d{2,5}(?!\d)")
DATE_HEADER_RE = re.compile(r"(?:Thứ\s+(?:hai|ba|tư|năm|sáu|bảy)|Chủ nhật)\s+ngày\s+(\d{2})-(\d{2})-(\d{4})", re.IGNORECASE)


@dataclass(frozen=True)
class SourceDRecord:
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
    return re.sub(r"\s+", " ", text).strip()


def extract_date_block(text: str, target: date) -> str:
    target = f"{target.day:02d}-{target.month:02d}-{target.year}"
    pattern = re.compile(rf"(?:Thứ\s+(?:hai|ba|tư|năm|sáu|bảy)|Chủ nhật)\s+ngày\s+{re.escape(target)}\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        raise ValueError("DATE_NOT_OBSERVED")
    remainder = text[match.start():]
    next_match = DATE_HEADER_RE.search(remainder[len(match.group(0)):])
    if next_match:
        block = remainder[: len(match.group(0)) + next_match.start()]
    else:
        block = remainder
    return block


def _label(line: str) -> str | None:
    line = _normalise(line)
    for label in LABELS:
        if line == label or line.startswith(label + " ") or line.startswith(label + "|"):
            return label
    return None


def parse_full27_block(block: str) -> tuple[str, ...]:
    lines = [_normalise(line) for line in block.splitlines() if _normalise(line)]
    groups: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        label = _label(line)
        if label is None:
            continue
        tail = line[len(label):].lstrip(" |:")
        values = NUMBER_RE.findall(tail)
        cursor = index + 1
        while len(values) < COUNTS[label] and cursor < len(lines):
            next_line = lines[cursor]
            if _label(next_line) is not None or DATE_HEADER_RE.search(next_line):
                break
            values.extend(NUMBER_RE.findall(next_line))
            cursor += 1
        groups[label] = values[: COUNTS[label]]

    if set(groups) != set(LABELS):
        missing = sorted(set(LABELS) - set(groups))
        raise ValueError(f"FULL27_GROUP_MISSING:{','.join(missing)}")
    for label, expected in COUNTS.items():
        if len(groups[label]) != expected:
            raise ValueError(f"FULL27_GROUP_COUNT:{label}:{len(groups[label])}!={expected}")

    ordered = {
        "DB": groups["Đặc biệt"],
        "G1": groups["Giải nhất"],
        "G2": groups["Giải nhì"],
        "G3": groups["Giải ba"],
        "G4": groups["Giải tư"],
        "G5": groups["Giải năm"],
        "G6": groups["Giải sáu"],
        "G7": groups["Giải bảy"],
    }
    return validate_prize_groups(ordered)


def fetch_source_d(day: date, raw_root: str | Path = "runtime/raw", timeout: int = 20, parse_window_bytes: int = 8 * 1024 * 1024) -> SourceDRecord:
    raw_dir = Path(raw_root) / SOURCE_ID / day.isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = raw_dir / ".capture.html"
    digest = hashlib.sha256()
    parse_buf = bytearray()

    with requests.get(
        SOURCE_URL,
        headers={"User-Agent": "XSMB-ForensicCrawler/2.1", "Accept": "text/html,application/xhtml+xml"},
        timeout=timeout,
        stream=True,
    ) as response:
        response.raise_for_status()
        with tmp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                digest.update(chunk)
                handle.write(chunk)
                if len(parse_buf) < parse_window_bytes:
                    parse_buf.extend(chunk[: parse_window_bytes - len(parse_buf)])
        encoding = response.encoding or "utf-8"

    html_sha = digest.hexdigest()
    raw_path = raw_dir / f"{html_sha}.html"
    tmp_path.replace(raw_path)
    text = bytes(parse_buf).decode(encoding, errors="replace")
    visible = BeautifulSoup(text, "html.parser").get_text("\n", strip=True)
    block = extract_date_block(visible, day)
    full = parse_full27_block(block)
    block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
    return SourceDRecord(day.isoformat(), full, SOURCE_ID, SOURCE_URL, html_sha, str(raw_path), block_sha)
