"""Deadlock detection (pure functions; no Flask/UI dependency).
Input `m` is the matrix view from Simulation.matrices():
{pids, res, total, available, alloc, request, max}."""


def wait_for_edges(m):
    """Pi -> Pj if Pi requests resource r and Pj currently holds r."""
    edges = []
    for i, pi in enumerate(m["pids"]):
        for k, r in enumerate(m["res"]):
            if m["request"][i][k] > 0:
                for j, pj in enumerate(m["pids"]):
                    if j != i and m["alloc"][j][k] > 0:
                        edges.append({"from": pi, "to": pj, "resource": r})
    return edges


def find_cycle(nodes, edges):
    adj = {n: [] for n in nodes}
    for e in edges:
        adj[e["from"]].append(e["to"])
    color, stack = {n: 0 for n in nodes}, []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in adj[u]:
            if color[v] == 1:
                return stack[stack.index(v):] + [v]
            if color[v] == 0:
                c = dfs(v)
                if c:
                    return c
        stack.pop()
        color[u] = 2
        return None

    for n in nodes:
        if color[n] == 0:
            c = dfs(n)
            if c:
                return c
    return []


def detect_single_instance(m):
    """Algorithm 1: wait-for graph cycle detection.
    A cycle PROVES deadlock only if every resource type has exactly one instance."""
    edges = wait_for_edges(m)
    cycle = find_cycle(m["pids"], edges)
    single = all(t == 1 for t in m["total"])
    path = []
    for a, b in zip(cycle, cycle[1:]):
        e = next(e for e in edges if e["from"] == a and e["to"] == b)
        path.append(f'{a} waits for {e["resource"]} held by {b}')
    if cycle and single:
        verdict, note = "deadlock", "Cycle in a single-instance system: deadlock is guaranteed."
    elif cycle:
        verdict, note = "inconclusive", ("Cycle exists but some resource types have multiple instances, "
                                         "so a cycle is necessary, not sufficient. Run Algorithm 2.")
    else:
        verdict, note = "no_deadlock", "No cycle in the wait-for graph: no deadlock."
    return {"edges": edges, "cycle": cycle, "path": path, "single_instance": single,
            "verdict": verdict, "note": note}


def detect_multi_instance(m):
    """Algorithm 2: Work/Finish detection using Available, Allocation, Request."""
    n, res = len(m["pids"]), m["res"]
    work = list(m["available"])
    finish = [not any(row) for row in m["alloc"]]  # holds nothing -> cannot be part of a deadlock
    order, steps = [], []
    fmt = lambda v: "(" + ", ".join(f"{r}={x}" for r, x in zip(res, v)) + ")"
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(a <= b for a, b in zip(m["request"][i], work)):
                before = list(work)
                work = [w + a for w, a in zip(work, m["alloc"][i])]
                finish[i] = True
                order.append(m["pids"][i])
                steps.append({"process": m["pids"][i], "finished": list(order),
                              "work_before": before, "work_after": list(work),
                              "text": f'{m["pids"][i]} requests {fmt(m["request"][i])} <= Work {fmt(before)}, so it can '
                                      f'finish and release {fmt(m["alloc"][i])}. Work becomes {fmt(work)}.'})
                progress = True
    dead = [p for p, f in zip(m["pids"], finish) if not f]
    why = {m["pids"][i]: f'requests {fmt(m["request"][i])} but Work is only {fmt(work)}'
           for i in range(n) if not finish[i]}
    waiting = [p for i, p in enumerate(m["pids"]) if any(m["request"][i]) and finish[i]]
    text = ("No unfinished process can proceed. Deadlocked: " + ", ".join(dead) + "." if dead
            else "Every process can finish: no deadlock.")
    steps.append({"process": None, "finished": list(order), "work_before": work, "work_after": work, "text": text})
    return {"deadlocked": dead, "waiting": waiting, "completion_order": order,
            "steps": steps, "why_blocked": why, "final_work": work, "has_deadlock": bool(dead)}


def risk_indicator(m):
    """HEURISTIC (not a probability): mixes waiting ratio, resource contention and wait-for cycles."""
    n = len(m["pids"])
    if n == 0:
        return {"score": 0, "label": "Low", "heuristic": True}
    if detect_multi_instance(m)["has_deadlock"]:
        return {"score": 100, "label": "Deadlocked (verified)", "heuristic": False}
    waiting = sum(1 for row in m["request"] if any(row)) / n
    contended = sum(1 for k in range(len(m["res"]))
                    if sum(r[k] for r in m["request"]) > m["available"][k]) / max(1, len(m["res"]))
    cyc = 1 if find_cycle(m["pids"], wait_for_edges(m)) else 0
    score = round(100 * min(1, 0.4 * waiting + 0.3 * contended + 0.3 * cyc))
    return {"score": score, "label": "High" if score >= 60 else "Medium" if score >= 30 else "Low",
            "heuristic": True}
