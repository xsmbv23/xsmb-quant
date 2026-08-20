from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from data.ingestion.full27_validator import validate_prize_groups

SOURCE_ID = "xsmb"
SOURCE_URL = "https://www.xsmb.com.vn/so-ket-qua-xsmb-500-ngay"
DATE_RE = re.compile(r"XSMB\s+(?:Thứ|Chủ nhật)[^\n]*?(\d{2})/(\d{2})/(\d{4})", re.IGNORECASE)
LABELS = ("ĐB", "G1", "G2", "G3", "G4", "G5", "G6", "G7")
COUNTS = {"ĐB": 1, "G1": 1, "G2": 2, "G3": 6, "G4": 4, "G5": 6, "G6": 3, "G7": 4}
NUMBER_RE = re.compile(r"(?<!\d)\d{2,5}(?!\d)")


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
    return re.sub(r"\s+", " ", text).strip()


def extract_date_block(text: str, target: date) -> str:
    target_header = re.compile(
        rf"XSMB\s+(?:Thứ|Chủ nhật)[^\n]*?{target.day:02d}/{target.month:02d}/{target.year}\b",
        re.IGNORECASE,
    )
    match = target_header.search(text)
    if not match:
        raise ValueError("DATE_NOT_OBSERVED")
    remainder = text[match.start():]
    next_match = re.search(r"\nXSMB\s+(?:Thứ|Chủ nhật)\b", remainder[1:], re.IGNORECASE)
    block = remainder if not next_match else remainder[: next_match.start() + 1]
    return block


def parse_full27_block(block: str) -> tuple[str, ...]:
    lines = [_normalise(line) for line in block.splitlines() if _normalise(line)]
    groups: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        label = next((candidate for candidate in LABELS if line == candidate or line.startswith(candidate + " ")), None)
        if label is None:
            continue
        values = NUMBER_RE.findall(line[len(label):])
        cursor = index + 1
        while len(values) < COUNTS[label] and cursor < len(lines):
            next_line = lines[cursor]
            if any(next_line == candidate or next_line.startswith(candidate + " ") for candidate in LABELS):
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
        "DB": groups["ĐB"],
        "G1": groups["G1"],
        "G2": groups["G2"],
        "G3": groups["G3"],
        "G4": groups["G4"],
        "G5": groups["G5"],
        "G6": groups["G6"],
        "G7": groups["G7"],
    }
    return validate_prize_groups(ordered)


def fetch_source_b(day: date, raw_root: str | Path = "runtime/raw", timeout: int = 20, parse_window_bytes: int = 8 * 1024 * 1024) -> SourceBRecord:
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

    html_sha = digest.hexdigest()
    raw_path = raw_dir / f"{html_sha}.html"
    tmp_path.replace(raw_path)
    text = bytes(parse_buf).decode(response.encoding or "utf-8", errors="replace")
    from bs4 import BeautifulSoup
    visible = BeautifulSoup(text, "html.parser").get_text("\n", strip=True)
    block = extract_date_block(visible, day)
    full = parse_full27_block(block)
    block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
    return SourceBRecord(day.isoformat(), full, SOURCE_ID, SOURCE_URL, html_sha, str(raw_path), block_sha)
