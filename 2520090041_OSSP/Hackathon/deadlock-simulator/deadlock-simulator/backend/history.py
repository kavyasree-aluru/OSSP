import csv, io, json, os, time


class History:
    def __init__(self, path=None):
        self.path, self.events, self.records = path, [], []
        if path and os.path.exists(path):
            try:
                d = json.load(open(path))
                self.events, self.records = d.get("events", []), d.get("records", [])
            except (ValueError, OSError):
                pass

    def event(self, kind, msg):
        self.events.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "message": msg})
        self._save()

    def record(self, rec):
        rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.records.append(rec)
        self._save()

    def clear(self):
        self.events, self.records = [], []
        self._save()

    def _save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            json.dump({"events": self.events[-1000:], "records": self.records[-200:]}, open(tmp, "w"))
            os.replace(tmp, self.path)

    def events_csv(self):
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["time", "kind", "message"])
        w.writerows([e["time"], e["kind"], e["message"]] for e in self.events)
        return out.getvalue()


def state_csv(m):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["row"] + [f"{k}_{r}" for k in ("max", "alloc", "request") for r in m["res"]])
    for i, p in enumerate(m["pids"]):
        w.writerow([p] + m["max"][i] + m["alloc"][i] + m["request"][i])
    pad = [""] * len(m["res"])
    w.writerow(["TOTAL"] + pad + m["total"] + pad)
    w.writerow(["AVAILABLE"] + pad + m["available"] + pad)
    return out.getvalue()
