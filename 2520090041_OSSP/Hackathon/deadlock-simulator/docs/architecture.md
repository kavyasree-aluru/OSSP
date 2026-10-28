# Architecture
```mermaid
flowchart LR
  UI[Browser: HTML/CSS/JS + SVG graph] -- REST/JSON --> API[app.py Flask routes]
  API --> SIM[simulation.py state + atomic ops + invariants]
  API --> DET[detection.py]
  API --> BNK[bankers.py]
  API --> REC[recovery.py]
  API --> SCN[scenarios.py]
  SIM --> HIS[history.py JSON log + CSV]
  REC --> SIM
```
Data flow: UI action -> REST call -> `Simulation` mutation (deep-copy snapshot, rollback on any error, invariant check) -> algorithms read an immutable matrix view (`matrices()`) -> JSON state back -> UI re-renders. Algorithm modules are pure functions with no Flask/UI imports, so they are unit-tested independently.
State model: `resources{name:total}`, `procs{pid:{status,max,alloc,req,priority,cost,progress}}`. Invariant: total = available + sum(alloc); no negatives; alloc+req <= max.
