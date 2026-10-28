"""Simulation state + resource allocation logic. Every mutation is atomic (rolled back on error)."""
import copy, functools
from .history import History


class SimError(ValueError):
    status = 400


class NotFound(SimError):
    status = 404


def atomic(fn):
    @functools.wraps(fn)
    def wrap(self, *a, **k):
        snap = copy.deepcopy((self.resources, self.procs))
        try:
            out = fn(self, *a, **k)
            self.check_invariants()
            return out
        except Exception:
            self.resources, self.procs = snap
            raise
    return wrap


def _int(v, name, minimum=0):
    if isinstance(v, bool) or not isinstance(v, int):
        raise SimError(f"{name} must be an integer")
    if v < minimum:
        raise SimError(f"{name} must be >= {minimum}")
    return v


class Simulation:
    def __init__(self, history=None):
        self.history = history if history is not None else History()
        self.resources, self.procs = {}, {}

    def _p(self, pid):
        if pid not in self.procs or self.procs[pid]["status"] != "active":
            raise NotFound(f"Unknown or inactive process '{pid}'")
        return self.procs[pid]

    def _r(self, r):
        if r not in self.resources:
            raise NotFound(f"Unknown resource '{r}'")
        return r

    def active(self):
        return sorted(p for p, v in self.procs.items() if v["status"] == "active")

    def avail(self, r):
        return self.resources[r] - sum(p["alloc"][r] for p in self.procs.values())

    @atomic
    def add_resource(self, name, total):
        if not isinstance(name, str) or not name.strip():
            raise SimError("Resource name required")
        name = name.strip()
        if name in self.resources:
            raise SimError(f"Resource '{name}' already exists")
        self.resources[name] = _int(total, "Instance count", 1)
        for p in self.procs.values():
            p["max"][name] = p["alloc"][name] = p["req"][name] = 0
        self.history.event("resource", f"Added resource {name} x{total}")

    @atomic
    def set_total(self, name, total):
        self._r(name)
        total = _int(total, "Instance count", 1)
        held = sum(p["alloc"][name] for p in self.procs.values())
        if total < held:
            raise SimError(f"Cannot set {name} to {total}: {held} instances are allocated")
        if any(p["max"][name] > total for p in self.procs.values()):
            raise SimError(f"Cannot set {name} to {total}: a process has a larger maximum claim")
        self.resources[name] = total
        self._grant_pending()
        self.history.event("resource", f"Set {name} total to {total}")

    @atomic
    def remove_resource(self, name):
        self._r(name)
        if any(p["alloc"][name] or p["req"][name] for p in self.procs.values()):
            raise SimError(f"Resource {name} is in use; release/cancel first")
        del self.resources[name]
        for p in self.procs.values():
            for k in ("max", "alloc", "req"):
                del p[k][name]
        self.history.event("resource", f"Removed resource {name}")

    @atomic
    def add_process(self, pid, maxclaim, priority=1, cost=1):
        if not isinstance(pid, str) or not pid.strip():
            raise SimError("Process id required")
        pid = pid.strip()
        if pid in self.procs:
            raise SimError(f"Process '{pid}' already exists")
        mx = {r: 0 for r in self.resources}
        for r, v in (maxclaim or {}).items():
            self._r(r)
            mx[r] = _int(v, f"Max claim for {r}")
            if mx[r] > self.resources[r]:
                raise SimError(f"Max claim for {r} exceeds total instances ({self.resources[r]})")
        z = lambda: {r: 0 for r in self.resources}
        self.procs[pid] = {"status": "active", "max": mx, "alloc": z(), "req": z(),
                           "priority": _int(priority, "Priority", 1), "cost": _int(cost, "Recovery cost", 1),
                           "progress": 0}
        self.history.event("process", f"Added process {pid}")

    @atomic
    def remove_process(self, pid):
        if pid not in self.procs:
            raise NotFound(f"Unknown process '{pid}'")
        del self.procs[pid]
        self._grant_pending()
        self.history.event("process", f"Removed process {pid}")

    def _grant_pending(self):
        changed = True
        while changed:
            changed = False
            for pid in self.active():
                p = self.procs[pid]
                if any(p["req"].values()) and all(p["req"][r] <= self.avail(r) for r in self.resources):
                    for r in self.resources:
                        p["alloc"][r] += p["req"][r]
                        p["req"][r] = 0
                    p["progress"] += 1
                    self.history.event("grant", f"Pending request of {pid} granted")
                    changed = True

    @atomic
    def request(self, pid, r, n):
        p, r, n = self._p(pid), self._r(r), _int(n, "Count", 1)
        if p["alloc"][r] + p["req"][r] + n > p["max"][r]:
            raise SimError(f"{pid} would exceed its declared maximum claim for {r} ({p['max'][r]})")
        if n <= self.avail(r) and not any(p["req"].values()):
            p["alloc"][r] += n
            p["progress"] += 1
            self.history.event("allocate", f"{pid} granted {n} x {r}")
            return "granted"
        p["req"][r] += n
        self.history.event("request", f"{pid} waits for {n} x {r} (available {self.avail(r)})")
        return "blocked"

    @atomic
    def release(self, pid, r, n):
        p, r, n = self._p(pid), self._r(r), _int(n, "Count", 1)
        if n > p["alloc"][r]:
            raise SimError(f"{pid} holds only {p['alloc'][r]} x {r}")
        p["alloc"][r] -= n
        self.history.event("release", f"{pid} released {n} x {r}")
        self._grant_pending()

    @atomic
    def finish(self, pid):
        p = self._p(pid)
        if any(p["req"].values()):
            raise SimError(f"{pid} is waiting and cannot complete")
        for r in self.resources:
            p["alloc"][r] = 0
        p["status"] = "completed"
        self.history.event("finish", f"{pid} completed and released all resources")
        self._grant_pending()

    @atomic
    def terminate(self, pid):
        p = self._p(pid)
        freed = {r: v for r, v in p["alloc"].items() if v}
        for r in self.resources:
            p["alloc"][r] = p["req"][r] = 0
        p["status"] = "terminated"
        self.history.event("recovery", f"Terminated {pid}, released {freed or 'nothing'}")
        self._grant_pending()
        return freed

    @atomic
    def preempt(self, pid, r, n):
        p, r, n = self._p(pid), self._r(r), _int(n, "Count", 1)
        if n > p["alloc"][r]:
            raise SimError(f"Cannot preempt {n} x {r} from {pid}: it holds {p['alloc'][r]}")
        p["alloc"][r] -= n
        p["progress"] = 0  # victim is rolled back
        self.history.event("recovery", f"Preempted {n} x {r} from {pid} (rolled back)")
        self._grant_pending()
        return {r: n}

    @atomic
    def cancel_request(self, pid, r):
        self._p(pid)["req"][self._r(r)] = 0
        self._grant_pending()

    def check_invariants(self):
        for r, t in self.resources.items():
            held = sum(p["alloc"][r] for p in self.procs.values())
            if held + self.avail(r) != t or self.avail(r) < 0:
                raise SimError(f"Invariant violated for {r}")
        for pid, p in self.procs.items():
            for r in self.resources:
                if min(p["alloc"][r], p["req"][r], p["max"][r]) < 0:
                    raise SimError(f"Negative value for {pid}/{r}")
                if p["alloc"][r] + p["req"][r] > p["max"][r]:
                    raise SimError(f"{pid} exceeds max claim on {r}")

    def matrices(self):
        res, pids = sorted(self.resources), self.active()
        row = lambda key, pid: [self.procs[pid][key][r] for r in res]
        return {"pids": pids, "res": res, "total": [self.resources[r] for r in res],
                "available": [self.avail(r) for r in res], "alloc": [row("alloc", p) for p in pids],
                "request": [row("req", p) for p in pids], "max": [row("max", p) for p in pids]}

    def fork(self):
        f = Simulation(History())
        f.resources, f.procs = copy.deepcopy((self.resources, self.procs))
        return f

    def load(self, data):
        """Load a scenario directly (bypasses granting); validated by invariants, rolled back on failure."""
        snap = copy.deepcopy((self.resources, self.procs))
        try:
            self.resources, self.procs = dict(data["resources"]), {}
            z = lambda: {r: 0 for r in self.resources}
            for pid, d in data["processes"].items():
                self.procs[pid] = {"status": "active", "max": {**z(), **d.get("max", {})},
                                   "alloc": {**z(), **d.get("alloc", {})}, "req": {**z(), **d.get("req", {})},
                                   "priority": d.get("priority", 1), "cost": d.get("cost", 1),
                                   "progress": d.get("progress", 1)}
            self.check_invariants()
        except Exception:
            self.resources, self.procs = snap
            raise
