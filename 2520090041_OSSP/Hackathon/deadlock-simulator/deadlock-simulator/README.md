# Deadlock Detection and Recovery Simulator (OSSP Hackathon)
Interactive Flask + JavaScript simulator that models processes/resources, builds a Resource Allocation Graph, detects deadlock (wait-for graph and multiple-instance Work/Finish), analyzes safety with the Banker's algorithm, and recovers by termination or preemption - verifying every recovery by re-running detection.

## Problem & objectives
See [docs/problem_statement.md](docs/problem_statement.md): teach and demonstrate deadlock detection/recovery correctly, including why a graph cycle is not always a deadlock.

## Features
Dashboard; process/resource managers with validation; zoom/pan RAG with legend and red highlighting; wait-for and multiple-instance detection with explanations; Banker's safety module; recovery (terminate, terminate-all, preempt) with cost-based victim recommendation and before/after metrics; step-by-step playground; 5 scenarios + 2 Banker scenarios; event log, JSON persistence, CSV export, printable report; what-if analysis, heuristic risk indicator, learn page, challenge mode.

## Stack
HTML/CSS/JS + SVG, Python Flask, JSON history, `unittest`.

## Setup & run
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py            # open http://localhost:5000
python -m unittest discover -s tests -t . -v
```

## Architecture
See [docs/architecture.md](docs/architecture.md) (Mermaid diagram) and [docs/algorithms.md](docs/algorithms.md).

## Scenarios and expected results
| Scenario | Wait-for cycle | Multi-instance result |
|---|---|---|
| 1 No deadlock | no | none deadlocked (P2 then P1 finish) |
| 2 Simple circular | yes | P1, P2 deadlocked |
| 3 Three-process | yes | P1, P2, P3 deadlocked |
| 4 Multiple instances | yes (inconclusive) | none deadlocked (P3, P2, P1 finish) |
| 5 Recoverable | yes | P1, P2; victim P1 (score 8); terminating P1 resolves |
| Banker safe | - | safe: P1, P3, P4, P0, P2 |
| Banker unsafe | - | unsafe, but no deadlock |
These are asserted in `tests/`.

## Screenshots
Run the app, load each scenario, and save screenshots into `docs/screenshots/` (none are included yet), then link them here.

## Limitations / future scope
In-memory single-user model (one global simulation); preemption model is simplified (victim rolled back, not re-queued); no starvation/aging in victim choice; Banker's request-check (resource-request algorithm) not included; UI not covered by automated browser tests.

## Team contributions
Fill in after work is done (see roles in docs/presentation.md).

## GitHub
```bash
git init && git add . && git commit -m "feat: deadlock simulator core algorithms and tests"
git branch -M main && git remote add origin https://github.com/<user>/deadlock-simulator.git && git push -u origin main
```
Commit in small meaningful steps (backend, tests, UI, docs).
