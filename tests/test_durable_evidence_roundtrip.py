import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verification.durable_evidence_roundtrip import evidence_sha, verify_envelope


class DurableEvidenceRoundtripTests(unittest.TestCase):
    def _write_envelope(self, payload):
        payload = dict(payload)
        payload["evidence_sha256"] = evidence_sha(payload)
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        json.dump(payload, handle, ensure_ascii=False)
        handle.close()
        return Path(handle.name), payload

    def test_valid_envelope_requires_matching_readback_hash(self):
        path, envelope = self._write_envelope({"action_id": "TEST-ROUNDTRIP", "value": 1})
        with patch("verification.durable_evidence_roundtrip.persist_envelope") as persist, patch(
            "verification.durable_evidence_roundtrip.read_envelope", return_value=envelope
        ):
            code, result = verify_envelope(path)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        persist.assert_called_once_with(envelope)

    def test_readback_payload_tamper_is_denied_even_when_hash_field_is_retained(self):
        path, envelope = self._write_envelope({"action_id": "TEST-TAMPER", "value": 1})
        tampered = dict(envelope)
        tampered["value"] = 999
        with patch("verification.durable_evidence_roundtrip.persist_envelope"), patch(
            "verification.durable_evidence_roundtrip.read_envelope", return_value=tampered
        ):
            code, result = verify_envelope(path)
        self.assertEqual(code, 5)
        self.assertEqual(result["status"], "DENY_READBACK_HASH_MISMATCH")

    def test_local_hash_mismatch_is_denied_before_persistence(self):
        path, envelope = self._write_envelope({"action_id": "TEST-LOCAL", "value": 1})
        envelope["value"] = 2
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with patch("verification.durable_evidence_roundtrip.persist_envelope") as persist:
            code, result = verify_envelope(path)
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "EVIDENCE_SHA_LOCAL_MISMATCH")
        persist.assert_not_called()


if __name__ == "__main__":
    unittest.main()
