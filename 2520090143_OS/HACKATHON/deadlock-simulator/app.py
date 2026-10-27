import os
from flask import Flask, jsonify, request, render_template, Response
from backend.simulation import Simulation, SimError
from backend.detection import detect_single_instance, detect_multi_instance, risk_indicator
from backend import bankers, recovery
from backend.history import History, state_csv
from backend.scenarios import SCENARIOS


def create_app(history_path=None):
    app = Flask(__name__)
    sim = Simulation(History(history_path))

    def body():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            raise SimError("JSON object body required")
        return d

    def view():
        m = sim.matrices()
        try:
            bank = bankers.safety(m)
        except ValueError as e:
            bank = {"safe": None, "error": str(e), "steps": [], "sequence": [], "need": []}
        procs = {p: {**v} for p, v in sim.procs.items()}
        return {"matrices": m, "processes": procs, "resources": dict(sim.resources),
                "available": dict(zip(m["res"], m["available"])),
                "single": detect_single_instance(m), "multi": detect_multi_instance(m),
                "banker": bank, "risk": risk_indicator(m)}

    @app.errorhandler(SimError)
    def sim_error(e):
        return jsonify(error=str(e)), e.status

    @app.errorhandler(404)
    def nf(e):
        return jsonify(error="Not found"), 404

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def state():
        return jsonify(view())

    @app.post("/api/resources")
    def add_resource():
        d = body(); sim.add_resource(d.get("name"), d.get("total")); return jsonify(view()), 201

    @app.put("/api/resources/<name>")
    def set_total(name):
        sim.set_total(name, body().get("total")); return jsonify(view())

    @app.delete("/api/resources/<name>")
    def del_resource(name):
        sim.remove_resource(name); return jsonify(view())

    @app.post("/api/processes")
    def add_process():
        d = body()
        sim.add_process(d.get("pid"), d.get("max", {}), d.get("priority", 1), d.get("cost", 1))
        return jsonify(view()), 201

    @app.delete("/api/processes/<pid>")
    def del_process(pid):
        sim.remove_process(pid); return jsonify(view())

    @app.post("/api/request")
    def req():
        d = body(); out = sim.request(d.get("pid"), d.get("resource"), d.get("count"))
        return jsonify({**view(), "result": out})

    @app.post("/api/release")
    def rel():
        d = body(); sim.release(d.get("pid"), d.get("resource"), d.get("count")); return jsonify(view())

    @app.post("/api/finish")
    def fin():
        sim.finish(body().get("pid")); return jsonify(view())

    @app.post("/api/detect")
    def detect():
        v = view()
        sim.history.event("detect", "Detection: " + (", ".join(v["multi"]["deadlocked"]) or "no deadlock")
                          + f" | wait-for verdict: {v['single']['verdict']}")
        sim.history.record({"type": "detection", "deadlocked": v["multi"]["deadlocked"],
                            "verdict": v["single"]["verdict"], "state": sim.matrices()})
        return jsonify(v)

    @app.get("/api/recommend")
    def recommend():
        return jsonify(recovery.recommend(sim))

    @app.post("/api/recover")
    def recover():
        d = body()
        res = recovery.execute(sim, d.get("strategy"), d.get("pid"), d.get("resource"), d.get("count"))
        return jsonify({"recovery": res, "state": view()})

    @app.get("/api/scenarios")
    def scenarios():
        return jsonify([{"id": k, "name": v["name"], "description": v["description"], "expected": v["expected"]}
                        for k, v in SCENARIOS.items()])

    @app.post("/api/scenarios/<sid>/load")
    def load(sid):
        if sid not in SCENARIOS:
            return jsonify(error="Unknown scenario"), 404
        sim.load(SCENARIOS[sid]); sim.history.event("scenario", f"Loaded scenario: {SCENARIOS[sid]['name']}")
        return jsonify(view())

    @app.post("/api/reset")
    def reset():
        sim.resources, sim.procs = {}, {}; sim.history.clear(); return jsonify(view())

    @app.post("/api/whatif")
    def whatif():
        d, f = body(), sim.fork()
        act, pid = d.get("action"), d.get("pid")
        before = recovery.summary(f)
        if act == "terminate": f.terminate(pid)
        elif act == "preempt": f.preempt(pid, d.get("resource"), d.get("count"))
        elif act == "add_instance":
            r = d.get("resource"); f.set_total(r, f.resources.get(r, 0) + int(d.get("count", 1)))
        elif act == "cancel_request": f.cancel_request(pid, d.get("resource"))
        else: raise SimError("Unknown what-if action")
        after = recovery.summary(f)
        return jsonify({"before": before, "after": after,
                        "text": ("Deadlock would be RESOLVED." if before["deadlocked"] and not after["deadlocked"]
                                 else "Deadlock would REMAIN." if after["deadlocked"] else "No deadlock either way."),
                        "real_state_unchanged": True})

    @app.get("/api/history")
    def history():
        return jsonify(events=sim.history.events, records=sim.history.records)

    @app.get("/api/export/events.csv")
    def ev_csv():
        return Response(sim.history.events_csv(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=events.csv"})

    @app.get("/api/export/state.csv")
    def st_csv():
        return Response(state_csv(sim.matrices()), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=state.csv"})

    @app.get("/report")
    def report():
        return render_template("report.html", v=view(), events=sim.history.events, records=sim.history.records)

    app.sim = sim
    return app


if __name__ == "__main__":
    create_app(os.path.join(os.path.dirname(__file__), "data", "history.json")).run(debug=False, port=5000)
