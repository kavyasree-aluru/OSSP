import unittest
from backend.simulation import Simulation, SimError, NotFound
from backend.scenarios import SCENARIOS


def sim():
    s = Simulation(); s.add_resource("R1", 2); s.add_resource("R2", 1)
    s.add_process("P1", {"R1": 2, "R2": 1}); s.add_process("P2", {"R1": 1, "R2": 1}); return s


class TestSimulation(unittest.TestCase):
    def test_grant_and_block(self):
        s = sim()
        self.assertEqual(s.request("P1", "R2", 1), "granted")
        self.assertEqual(s.request("P2", "R2", 1), "blocked")
        s.release("P1", "R2", 1)  # pending request auto-granted
        self.assertEqual(s.procs["P2"]["alloc"]["R2"], 1); self.assertEqual(s.avail("R2"), 0)

    def test_invalid_ids_and_counts(self):
        s = sim()
        with self.assertRaises(NotFound): s.request("PX", "R1", 1)
        with self.assertRaises(NotFound): s.request("P1", "RX", 1)
        for bad in (-1, 0, "a", 1.5, True):
            with self.assertRaises(SimError): s.request("P1", "R1", bad)
        with self.assertRaises(SimError): s.add_resource("R3", -4)

    def test_exceed_max_claim(self):
        s = sim()
        with self.assertRaises(SimError): s.request("P2", "R1", 2)

    def test_request_above_available_is_blocked_not_allocated(self):
        s = sim(); s.request("P1", "R1", 2)
        self.assertEqual(s.request("P2", "R1", 1), "blocked"); self.assertEqual(s.avail("R1"), 0)

    def test_release_more_than_held_is_atomic(self):
        s = sim(); s.request("P1", "R1", 1); before = s.matrices()
        with self.assertRaises(SimError): s.release("P1", "R1", 2)
        self.assertEqual(s.matrices(), before)

    def test_invariant_holds_through_operations(self):
        s = sim()
        for op in [("request", "P1", "R1", 2), ("request", "P2", "R1", 1), ("release", "P1", "R1", 1), ("finish", "P1")]:
            getattr(s, op[0])(*op[1:]); s.check_invariants()

    def test_scenarios_are_consistent(self):
        for sc in SCENARIOS.values():
            s = Simulation(); s.load(sc)
            for r, t in s.resources.items():
                self.assertEqual(t, s.avail(r) + sum(p["alloc"][r] for p in s.procs.values()))

    def test_bad_scenario_rejected(self):
        s = Simulation()
        with self.assertRaises(SimError):
            s.load({"resources": {"R": 1}, "processes": {"A": {"max": {"R": 1}, "alloc": {"R": 1}}, "B": {"max": {"R": 1}, "alloc": {"R": 1}}}})

class TestAPI(unittest.TestCase):
    def setUp(self):
        from app import create_app
        self.c = create_app().test_client()

    def test_flow(self):
        self.assertEqual(self.c.post("/api/scenarios/recoverable/load").status_code, 200)
        self.assertEqual(self.c.get("/api/state").json["multi"]["deadlocked"], ["P1", "P2"])
        r = self.c.post("/api/recover", json={"strategy": "terminate", "pid": "P1"})
        self.assertTrue(r.json["recovery"]["resolved"])
        self.assertEqual(self.c.get("/api/state").json["multi"]["deadlocked"], [])

    def test_errors(self):
        self.assertEqual(self.c.post("/api/request", json={"pid": "X", "resource": "R", "count": 1}).status_code, 404)
        self.assertEqual(self.c.post("/api/resources", json={"name": "R", "total": -1}).status_code, 400)
        self.assertEqual(self.c.post("/api/resources", data="x").status_code, 400)
        self.assertEqual(self.c.post("/api/scenarios/nope/load").status_code, 404)

    def test_whatif_does_not_mutate(self):
        self.c.post("/api/scenarios/simple_deadlock/load")
        r = self.c.post("/api/whatif", json={"action": "add_instance", "resource": "R1", "count": 1})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/api/state").json["multi"]["deadlocked"], ["P1", "P2"])

    def test_exports(self):
        self.c.post("/api/scenarios/simple_deadlock/load")
        self.assertIn("time,kind,message", self.c.get("/api/export/events.csv").text)
        self.assertEqual(self.c.get("/report").status_code, 200)

if __name__ == "__main__":
    unittest.main()
