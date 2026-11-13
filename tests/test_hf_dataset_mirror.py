import unittest
import tempfile
import json
from pathlib import Path
from ci.hf_dataset_mirror import validate, _stage

ROOT = Path(__file__).resolve().parents[1]


class HuggingFaceDatasetMirrorTests(unittest.TestCase):
    def test_public_payload_and_viewer_configs_are_consistent(self):
        result = validate()
        self.assertGreater(result["rows"], 0)
        self.assertEqual(result["signature_state"], "SIGNED_PREFIX_ONLY")
        self.assertGreater(result["unsigned_tail_rows"], 0)
        self.assertLessEqual(result["signed_prefix_rows"], result["rows"])

    def test_watcher_installs_crypto_before_signature_verification(self):
        workflow = (ROOT / ".github/workflows/gspc-pulse-watcher.yml").read_text()
        install = workflow.index("Install signature verification dependency")
        verify = workflow.index("Verify signed prefix before commit")
        self.assertLess(install, verify)
        self.assertIn("pip install --disable-pip-version-check --quiet cryptography", workflow)

    def test_mirror_receipt_is_deterministic_for_unchanged_source(self):
        summary = validate()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = _stage(ROOT, a, summary)
            second = _stage(ROOT, b, summary)
            self.assertEqual(first, second)
            self.assertEqual(json.loads((Path(a) / "mirror-receipt.json").read_text()),
                             json.loads((Path(b) / "mirror-receipt.json").read_text()))
            self.assertNotIn("published_at", first)
            self.assertNotIn("workflow_run_id", first)
            self.assertEqual(first["latest_ts"], summary["latest_ts"])
            self.assertIn("DIGEST.md", first["files"])


if __name__ == "__main__":
    unittest.main()
