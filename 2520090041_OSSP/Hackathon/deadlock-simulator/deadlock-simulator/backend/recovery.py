"""Recovery strategies: victim scoring, termination, preemption. Verifies results by re-detection."""
from .detection import detect_multi_instance
from .simulation import SimError

W = {"priority": 3, "held": 2, "cost": 2, "progress": 1}  # transparent weights


def victim_scores(sim, candidates):
    rows = []
    for pid in candidates:
        p = sim.procs[pid]
        held = sum(p["alloc"].values())
        parts = {"priority": W["priority"] * p["priority"], "held": W["held"] * held,
                 "cost": W["cost"] * p["cost"], "progress": W["progress"] * p["progress"]}
        rows.append({"pid": pid, "score": sum(parts.values()), "parts": parts, "held": held})
    return sorted(rows, key=lambda r: (r["score"], r["pid"]))


def recommend(sim):
    det = detect_multi_instance(sim.matrices())
    if not det["has_deadlock"]:
        return {"deadlocked": [], "message": "No deadlock - no recovery needed.", "ranking": []}
    ranking = victim_scores(sim, det["deadlocked"])
    v = ranking[0]
    wanted = {r for q in det["deadlocked"] if q != v["pid"] for r, c in sim.procs[q]["req"].items() if c}
    pre = [(r, n) for r, n in sim.procs[v["pid"]]["alloc"].items() if n and r in wanted]
    return {"deadlocked": det["deadlocked"], "ranking": ranking, "victim": v["pid"],
            "preempt_option": {"pid": v["pid"], "resource": pre[0][0], "count": pre[0][1]} if pre else None,
            "message": (f"Recommend {v['pid']}: lowest cost score {v['score']} = priority x{W['priority']} + "
                        f"resources held x{W['held']} + recovery cost x{W['cost']} + progress x{W['progress']}.")}


def summary(sim):
    m, det = sim.matrices(), detect_multi_instance(sim.matrices())
    return {"deadlocked": det["deadlocked"], "available": dict(zip(m["res"], m["available"])),
            "allocated": {r: t - a for r, t, a in zip(m["res"], m["total"], m["available"])},
            "active": len(m["pids"])}


def execute(sim, strategy, pid=None, resource=None, count=None):
    before = summary(sim)
    if not before["deadlocked"]:
        raise SimError("No deadlock detected; recovery is not needed")
    freed = {}
    if strategy == "terminate":
        if pid not in before["deadlocked"]:
            raise SimError(f"{pid} is not a deadlocked process")
        freed, affected = sim.terminate(pid), [pid]
    elif strategy == "terminate_all":
        for q in before["deadlocked"]:
            for r, n in sim.terminate(q).items():
                freed[r] = freed.get(r, 0) + n
        affected = before["deadlocked"]
    elif strategy == "preempt":
        if pid not in before["deadlocked"]:
            raise SimError(f"{pid} is not a deadlocked process")
        if resource not in sim.resources or isinstance(count, bool) or not isinstance(count, int):
            raise SimError("Preemption needs a valid resource and integer count")
        if not any(sim.procs[q]["req"].get(resource, 0) for q in before["deadlocked"] if q != pid):
            raise SimError(f"No other deadlocked process is waiting for {resource}; preemption would not help")
        freed, affected = sim.preempt(pid, resource, count), [pid]
    else:
        raise SimError("Unknown strategy (use terminate, terminate_all, preempt)")
    after = summary(sim)
    resolved = not after["deadlocked"]
    sim.history.record({"type": "recovery", "strategy": strategy, "before": before, "after": after, "freed": freed})
    return {"strategy": strategy, "before": before, "after": after, "freed": freed, "affected": affected,
            "resolved": resolved,
            "message": ("Verified: re-running detection shows no deadlock." if resolved else
                        "NOT resolved: deadlock persists for " + ", ".join(after["deadlocked"]) + ".")}
