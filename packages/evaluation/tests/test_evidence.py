import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

EVALUATION = Path(__file__).resolve().parents[1]
DATASETS = EVALUATION / "datasets"
SYNTHETIC = EVALUATION / "fixtures/synthetic"
SCHEMA = json.loads((DATASETS / "manifest.schema.json").read_text())
MANIFEST = json.loads((SYNTHETIC / "manifest.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class EvidenceContractTest(unittest.TestCase):
    def test_schema_is_valid_and_manifest_is_accepted(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(list(VALIDATOR.iter_errors(MANIFEST)), [])
        template = json.loads((DATASETS / "manifest.template.json").read_text())
        self.assertEqual(list(VALIDATOR.iter_errors(template)), [])

    def test_required_evidence_fields_are_rejected_when_missing(self):
        for field in ("checksum_sha256", "split", "rights_consent"):
            with self.subTest(field=field):
                entry = dict(MANIFEST["entries"][0])
                del entry[field]
                invalid = {"schema_version": "1.0.0", "entries": [entry]}
                self.assertTrue(list(VALIDATOR.iter_errors(invalid)))

    def test_real_entry_requires_approval(self):
        entry = dict(MANIFEST["entries"][0])
        entry["source_type"] = "scan"
        invalid = {"schema_version": "1.0.0", "entries": [entry]}
        self.assertTrue(list(VALIDATOR.iter_errors(invalid)))

    def test_fixture_hashes_dimensions_and_ids(self):
        ids = set()
        for entry in MANIFEST["entries"]:
            with self.subTest(drawing_id=entry["drawing_id"]):
                self.assertNotIn(entry["drawing_id"], ids)
                ids.add(entry["drawing_id"])
                payload = (SYNTHETIC / entry["asset_uri"]).read_bytes()
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(), entry["checksum_sha256"]
                )
                self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", payload[16:24]), (128, 128))

    def test_ground_truth_preserves_connectivity_distinction(self):
        truth = json.loads((SYNTHETIC / "ground_truth.json").read_text())
        self.assertTrue(truth["synthetic_only"])
        self.assertTrue(truth["connected_crossing"]["connected"])
        self.assertIsNotNone(truth["connected_crossing"]["shared_node_id"])
        self.assertFalse(truth["disconnected_crossing"]["connected"])
        self.assertIsNone(truth["disconnected_crossing"]["shared_node_id"])
        self.assertEqual(truth["note_crop"]["literal_text"], "VALVE")
        self.assertEqual(truth["dimension"]["parsed_value"], 25)

    def test_generated_fixtures_are_current(self):
        result = subprocess.run(
            ["python3.12", str(SYNTHETIC / "generate.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
