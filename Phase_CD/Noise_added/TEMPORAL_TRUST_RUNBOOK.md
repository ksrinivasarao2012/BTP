# TEMPORAL TRUST — self-contained runbook (P2/P4)

> **Purpose.** This file is a complete, cold-start handoff. A NEW chat with **no prior context** should be
> able to read ONLY this file plus the few files it points to, and execute the whole temporal-trust
> experiment: build a feasibility probe, read its result, decide whether to build the full filter, build &
> evaluate it, and know exactly how to react to every outcome.
>
> **How to use this in a new chat:** paste *"Read `Phase_CD/Noise_added/TEMPORAL_TRUST_RUNBOOK.md` and start
> at STEP 1"*. Then after each step you (the user) paste the printed result back; the assistant follows the
> "DECISION GATE / HOW TO REACT" block for that step.
>
> **Hard rules for the assistant (from CLAUDE.md):** (1) address the user as "Srinivasa,"; (2) **never run
> any command automatically** — always show the command and wait for explicit "go".

---

## 0. COLD-START CONTEXT (read these first, in order)

1. `Phase_CD/PAPER_MASTER_PLAN.md` — the whole project. Pay attention to **§5.7, §5.8, §5.10** (the noise
   results we are trying to improve) and **§6** (parameter justifications). This runbook attacks the ONE
   open weakness: §5.8 row σ=0.6 camouflage, where recall = 0.21 and recovery = +1.4 pp.
2. `Phase_CD/Noise_added/env_noisy_byzantine.py` — the env we instrument. Read it fully. Key members:
   - `self._sensed`  shape `(n_drones, M, 2)` — each drone's **noisy** view of the M real obstacles.
   - `self._in_range` shape `(n_drones, M)` bool — which real obstacles each drone currently senses
     (false if the drone is LiDAR-blind this step).
   - `self._sradii` shape `(M,)` — true radii.
   - `self._phantoms` shape `(P,3)` — fabricated obstacles (cols 0:2 = centers). Exact (no sensor noise).
   - `self.obstacles` — list of `(x,y,r)` TRUE obstacles (ground truth, for oracle association in the probe).
   - `self.positions[j]`, `self.lidar_blind[j]`, `self.lidar_range`, `self.communication_range`.
   - `self.traitor_indices` (ground-truth liars), `self.possible_agents`, `self.agents`,
     `self.agent_name_mapping`.
   - Trust knobs: `self.trust[idx,j]`, `self.trust_alpha`, `self.tau_trust`, `self.verify_eps`,
     `self.verify_k_sigma`. `predicted_traitors()` → `{i: set(predicted_j)}`.
   - `_sample_sensing()` makes ONE noise draw per step (keyed by `self.steps`), shared across observers.
     It is called inside `_fused_lidar`; after `env.step(...)` returns, `self._sensed/_in_range` are current.
3. `Phase_CD/Noise_added/eval_noise_robust.py` — **copy its scaffolding** (parallel `Pool`, `_init`,
   `_build_env`, `MAPPO_Policy_M0`, deterministic seeding, solvability retry, honest-drone denominator).
   The probe and the temporal eval should reuse this structure verbatim so results stay comparable.
4. `Phase_CD/Collab_Perception/env_byzantine_adaptive.py` — parent env; defines `attack_mode`
   ("wall"|"camouflage"), `camouflage_gap`, `_phantoms` placement, `predicted_traitors`.

**Environment / commands:**
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
# model under test (noise-robust base from Option C):
$M  = "models/noise_robust_ON_stage1_final.zip"
```

---

## 1. THE HYPOTHESIS AND THE MATH (why this might work — and might not)

**Problem.** At σ=0.6 the single-frame robust filter uses tolerance `eps = 0.6 + 4·0.6 = 3.0 m`. That band
is so wide that a **camouflage** phantom placed ~1 m from a real obstacle is never contradicted on any
single frame → recall 0.21. We widened `eps` to avoid false-accusing honest neighbors, and the attack hides
in exactly that widened band. A single frame **cannot** separate the two.

**Escape — temporal aggregation of the OFFSET VECTOR (not the scalar distance).**
For neighbor `j`'s report of an obstacle, define the per-frame **offset vector**
`d_t = (j's reported position) − (ego's own sensed position of the matched obstacle)`.
- **Honest j:** `d_t = noise_j(t) − noise_ego(t)` ~ `N(0, √2·σ)` → **zero-mean**. Average of K frames →
  magnitude shrinks like `√2·σ/√K`.
- **Liar (camouflage):** `d_t = gap − noise_ego(t)` → **mean = the gap vector (~1 m)**, does NOT average away.

So the discriminator is `‖ EWMA/mean of d_t ‖`. Predicted scales (σ=0.6, gap≈1 m):

| K (usable frames) | honest median ‖mean‖ | liar ‖mean‖ | separated? |
|---|---|---|---|
| 5  | ~0.45 m | ~1.0 m | marginal |
| 10 | ~0.32 m | ~1.0 m | yes |
| 20 | ~0.22 m | ~1.0 m | clean |

> ⚠ **Note the scalar trap:** the *distance* `‖d_t‖` does NOT average to zero for honest neighbors
> (it's ~0.85 m every frame). Only the **vector mean** cancels honest noise. The filter MUST accumulate
> vectors and threshold on the magnitude of the mean. This is the entire idea.

**Two ways this fails (be honest about both):**
- **A. Statistics fail** — separation doesn't appear even with perfect association (unlikely given the math,
  but possible if `gap` < honest spread or obstacles too dense). → abandon temporal trust; the
  fundamental-limit result in §5.10 stands.
- **B. Association fails** — the statistics exist but, under ~33% LiDAR dropout, usable K per (ego,neighbor)
  pair is too small, or nearest-neighbor matching mixes the phantom with the real obstacle it hugs. → the
  bottleneck is engineering, not statistics; consider learned temporal trust (P2) only if a stretch venue
  needs it, else report the limit.

We test A and B **separately** (STEP 1 = oracle association, STEP 2 = realistic association) so we always
know which one bit us.

**Also be honest about venue:** even a perfect temporal filter does **NOT** by itself unlock IEEE RA-L —
the Dijkstra goal-direction crutch (PAPER_MASTER_PLAN §7.3, P3, weeks of retrain) is a separate blocker.
Temporal trust is a **strong bonus section** for the target journal and *one of two* RA-L prerequisites.
Frame it that way; do not oversell.

> ⚠ **VENUE SUPERSEDED (2026-06-26):** this runbook predates the venue decision. Target is now **Elsevier
> *Robotics and Autonomous Systems*** (free subscription track); **MDPI *Drones* was ruled out by the NO-APC
> constraint.** Wherever this file says "MDPI"/"Drones" below (decision-tree leaves included), read it as the
> safe mid-tier target = Elsevier *RAS*. RA-L framing is unchanged.

---

## STEP 1 — PROBE A: does the signal exist with ORACLE association? (~2 h build+run)

**Goal:** measure, on σ=0.6 **camouflage** episodes, the distribution of `‖mean offset‖` for HONEST vs
PHANTOM obstacle reports, using ground truth to associate (so association can't be blamed). This tests the
STATISTICS only.

**Build `Phase_CD/Noise_added/probe_temporal_offset.py`** (no env edits — read env internals from outside):
- Reuse `eval_noise_robust.py` scaffolding: `MAPPO_Policy_M0`, `_init` (load model on CPU), parallel `Pool`,
  deterministic seeding + solvability retry, `_build_env` but with:
  `sensor_noise=0.6, false_obstacle_attack=True, traitor_indices=[0,1], attack_mode="camouflage",
   trust_defense=False` (defense OFF — we are only *observing*, not gating), `target_density=0.20`.
- Per episode, keep accumulators `acc[(idx, j, key)] = [sum_vec(2,), count]` where `key` identifies the
  matched obstacle and carries a label `honest|phantom`.
- After **each** `env.step(...)`, for every honest ego `idx` (not blind) and every neighbor `j` in comm
  range that is broadcasting (not blind, or a traitor):
  - `S = env._sensed[idx]`, `in_i = env._in_range[idx]`  (ego's sighted noisy views + mask).
  - **Honest reports of j** (always present if j sighted): for each real obstacle index `m` with
    `env._in_range[j][m]` AND `in_i[m]` (ego also sees m) AND `‖env.positions[idx]−obstacles[m][:2]‖ ≤
    lidar_range`: `d = env._sensed[j][m] − env._sensed[idx][m]`; add to `acc[(idx,j,("real",m))]`,
    label honest. (Oracle: same true index m on both sides — perfect association.)
  - **Phantom reports of j** (only if `j in traitor_indices`): for each phantom `p = env._phantoms[k,:2]`
    within `lidar_range` of ego: find the TRUE real obstacle nearest to p: `m* = argmin_m ‖p −
    obstacles[m][:2]‖`; if ego sights `m*` (`in_i[m*]`): `d = p − env._sensed[idx][m*]`; add to
    `acc[(idx,j,("phantom",k))]`, label phantom. (Oracle: we know it's a phantom and which real it hugs.)
- At episode end, for every accumulator with `count ≥ Kmin` (sweep `Kmin ∈ {1,5,10,20}` — report each),
  emit `mag = ‖sum_vec/count‖` tagged honest/phantom, and also emit `count` (the usable-K).
- Aggregate across all maps. **Print:**
  1. Honest `mag` percentiles (p50, p75, p90, p95) and Phantom `mag` percentiles (p5, p10, p25, p50).
  2. The **K (count) distribution** for both classes (median, p10) — this is the dropout diagnostic.
  3. A simple separability score: best single threshold's **AUC** (rank phantom vs honest by `mag`), and the
     "clean-gap" check `phantom_p10 − honest_p90`.
- Suggested run: 150 camouflage maps, 10 workers, k=2, fixed σ=0.6 (this is the hardest cell).

**RUN (show first, wait for go):**
```
& $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6
```

### DECISION GATE — STEP 1 (how to react to the printed numbers)
- **GREEN (statistics support it):** AUC ≥ 0.85 **and** `honest_p90 < phantom_p10` at some `Kmin ≤ 10`
  **and** median usable-K ≥ that `Kmin`. → The signal is real and reachable. **Go to STEP 2.**
- **AMBER (signal exists but K is thin):** AUC ≥ 0.85 only at `Kmin = 20` but median usable-K < 10. →
  Statistics fine, dropout starves the window. Options to report back and decide: (a) relax the regime
  (test σ=0.4 too — temporal trust may rescue the *moderate*-noise camouflage cell even if σ=0.6 stays a
  limit), or (b) accept σ=0.6 as the limit and claim temporal recovery for σ≤0.4 only. Still worth STEP 2.
- **RED (no separation):** AUC < 0.75 even with oracle association at Kmin=20. → The statistics don't
  support it (gap too small vs noise, or obstacles too dense). **STOP.** Do not build the filter. The
  §5.10 fundamental-limit result is the honest, final story. Update PAPER_MASTER_PLAN §8 P2 → "tested,
  negative" and move to paper drafting.

**Paste back to the new chat:** the full printed table (honest/phantom percentiles + K distribution + AUC),
and the chosen gate (GREEN/AMBER/RED).

---

## STEP 2 — PROBE B: does REALISTIC association preserve the separation? (~2 h)

Only if STEP 1 = GREEN or AMBER. Same probe, but **drop the oracle**: associate using only what a drone
actually has (its own noisy views + the raw broadcast list, no ground-truth indices, no "is-phantom" flag).

**Changes to the probe (add a `--assoc realistic` mode):**
- The neighbor `j` broadcasts a single mixed list `B_j` = (its sighted noisy reals) ⧺ (phantoms if traitor),
  with NO labels — exactly what `_fused_lidar` sees at `bc_c`.
- Ego associates each broadcast obstacle `o ∈ B_j` to **ego's nearest sighted obstacle** (`S[in_i]`),
  offset `d = o − nearest`. To get a *temporal* track per broadcast obstacle (so the fixed phantom
  accumulates a stable bias while honest reports of distinct obstacles don't smear), key the accumulator by
  the **ego-obstacle index of the nearest match** `m*` AND keep a per-(idx,j,m*) running vector mean.
  Then a phantom that always hugs real obstacle `m*` will dominate that bucket with a biased mean; honest
  reports of `m*` are zero-mean. **The risk:** the phantom and the honest report of the SAME real obstacle
  both land in bucket `m*` and the honest zero-mean reports dilute the phantom bias. So ALSO compute a
  second statistic that is robust to mixing: the **fraction of frames in bucket `m*` whose `‖d_t‖ > eps_tight`
  is consistently in the same half-plane** (directional persistence), or simpler: cluster the `d_t` vectors
  in a bucket into ≤2 modes (k-means k=2) and test if one mode has a persistent non-zero centroid. Report
  both the simple mean-bias and the cluster-based statistic.
- Label each bucket by ground truth POST-HOC only for scoring (a bucket "contains a phantom" if any phantom
  mapped to that `m*`). The *filter logic itself* uses no labels.

**RUN:**
```
& $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6 --assoc realistic
```

### DECISION GATE — STEP 2
- **GREEN:** realistic association keeps AUC ≥ 0.80 (mean-bias OR cluster statistic). → Build the filter
  (STEP 3) using whichever statistic scored best.
- **AMBER:** only the cluster statistic separates (mean-bias diluted by mixing). → Buildable but more
  complex; note it and proceed to STEP 3 with the cluster statistic.
- **RED:** AUC < 0.75 with realistic association though STEP 1 was GREEN. → **Association is the wall.**
  This is the precise justification for **learned** temporal trust (P2): a small classifier can learn the
  association+bias jointly. Decide with the user: build P2 only if targeting RA-L; otherwise report
  "single-frame limited; temporal separable in principle (STEP 1) but not with hand association" as a
  richer fundamental-limit result and go to paper drafting.

**Paste back:** AUC for mean-bias and cluster statistic, plus which gate.

---

## STEP 3 — BUILD the temporal filter into the env (only if STEP 2 ≥ AMBER)

**Do NOT touch** the pristine `swarm_env_step_B10_8_0m.py`. Edit only `env_noisy_byzantine.py` (the
experimental copy), additively.

**Design (hand-coded temporal trust, P4):**
- Add ctor knobs: `temporal_window` (target K, default 15), `temporal_bias_eps` (the green threshold from
  STEP 1/2, e.g. 0.5 m), `temporal_min_k` (min samples before a verdict, e.g. 6), keep `tau_trust`.
- Add per-pair vector accumulator `self._tbias[idx, j, m*] = (sum_vec, count)` (EWMA with the SAME
  `trust_alpha` philosophy, or a fixed sliding window). Reset on `reset()`.
- In `_fused_lidar`, in the per-neighbor loop where `trust_defense` is checked, replace/augment the
  single-frame `_ego_judgement` with the temporal rule:
  1. associate each broadcast obstacle to ego's nearest sighted obstacle `m*` (as in STEP 2 winner);
  2. update `self._tbias[idx,j,m*]` with `d = o − ego_sensed[m*]`;
  3. once `count ≥ temporal_min_k`, if `‖mean(d)‖ > temporal_bias_eps` for ANY `m*` of neighbor `j`,
     drive `self.trust[idx,j]` down (EWMA toward 0); else toward 1; gate as today (`< tau_trust` ⇒ skip j).
- **Keep the single-frame robust check as a fast path** for obvious open-space (wall) phantoms; temporal is
  the slow path that catches camouflage. They compose (logical OR on "contradicted").
- Keep `verify_k_sigma`/`verify_eps` for the single-frame path; the temporal path uses `temporal_bias_eps`,
  which can stay TIGHT (that's the whole point — temporal lets us avoid the 3.0 m widened band).

**Sanity self-test before evaluating:** run a 5-map debug print confirming (a) honest pairs keep
`‖mean(d)‖` small, (b) traitor pairs cross `temporal_bias_eps`, (c) `predicted_traitors()` now flags
camouflage at σ=0.6. Show the assistant's debug snippet to the user; run only on "go".

---

## STEP 4 — EVALUATE the temporal filter (wall + camouflage under noise)

Add a `temporal_on` condition to `eval_noise_robust.py` (or a sibling `eval_temporal.py` reusing its
scaffolding). Per noise level run the SAME columns as §5.7/5.8 plus the new one:
`base · attack · robust(single-frame) · temporal · temporal_no-harm(k=0)` with P/R for each defended col.

**RUN (show first):**
```
& $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 wall
& $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 camouflage
```

### DECISION GATE — STEP 4 (the result that decides the paper's strength)
Compare the **temporal** column against the **robust** column from §5.7/5.8 (esp. the σ=0.6 camouflage cell:
robust recall 0.21, recovery +1.4 pp):
- **WIN:** temporal raises σ=0.6 camouflage **recall ≥ 0.5** and **recovery ≥ +5 pp**, while **no-harm ≈
  base** (precision stays ≥ 0.9, no new false positives) and the wall numbers don't regress. → Major result.
  This is the "temporal memory breaks the noise-band limit" headline. → STEP 5 (write it up; reconsider RA-L
  *together with* the Dijkstra blocker).
- **PARTIAL:** temporal clearly beats robust at σ=0.4 camouflage but σ=0.6 stays hard. → Honest, still
  publishable upgrade: "temporal recovers moderate-noise camouflage; severe-noise remains the limit."
  → STEP 5.
- **NO-HARM FAILS:** temporal recovers recall but drops no-harm (precision < 0.85) — it false-accuses honest
  neighbors via association errors. → tighten `temporal_min_k`/`temporal_bias_eps`; if it can't get both,
  report as PARTIAL with the single-frame robust filter as the recommended default.
- **NO GAIN:** temporal ≈ robust everywhere. → the §5.10 limit is firm; keep single-frame robust as the
  contribution. Update P2 → "implemented, no measurable gain." Go to paper.

**Paste back:** the two full eval tables (wall + camouflage) with the temporal column, and the gate.

---

## STEP 5 — WRITE IT UP

Update `Phase_CD/PAPER_MASTER_PLAN.md`:
- New subsection **§5.11 Temporal trust** with the STEP 4 tables and the mechanism (zero-mean honest noise
  vs persistent lie bias). Reference STEP 1 probe as the evidence the mechanism is sound.
- §7 limitations: if WIN/PARTIAL, soften "fundamental limit" to "single-frame limit, recovered temporally
  at σ≤X"; if NO GAIN, strengthen §5.10 as the firm limit.
- §8: mark P2/P4 with the outcome (WIN/PARTIAL/NEG) and the exact numbers.
- §10 venue: restate honestly — RA-L still needs the Dijkstra-free retrain (P3) regardless; MDPI gets a
  stronger defense section either way.
- Save a memory file `temporal-trust-result.md` (type project) with the one-line outcome and link
  `[[option-c-perception-limit]]`, and add a line to `MEMORY.md`.

Then begin drafting the paper Methods/Results per PAPER_MASTER_PLAN §9.

---

## 6. FAIL-FAST SUMMARY (the whole decision tree on one screen)

```
STEP 1 (oracle assoc, σ=0.6 camo)
  RED  → STOP. §5.10 limit is final. Paper as-is (MDPI). P2 = tested-negative.
  AMBER→ STEP 2 (maybe restrict claims to σ≤0.4)
  GREEN→ STEP 2
STEP 2 (realistic assoc)
  RED  → association is the wall → P2-learned ONLY if RA-L wanted, else report richer limit.
  AMBER/GREEN → STEP 3 (build filter)
STEP 3 → self-test → STEP 4
STEP 4 (eval vs robust col)
  WIN     → §5.11 headline; reconsider RA-L *with* Dijkstra (P3).
  PARTIAL → §5.11 "moderate-noise recovery"; MDPI stronger.
  NO-HARM FAILS → tune; else PARTIAL with robust as default.
  NO GAIN → keep single-frame robust; §5.10 firm. Paper.
```

## 7. CHEAT-SHEET (env knobs used by probe + filter)

| knob | where | meaning |
|---|---|---|
| `sensor_noise` | NoisyByzantineEnv ctor | Gaussian σ (m) on sensed obstacle positions |
| `false_obstacle_attack`, `traitor_indices` | ctor | enable attack + which drones lie |
| `attack_mode` ("wall"/"camouflage"), `camouflage_gap` | parent (adaptive) | phantom placement |
| `trust_defense` | ctor | gate broadcasts by `self.trust < tau_trust` |
| `verify_eps`, `verify_k_sigma` | ctor | single-frame tolerance `eps = verify_eps + k_sigma·σ` |
| `trust_alpha`, `tau_trust` | ctor | EWMA decay + exclusion threshold |
| `_sensed`,`_in_range`,`_sradii`,`_phantoms`,`obstacles`,`positions`,`lidar_blind`,`lidar_range`,`communication_range` | members | read by the probe (no env edit needed) |
| `predicted_traitors()` | method | `{i: set(j)}` for P/R scoring |
| **NEW** `temporal_window`,`temporal_bias_eps`,`temporal_min_k` | add in STEP 3 | temporal-filter knobs |

## 8. FILE / COMMAND INDEX

```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe" ; cd "D:\Swarm\BTP"
$M  = "models/noise_robust_ON_stage1_final.zip"

# STEP 1 (oracle):     & $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6
# STEP 2 (realistic):  & $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6 --assoc realistic
# STEP 4 (eval):       & $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 wall
#                      & $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 camouflage
```
- Build new: `Phase_CD/Noise_added/probe_temporal_offset.py`, `Phase_CD/Noise_added/eval_temporal.py`.
- Edit (experimental copy only): `Phase_CD/Noise_added/env_noisy_byzantine.py`.
- Scaffolding to copy: `Phase_CD/Noise_added/eval_noise_robust.py`.
- Reference: `Phase_CD/PAPER_MASTER_PLAN.md` (§5.7/5.8/5.10, §6, §7, §8, §10).

---
*Created 2026-06-19. Anchor for the temporal-trust experiment that follows Option C (§5.10).*
