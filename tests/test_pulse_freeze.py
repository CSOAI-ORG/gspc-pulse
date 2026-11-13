import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pulse_freeze


class PulseFreezePrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.paths = {
            "JSONL": base / "pulse.jsonl",
            "MANIFEST": base / "pulse-freeze-manifest.json",
            "LEAVES": base / "pulse-leaves.json",
            "SIG": base / "pulse-freeze-manifest.sig",
            "KEY": base / "pulse-lane-key.pem",
        }
        self.patches = [patch.object(pulse_freeze, name, str(path)) for name, path in self.paths.items()]
        for item in self.patches:
            item.start()
        self.rows = [
            {"ts": "2026-11-01T00:00:00Z", "kev": {"count": 10}},
            {"ts": "2026-11-01T01:00:00Z", "kev": {"count": 11}},
            {"ts": "2026-11-01T02:00:00Z", "kev": {"count": 12}},
        ]
        self._write_rows(self.rows)
        self.assertEqual(pulse_freeze.cmd_freeze(None), 0)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def _write_rows(self, rows):
        Path(self.paths["JSONL"]).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))

    def _capture(self, fn, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = fn(*args, **kwargs)
        return result, output.getvalue()

    def test_full_series_verifies_before_any_tail(self):
        result, output = self._capture(pulse_freeze.verify, {}, False)
        self.assertEqual(result, 0)
        self.assertIn("VERIFIED FULL SERIES", output)

    def test_unsigned_tail_is_reported_but_not_mislabelled_signed(self):
        rows = self.rows + [
            {"ts": "2026-11-01T03:00:00Z", "kev": {"count": 13}},
            {"ts": "2026-11-01T04:00:00Z", "kev": {"count": 14}},
        ]
        self._write_rows(rows)
        result, output = self._capture(pulse_freeze.verify, {}, False)
        self.assertEqual(result, 0)
        self.assertIn("VERIFIED SIGNED PREFIX", output)
        self.assertIn("UNSIGNED TAIL: 2 row(s)", output)
        self.assertIn("signature ok", output)
        strict, strict_output = self._capture(pulse_freeze.verify, {}, False, True)
        self.assertEqual(strict, 1)
        self.assertIn("--require-full", strict_output)

    def test_unsigned_tail_is_not_inclusion_provable(self):
        rows = self.rows + [{"ts": "2026-11-01T03:00:00Z", "kev": {"count": 13}}]
        self._write_rows(rows)
        verdict, _ = pulse_freeze.inclusion_proof("2026-11-01T00:00:00Z")
        self.assertEqual(verdict, "VALID")
        verdict, reason = pulse_freeze.inclusion_proof("2026-11-01T03:00:00Z")
        self.assertIsNone(verdict)
        self.assertIn("unsigned tail", reason)

    def test_unsigned_tail_changes_do_not_become_signed(self):
        rows = self.rows + [{"ts": "2026-11-01T03:00:00Z", "kev": {"count": 13}}]
        rows[-1]["kev"]["count"] = 999
        self._write_rows(rows)
        result, output = self._capture(pulse_freeze.verify, {}, False)
        self.assertEqual(result, 0)
        self.assertIn("UNSIGNED TAIL: 1 row(s)", output)
        self.assertIn("VERIFIED SIGNED PREFIX", output)

    def test_tampered_signed_row_fails_even_when_tail_exists(self):
        rows = self.rows + [{"ts": "2026-11-01T03:00:00Z", "kev": {"count": 13}}]
        rows[0]["kev"]["count"] = 999
        self._write_rows(rows)
        result, output = self._capture(pulse_freeze.verify, {}, False)
        self.assertEqual(result, 1)
        self.assertIn("signed row 0 does not match its leaf", output)
        self.assertIn("signature ok", output)

    def test_self_test_tampers_a_signed_row_and_restores_files(self):
        result, output = self._capture(pulse_freeze.cmd_self_test, None)
        self.assertEqual(result, 0)
        self.assertIn("YES (correct)", output)
        self.assertFalse(Path(str(self.paths["JSONL"]) + ".bak").exists())
        self.assertEqual(pulse_freeze.verify({}, quiet=True), 0)


if __name__ == "__main__":
    unittest.main()
