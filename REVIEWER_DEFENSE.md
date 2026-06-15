# Reviewer Defense Sheet — TA-MAPPO (anticipated objections & honest answers)

> **Created:** 2026-06-14
> Purpose: a single reference of likely reviewer objections with **honest** answers and the
> phrasing to use / avoid. Line refs are to `swarm_env_step_B10.py` (env) and
> `train_step_B10_extended_v14.py` (policy), verified against code.
> **Companions:** [`PHASE_C_TRUST_DESIGN.md`](PHASE_C_TRUST_DESIGN.md), [`PARAMETER_JUSTIFICATION.md`](PARAMETER_JUSTIFICATION.md), [`FINAL_PARAMETER.md`](FINAL_PARAMETER.md), [`V14_8_0M_COMM_RANGE_PLAN.md`](V14_8_0M_COMM_RANGE_PLAN.md).

> **GOLDEN RULE:** state assumptions as **design choices**, never as **proven/optimal**. The only
> things that get rejected are *false claims*, *no novelty*, *no evidence*, and *no baselines* —
> not simplifying assumptions (every published paper, incl. our near-twin Chi et al. 2023, has them).

---

## ⚠️ Ablations NOT run (do NOT claim "optimal" for any of these)

These were never swept. Describe each as "a representative design choice"; if a reviewer presses,
the honest answer is "an ablation would settle the exact value."

- **History length = 5** — never ablated (no {0,3,5,10} sweep).
- **Arena size 20×20 m** — never ablated (no {15,20,25} sweep).
- **Swarm size 10** — never ablated (no {6,10,14} sweep).
- **Communication range 8 m** — single value, never swept.
- **Stagnation thresholds (40 / 25 steps)** — design choices, not tuned via sweep.

✅ What WAS empirically calibrated: **obstacle density** (10,000-map BFS sweep, Wilson CIs → ceiling 0.27). Lean on this as the rigor highlight.

---

## 1. CTDE — "your actor uses privileged/global info"

- **Goal direction (Dijkstra `to_goal`/`dist_goal`, env L74–163, used L383–384):** NOT a CTDE
  violation — it's static-environment knowledge, computed per-agent on a locally-held / SLAM map,
  independent of other agents. **Say:** hierarchical navigation (global planner + learned local
  controller). **Don't say:** "mapless" or "learns pathfinding."
- **Neighbour channel (rel pos/vel, dims 54–98, L426–438):** in **base v14 it is unlimited
  all-to-all** — that *would* be attacked. **Fix:** use the **8 m comm-range variant**
  (`swarm_env_step_B10_8_0m.py`, L27/L423) → "received via limited-range communication." Cite UWB.
- **Critic (global 520-D):** training-only, **discarded at execution** (verified L40–42:
  `forward_actor` uses `features[:, :130]` only). **Say this explicitly.**

## 2. CTDE — "the wall-glide / stagnation uses hidden state"

- Wall-glide (L391–413) triggers at `steps_stagnant > 40`; its inputs — own stagnation counter,
  own LiDAR, onboard Dijkstra dir, and a **1.2 m** local block check (L542) — are **all local**.
- Stagnation is detected from the agent's **own 25-step position memory** (`stagnation_position_history`,
  L548–553) + a running counter — **onboard memory**, like a classical controller's integrator.
- **There is NOT just one memory — there are several onboard temporal-state mechanisms** (all local,
  all reconstructable onboard, none global):
  | Mechanism | What it does | Code |
  |---|---|---|
  | `position_history` (5) | short-horizon motion shape → in the observation (dims 120–129) | L447–455 |
  | `stagnation_position_history` (25) | "no net progress" detection (`is_stagnant`) | L548–553 |
  | `steps_stagnant` counter | triggers wall-glide at `> 40` | L555–582 / L391 |
  | `blocked_steps` counter | **patience-then-escalation** when blocked by a drone | L560–573 |
  | `best_dist_to_goal` | best progress so far (own memory) | L555–558 |
- **`blocked_steps` (patience logic, L560–573):** when blocked by a drone in front (within 1.2 m):
  `blk ≤ 25` → grace period (`steps_stagnant` held at 0, `+0.5` reward if nearly stopped → polite
  waiting); `25 < blk ≤ 50` → patience reward **decays** `(1 − (blk−25)/25)` and `steps_stagnant`
  starts rising; `blk > 50` → **escalating penalty** (up to `−0.15`) so an agent cannot learn to wait
  behind traffic forever. Inputs are own speed + a 1.2 m local block check → **local/onboard**.
- **Framing:** separate **the policy** (Markov function of the 130-D obs) from **the onboard
  observation-builder + reward/state machine** (stateful: maintains the counters above, injects
  wall-glide into `to_goal`). Both are decentralised/onboard. **Don't say** "stateless reactive policy
  over a self-contained observation" — there IS onboard memory (multiple counters); say so.

## 3. Observation design — "why 5-step history in the actor?" / "why 5 vs the 25 used for stagnation?"

- The obs carries **5 past positions** (`rel_hist`, dims 120–129); stagnation uses a **separate
  25-step** buffer (NOT in the obs).
- **Why 5:** velocity (already in obs) is instantaneous; the 5-step trajectory captures the *shape*
  of recent motion (oscillation, deceleration) → short-horizon temporal context (~0.5 s at 10 Hz),
  mitigating partial observability. Window kept short to bound obs size.
- **Why 5 (actor) vs 25 (stagnation):** different timescales/purposes — short context for *acting*
  vs long window for *detecting no-progress*; the 25-step signal reaches the policy only via the
  wall-glide, so raw 25 positions never enter the obs.
- **Honest limits:** (a) history length was **never ablated**; (b) it *may* be partly redundant with
  velocity — only an ablation {0,3,5,10} would prove it earns its slot; (c) the exact 130-D layout is
  partly **frozen for weight compatibility** across versions (implementation reason — keep out of the
  paper's scientific justification). **Say:** "a 5-step window as a design choice." **Don't say:**
  "we found 5 to be optimal."

## 4. "Too much is hand-engineered, not learned"

- Dijkstra guidance + wall-glide are **classical/hand-coded**; the RL learns coordination, collision
  avoidance, and (Phase C) trust. **Frame as a hybrid architecture** — onboard classical modules +
  learned MARL policy. **Don't claim** end-to-end / learned-from-scratch navigation.

## 5. "Why 10 drones / 20×20 m?"

- Both are **design choices** (never ablated). **20×20:** anchor to sensor ratios (LiDAR 12 m = 60%,
  comms 8 m = 40% of field → genuinely partial observability). **10 drones:** moderate swarm size +
  clean adversary sweep (1–4 traitors = 10–40%, worst case 6/4 = bare honest majority). Both are
  standard in swarm-RL (sizes range 3–50; arenas 2.8 m–175 m). **Don't claim** optimal/required.
  See [`PARAMETER_JUSTIFICATION.md`](PARAMETER_JUSTIFICATION.md).

## 6. "Bio-inspired is just a buzzword"

- Ground in **Artificial Immune Systems / Danger Theory** (real field). Map: self/non-self =
  honest/traitor; antigen = broadcast-vs-LiDAR mismatch; **danger signal** = a broadcast that would
  steer into danger (ties to existing TTC/proximity rewards, L597–613); adaptive response = trust
  decay/recovery; tolerance = avoid false-distrust. Two layers: flocking (swarm) + immune (trust).
  **Say:** "inspired by," functional analogy — **not** biophysical fidelity. See [`PHASE_C_TRUST_DESIGN.md`](PHASE_C_TRUST_DESIGN.md) §4.

## 7. "This is already done — Chi et al. 2023 (Biomimetics)"

- Their work: **external** enemy (predator–prey), wolf-pack **grouping for scalability**, 2D
  mass-point, **no obstacles/LiDAR/trust**. Ours: **internal traitors**, **immune/T-cell trust for
  resilience**, obstacle+LiDAR navigation. **One-liner:** *"Unlike Chi et al. (2023), which counters
  an external adversary via a pack-hunting grouping mechanism for scalability, we counter insider
  adversaries via an immune-inspired adaptive trust mechanism in an obstacle-rich, LiDAR-sensed
  navigation task."* (This paper also supports ~12-agent swarms and that Biomimetics publishes this.)

---

## What is GENUINELY still needed (not framing — real work)

1. **Baselines** — compare trust-mechanism vs no-trust (and ideally vs a non-adaptive/binary filter)
   under traitors. This is the main thing a reviewer will require for the *contribution*, not the
   parameter choices.
2. **Phase-C results** — actual honest-drone survival vs number/type of traitors, with Wilson CIs.
   (Until then, any "how many survive" number is a hypothesis — do not state one.)
3. **Optional but strong:** the ablations above (history length, arena, swarm, comm range) — convert
   "design choice" into "robust across settings."

## Minor code hygiene to fix before sharing code
- `swarm_env_step_B10.py` L407 comment says `alpha=0.35` but L408 sets `alpha = 0.55` — fix the comment.
