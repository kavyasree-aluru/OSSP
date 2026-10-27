# Presentation Kit
## 6-minute demo script
1. (0:00) Problem: why deadlocks matter; Coffman conditions (Learn page).
2. (0:45) Load **Simple Circular Deadlock**: banner turns red; show graph with red cycle.
3. (1:30) Deadlock Detection page: wait-for path, then Work/Finish steps showing why P1, P2 cannot finish.
4. (2:30) Load **Multiple Instances**: graph cycle exists, algorithm 1 says *inconclusive*, algorithm 2 says no deadlock - the key theory point.
5. (3:30) Load **Recoverable Deadlock** -> Recovery Center -> Recommend victim (cost table) -> Terminate -> before/after table says RESOLVED only after re-detection.
6. (4:30) Banker's page: safe sequence P1,P3,P4,P0,P2; unsafe scenario shows unsafe != deadlocked.
7. (5:15) What-if, Challenge Mode, CSV/printable report. (5:45) Tests: `python -m unittest discover -s tests -t .`.
## Slide outline
1 Title/team; 2 Problem & motivation; 3 Objectives & scope; 4 Deadlock theory; 5 Architecture diagram; 6 State model & invariants; 7 Algorithms (3); 8 Recovery & cost model; 9 Innovation (explainable, what-if, risk, challenge); 10 Live demo; 11 Testing (real results); 12 Impact, limits, future work; 13 Team roles.
## Likely judge questions
- *Why is a cycle not always deadlock?* With multiple instances another process may release an instance and break the wait (scenario 4).
- *Detection vs avoidance?* Detection checks a state that already exists; Banker's refuses requests that could lead to unsafe states; unsafe is not deadlocked.
- *Complexity?* Detection/safety O(m n^2).
- *Is the risk score a probability?* No, a labeled heuristic.
- *Does preemption fully fix it?* Only if re-detection says so; the victim is rolled back (progress reset).
- *How do you avoid starvation in victim selection?* Not handled: repeated victims are possible (listed limitation; could add aging).
## Team roles (adapt to team size)
Backend algorithms; Flask API + state; Frontend/graph; Testing + docs; Presentation/GitHub. For 3 people merge testing+docs into backend/frontend. Track contributions via GitHub commits/PRs.
