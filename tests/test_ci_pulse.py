import unittest
import ci_pulse


class CurrentPulseWriterTests(unittest.TestCase):
    def test_current_writer_probes_meok_domain(self):
        self.assertIn("meok.ai", ci_pulse.DOMAINS)
        self.assertEqual(len(ci_pulse.DOMAINS), 20)

    def test_frozen_delta_reports_domain_code_changes(self):
        previous = {"board": {"measured": 30}, "domains": {"codes": {"meok.ai": "ERR"}}}
        current = {"board": {"measured": 30}, "domains": {"codes": {"meok.ai": "200"}}}
        delta = ci_pulse.frozen_delta(previous, current)
        self.assertEqual(delta["domain_codes"], [{"meok.ai": "ERR"}, {"meok.ai": "200"}])

    def test_missing_sections_and_fields_are_not_false_frozen_changes(self):
        previous = {
            "board": {"measured": 30, "slots": 34},
            "domains": {"codes": {"meok.ai": "200"}},
            "did": {"key_ids": ["did:key:example"]},
        }
        current = {"board": {"measured": 30}}
        self.assertEqual(ci_pulse.frozen_delta(previous, current), {})


if __name__ == "__main__":
    unittest.main()
