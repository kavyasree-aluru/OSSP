import unittest
from backend.simulation import Simulation
from backend.scenarios import SCENARIOS
from backend.bankers import safety


class TestBankers(unittest.TestCase):
    def m(self, sid):
        s = Simulation(); s.load(SCENARIOS[sid]); return s.matrices()

    def test_safe_textbook_sequence(self):
        r = safety(self.m("bankers_safe"))
        self.assertTrue(r["safe"]); self.assertEqual(r["sequence"], ["P1", "P3", "P4", "P0", "P2"])

    def test_unsafe_state_is_not_deadlock(self):
        from backend.detection import detect_multi_instance
        m = self.m("bankers_unsafe")
        self.assertFalse(safety(m)["safe"]); self.assertFalse(detect_multi_instance(m)["has_deadlock"])

    def test_need_is_max_minus_alloc(self):
        self.assertEqual(safety(self.m("bankers_safe"))["need"][0], [7, 4, 3])

    def test_alloc_above_max_rejected(self):
        m = self.m("bankers_safe"); m["alloc"][0][0] = 99
        with self.assertRaises(ValueError): safety(m)

if __name__ == "__main__":
    unittest.main()
