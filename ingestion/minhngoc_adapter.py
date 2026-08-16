from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import re
from urllib.request import Request, urlopen


URL = "https://www.minhngoc.net.vn/xo-so-mien-bac.html"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.script_depth = 0
        self.style_depth = 0
        self.script_tags = 0
        self.style_tags = 0
        self.link_tags = 0
        self.form_tags = 0
        self.table_tags = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "script":
            self.script_depth += 1
            self.script_tags += 1
        elif tag == "style":
            self.style_depth += 1
            self.style_tags += 1
        elif tag == "link":
            self.link_tags += 1
        elif tag == "form":
            self.form_tags += 1
        elif tag == "table":
            self.table_tags += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "script" and self.script_depth:
            self.script_depth -= 1
        elif tag == "style" and self.style_depth:
            self.style_depth -= 1

    def handle_data(self, data):
        if self.script_depth or self.style_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


@dataclass(frozen=True)
class RawCapture:
    source_id: str
    url: str
    retrieved_at: str
    http_status: int
    content_type: str
    content_sha256: str
    byte_length: int
    raw_bytes: bytes


@dataclass(frozen=True)
class Xsmb27Candidate:
    draw_date: str
    full_27: tuple[str, ...]
    source_id: str
    source_url: str
    source_sha256: str
    parser_version: str
    content_hygiene: dict[str, int]


def fetch_raw(timeout: int = 20) -> RawCapture:
    request = Request(
        URL,
        headers={
            "User-Agent": "XSMB-FORENSIC-L0/1.0 (+deterministic-verification)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        status = int(getattr(response, "status", 200))
    return RawCapture(
        source_id="minhngoc",
        url=URL,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        http_status=status,
        content_type=content_type,
        content_sha256=hashlib.sha256(raw).hexdigest(),
        byte_length=len(raw),
        raw_bytes=raw,
    )


def parse_full_27(capture: RawCapture) -> Xsmb27Candidate:
    parser = _TextExtractor()
    parser.feed(capture.raw_bytes.decode("utf-8", errors="replace"))
    text = " ".join(parser.parts)

    date_match = re.search(r"XỔ SỐ Miền Bắc\s*-\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if not date_match:
        raise ValueError("DRAW_DATE_NOT_FOUND")
    draw_date = date_match.group(1)

    specs = [
        ("DB", r"Giải\s+ĐB\s+(\d{5})", 1, 5),
        ("G1", r"Giải\s+nhất\s+(\d{5})", 1, 5),
        ("G2", r"Giải\s+nhì\s+((?:\d{5}\s+){1}\d{5})", 2, 5),
        ("G3", r"Giải\s+ba\s+((?:\d{5}\s+){5}\d{5})", 6, 5),
        ("G4", r"Giải\s+tư\s+((?:\d{4}\s+){3}\d{4})", 4, 4),
        ("G5", r"Giải\s+năm\s+((?:\d{4}\s+){5}\d{4})", 6, 4),
        ("G6", r"Giải\s+sáu\s+((?:\d{3}\s+){2}\d{3})", 3, 3),
        ("G7", r"Giải\s+bảy\s+((?:\d{2}\s+){3}\d{2})", 4, 2),
    ]

    values: list[str] = []
    for label, pattern, count, width in specs:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            raise ValueError(f"{label}_NOT_FOUND")
        found = match.group(1).split()
        if len(found) != count or any(len(v) != width or not v.isdigit() for v in found):
            raise ValueError(f"{label}_SHAPE_INVALID")
        values.extend(found)

    if len(values) != 27:
        raise ValueError("FULL_27_COUNT_INVALID")

    return Xsmb27Candidate(
        draw_date=draw_date,
        full_27=tuple(values),
        source_id=capture.source_id,
        source_url=capture.url,
        source_sha256=capture.content_sha256,
        parser_version="MINHNGOC_XSMB_FULL27_V1",
        content_hygiene={
            "script_tags": parser.script_tags,
            "style_tags": parser.style_tags,
            "link_tags": parser.link_tags,
            "form_tags": parser.form_tags,
            "table_tags": parser.table_tags,
        },
    )
