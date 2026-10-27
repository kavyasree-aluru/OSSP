import unittest
from backend.simulation import Simulation
from backend.scenarios import SCENARIOS
from backend.detection import detect_single_instance, detect_multi_instance, risk_indicator


def load(sid):
    s = Simulation(); s.load(SCENARIOS[sid]); return s


class TestDetection(unittest.TestCase):
    def test_all_scenarios_match_expected(self):
        for sid, sc in SCENARIOS.items():
            m = load(sid).matrices()
            self.assertEqual(detect_multi_instance(m)["deadlocked"], sc["expected"]["deadlocked"], sid)
            if "single_cycle" in sc["expected"]:
                self.assertEqual(bool(detect_single_instance(m)["cycle"]), sc["expected"]["single_cycle"], sid)

    def test_no_deadlock_process_finishes(self):
        d = detect_multi_instance(load("no_deadlock").matrices())
        self.assertEqual(d["completion_order"], ["P2", "P1"]); self.assertEqual(d["waiting"], ["P1"])

    def test_two_process_deadlock_path(self):
        r = detect_single_instance(load("simple_deadlock").matrices())
        self.assertEqual(r["verdict"], "deadlock"); self.assertEqual(len(r["path"]), 2)

    def test_three_process_deadlock(self):
        self.assertEqual(detect_multi_instance(load("three_process").matrices())["deadlocked"], ["P1", "P2", "P3"])

    def test_cycle_without_deadlock_is_inconclusive(self):
        m = load("multi_instance").matrices()
        self.assertEqual(detect_single_instance(m)["verdict"], "inconclusive")
        self.assertFalse(detect_multi_instance(m)["has_deadlock"])

    def test_risk_is_labeled_heuristic(self):
        self.assertTrue(risk_indicator(load("no_deadlock").matrices())["heuristic"])
        self.assertFalse(risk_indicator(load("simple_deadlock").matrices())["heuristic"])

if __name__ == "__main__":
    unittest.main()
