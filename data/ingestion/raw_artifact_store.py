from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RawArtifact:
    source_id: str
    url: str
    retrieved_at: str
    sha256: str
    byte_length: int
    content_path: str


class RawArtifactStore:
    """Write-once raw evidence store. Never overwrites an existing artifact."""

    def __init__(self, root: str | Path = "runtime/raw") -> None:
        self.root = Path(root)

    def put(self, *, source_id: str, url: str, content: bytes) -> RawArtifact:
        digest = hashlib.sha256(content).hexdigest()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        directory = self.root / source_id / day
        directory.mkdir(parents=True, exist_ok=True)
        content_path = directory / f"{digest}.html"
        if not content_path.exists():
            content_path.write_bytes(content)
        metadata = RawArtifact(
            source_id=source_id,
            url=url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            sha256=digest,
            byte_length=len(content),
            content_path=str(content_path),
        )
        meta_path = content_path.with_suffix(".json")
        if not meta_path.exists():
            meta_path.write_text(json.dumps(asdict(metadata), ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
