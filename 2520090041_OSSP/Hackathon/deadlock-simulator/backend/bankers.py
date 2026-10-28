"""Banker's safety algorithm: deadlock AVOIDANCE analysis (separate from detection)."""


def safety(m):
    pids, res = m["pids"], m["res"]
    need = [[mx - a for mx, a in zip(rm, ra)] for rm, ra in zip(m["max"], m["alloc"])]
    if any(x < 0 for row in need for x in row):
        raise ValueError("Allocation exceeds maximum claim for some process")
    work, finish, seq, steps = list(m["available"]), [False] * len(pids), [], []
    fmt = lambda v: "(" + ", ".join(f"{r}={x}" for r, x in zip(res, v)) + ")"
    moved = True
    while moved:
        moved = False
        for i in range(len(pids)):
            if not finish[i] and all(a <= b for a, b in zip(need[i], work)):
                before = list(work)
                work = [w + a for w, a in zip(work, m["alloc"][i])]
                finish[i] = True
                seq.append(pids[i])
                steps.append({"process": pids[i], "text": f"{pids[i]} Need {fmt(need[i])} <= Work {fmt(before)}; "
                              f"it could run to completion and release {fmt(m['alloc'][i])}. Work = {fmt(work)}."})
                moved = True
    safe = all(finish)
    return {"safe": safe, "sequence": seq if safe else [], "need": need, "steps": steps,
            "stuck": [p for p, f in zip(pids, finish) if not f],
            "note": ("Safe: a sequence exists in which every process can finish with its maximum claim."
                     if safe else
                     "Unsafe: no guaranteed completion order exists. This is NOT the same as deadlock - "
                     "an unsafe state only means deadlock is possible if processes request their maximum.")}
