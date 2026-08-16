from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen

from .raw_artifact_store import RawArtifact, RawArtifactStore


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    day: date
    status: str
    artifact: RawArtifact | None
    reason: str | None = None


class HistoricalFetcher:
    """Network fetcher with strict provenance; it does not parse or promote data."""

    def __init__(self, store: RawArtifactStore | None = None, timeout: int = 20) -> None:
        self.store = store or RawArtifactStore()
        self.timeout = timeout

    def fetch(self, *, source_id: str, day: date, url: str) -> FetchResult:
        request = Request(url, headers={"User-Agent": "XSMB-ForeNSIC/1.0"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
                artifact = self.store.put(source_id=source_id, url=url, content=content)
                return FetchResult(source_id, day, "FETCHED", artifact)
        except Exception as exc:
            return FetchResult(source_id, day, "FETCH_FAILED", None, type(exc).__name__)
