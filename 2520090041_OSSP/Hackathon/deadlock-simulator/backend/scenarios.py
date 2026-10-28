"""Predefined, internally consistent scenarios with expected results (verified by tests)."""


def P(mx, al, rq=None, pr=1, cost=1, prog=1):
    return {"max": mx, "alloc": al, "req": rq or {}, "priority": pr, "cost": cost, "progress": prog}


SCENARIOS = {
    "no_deadlock": {"name": "1. No Deadlock", "description": "P1 waits for R2, but P2 holds it and needs nothing more, so it finishes and frees R2.",
        "resources": {"R1": 1, "R2": 1},
        "processes": {"P1": P({"R1": 1, "R2": 1}, {"R1": 1}, {"R2": 1}), "P2": P({"R2": 1}, {"R2": 1})},
        "expected": {"deadlocked": [], "single_cycle": False}},
    "simple_deadlock": {"name": "2. Simple Circular Deadlock", "description": "P1 holds R1 and wants R2; P2 holds R2 and wants R1.",
        "resources": {"R1": 1, "R2": 1},
        "processes": {"P1": P({"R1": 1, "R2": 1}, {"R1": 1}, {"R2": 1}), "P2": P({"R1": 1, "R2": 1}, {"R2": 1}, {"R1": 1})},
        "expected": {"deadlocked": ["P1", "P2"], "single_cycle": True}},
    "three_process": {"name": "3. Three-Process Circular Deadlock", "description": "P1->P2->P3->P1 circular wait over three single-instance resources.",
        "resources": {"R1": 1, "R2": 1, "R3": 1},
        "processes": {"P1": P({"R1": 1, "R2": 1}, {"R1": 1}, {"R2": 1}), "P2": P({"R2": 1, "R3": 1}, {"R2": 1}, {"R3": 1}),
                      "P3": P({"R3": 1, "R1": 1}, {"R3": 1}, {"R1": 1})},
        "expected": {"deadlocked": ["P1", "P2", "P3"], "single_cycle": True}},
    "multi_instance": {"name": "4. Multiple Instances (cycle, no deadlock)", "description": "P1 and P2 form a wait-for cycle, but R1 has 2 instances and P3 (holding one) can finish and break it.",
        "resources": {"R1": 2, "R2": 1},
        "processes": {"P1": P({"R1": 1, "R2": 1}, {"R1": 1}, {"R2": 1}), "P2": P({"R1": 1, "R2": 1}, {"R2": 1}, {"R1": 1}),
                      "P3": P({"R1": 1}, {"R1": 1})},
        "expected": {"deadlocked": [], "single_cycle": True}},
    "recoverable": {"name": "5. Recoverable Deadlock", "description": "P1/P2 deadlock; P3 is a bystander. Terminating the cheapest victim (P1) frees R1 so P2 can proceed.",
        "resources": {"R1": 1, "R2": 1, "R3": 2},
        "processes": {"P1": P({"R1": 1, "R2": 1}, {"R1": 1}, {"R2": 1}, pr=1, cost=1, prog=2),
                      "P2": P({"R1": 1, "R2": 1}, {"R2": 1}, {"R1": 1}, pr=4, cost=5, prog=6),
                      "P3": P({"R3": 1}, {"R3": 1}, pr=2, cost=2)},
        "expected": {"deadlocked": ["P1", "P2"], "victim": "P1", "single_cycle": True}},
    "bankers_safe": {"name": "Banker: Safe State (textbook)", "description": "Classic 5-process, 3-resource example. Safe sequence exists (P1, P3, P4, P0, P2).",
        "resources": {"A": 10, "B": 5, "C": 7},
        "processes": {"P0": P({"A": 7, "B": 5, "C": 3}, {"B": 1}), "P1": P({"A": 3, "B": 2, "C": 2}, {"A": 2}),
                      "P2": P({"A": 9, "B": 0, "C": 2}, {"A": 3, "C": 2}), "P3": P({"A": 2, "B": 2, "C": 2}, {"A": 2, "B": 1, "C": 1}),
                      "P4": P({"A": 4, "B": 3, "C": 3}, {"C": 2})},
        "expected": {"deadlocked": [], "safe": True}},
    "bankers_unsafe": {"name": "Banker: Unsafe but NOT deadlocked", "description": "Nothing is waiting, yet if both ask for their max, deadlock follows. Unsafe != deadlocked.",
        "resources": {"R": 2},
        "processes": {"P1": P({"R": 2}, {"R": 1}), "P2": P({"R": 2}, {"R": 1})},
        "expected": {"deadlocked": [], "safe": False}},
}
