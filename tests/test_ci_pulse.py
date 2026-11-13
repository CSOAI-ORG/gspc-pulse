import unittest
import ci_pulse


class CurrentPulseWriterTests(unittest.TestCase):
    def test_current_writer_probes_meok_domain(self):
        self.assertIn("meok.ai", ci_pulse.DOMAINS)
        self.assertEqual(len(ci_pulse.DOMAINS), 20)


if __name__ == "__main__":
    unittest.main()
