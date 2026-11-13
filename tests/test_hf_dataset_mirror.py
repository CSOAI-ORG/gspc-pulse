import unittest
from ci.hf_dataset_mirror import validate


class HuggingFaceDatasetMirrorTests(unittest.TestCase):
    def test_public_payload_and_viewer_configs_are_consistent(self):
        result = validate()
        self.assertGreater(result["rows"], 0)
        self.assertEqual(result["signature_state"], "SIGNED_PREFIX_ONLY")
        self.assertGreater(result["unsigned_tail_rows"], 0)
        self.assertLessEqual(result["signed_prefix_rows"], result["rows"])


if __name__ == "__main__":
    unittest.main()
