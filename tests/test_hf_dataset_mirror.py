import unittest
from pathlib import Path
from ci.hf_dataset_mirror import validate

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


if __name__ == "__main__":
    unittest.main()
