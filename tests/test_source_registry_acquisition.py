import json
import unittest
from datetime import date
from pathlib import Path

from data.ingestion.forensic_crawler_v2 import registered_source_ids, url_for


ROOT = Path(__file__).resolve().parents[1]


class SourceRegistryAcquisitionTests(unittest.TestCase):
    def _registry(self):
        return json.loads((ROOT / "data/ingestion/source_registry_v2.json").read_text(encoding="utf-8"))

    def test_registry_has_exactly_five_registered_sources(self):
        self.assertEqual(
            registered_source_ids(),
            ("minhngoc", "xoso", "xskt", "ketqua16", "xsmb"),
        )

    def test_every_registered_source_has_adapter_declaration(self):
        for source in self._registry()["sources"]:
            self.assertTrue(source.get("adapter"), source["id"])

    def test_every_registered_source_has_an_acquisition_route(self):
        for source_id in registered_source_ids():
            url = url_for(source_id, date(2026, 8, 12))
            self.assertTrue(url.startswith("https://"), source_id)

    def test_registry_and_acquisition_counts_cannot_silently_drift(self):
        registry = self._registry()
        self.assertEqual(len(registry["sources"]), len(registered_source_ids()))
        self.assertEqual(registry["quorum"]["minimum_independent_sources"], 2)
        self.assertTrue(registry["acquisition_invariant"]["registry_is_authoritative"])


if __name__ == "__main__":
    unittest.main()
