from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class ContentNode:
    tag: str
    text: str
    role: str  # DATA, NAV, AD, SCRIPT, UNKNOWN


AD_HINTS = {
    "advertisement", "ads", "banner", "quang-cao", "quảng cáo",
    "googleadservices", "doubleclick", "googlesyndication", "adsbygoogle",
}


def classify_node(*, tag: str, text: str = "", attrs: Iterable[str] = ()) -> str:
    haystack = " ".join((tag, text, *attrs)).lower()
    if tag.lower() in {"script", "style", "noscript"}:
        return "SCRIPT"
    if any(hint in haystack for hint in AD_HINTS):
        return "AD"
    return "UNKNOWN"


def data_identity(html: bytes) -> str:
    return sha256(html).hexdigest()


def is_data_node(node: ContentNode) -> bool:
    return node.role == "DATA"


def reject_ad_as_data(node: ContentNode) -> None:
    if node.role == "AD":
        raise ValueError("AD_CONTENT_CANNOT_BE_CANONICAL_DATA")
