import unittest
from backend.simulation import Simulation, SimError
from backend.scenarios import SCENARIOS
from backend import recovery


def load(sid):
    s = Simulation(); s.load(SCENARIOS[sid]); return s


class TestRecovery(unittest.TestCase):
    def test_recommendation_picks_cheapest(self):
        r = recovery.recommend(load("recoverable"))
        self.assertEqual(r["victim"], SCENARIOS["recoverable"]["expected"]["victim"])
        self.assertEqual([x["pid"] for x in r["ranking"]], ["P1", "P2"])

    def test_terminate_resolves_and_verifies(self):
        s = load("recoverable"); out = recovery.execute(s, "terminate", "P1")
        self.assertTrue(out["resolved"]); self.assertEqual(out["after"]["deadlocked"], [])
        self.assertEqual(s.procs["P2"]["alloc"]["R1"], 1)  # waiting request was granted
        s.check_invariants()

    def test_terminate_all(self):
        s = load("three_process"); self.assertTrue(recovery.execute(s, "terminate_all")["resolved"])

    def test_terminate_non_deadlocked_rejected(self):
        with self.assertRaises(SimError): recovery.execute(load("recoverable"), "terminate", "P3")

    def test_valid_preemption(self):
        s = load("recoverable"); out = recovery.execute(s, "preempt", "P1", "R1", 1)
        self.assertTrue(out["resolved"]); s.check_invariants()

    def test_invalid_preemptions_leave_state_unchanged(self):
        s = load("recoverable"); before = s.matrices()
        for args in [("P1", "R1", 5), ("P1", "R3", 1), ("P3", "R3", 1), ("P1", "ZZ", 1)]:
            with self.assertRaises(SimError): recovery.execute(s, "preempt", *args)
        self.assertEqual(s.matrices(), before)

    def test_no_recovery_without_deadlock(self):
        with self.assertRaises(SimError): recovery.execute(load("no_deadlock"), "terminate", "P1")

    def test_conservation_after_recovery(self):
        s = load("recoverable"); recovery.execute(s, "terminate", "P1")
        for r, t in s.resources.items():
            self.assertEqual(t, s.avail(r) + sum(p["alloc"][r] for p in s.procs.values()))

if __name__ == "__main__":
    unittest.main()
