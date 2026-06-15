# Combined Adversarial Phase (C+D) — Confirmed Direction + Step-by-Step Action Plan

**Date:** 2026-06-15
**Scope note:** the original split (C = deceptive traitors, D = aggressive/physical traitors) is now
**merged into one Combined Adversarial Phase (C+D)**: deception (C) proved inert, physical aggression (D)
is the real threat, so the trust/defense idea (C) is applied to the physical threat (D) as a single phase.
**This supersedes the deception-centric plan.** Probes decided the direction with data.

## Staged adversary schedule (do in this order)
1. **NOW — ramming with TRUE broadcasts** (`deception_mode="none"`): isolate the physical threat and the
   behavioral (LiDAR-based) defense. This is the whole STEP-1→3 plan below.
2. **LATER — ramming + FALSE signals (ram+lie, D-T5c):** only after step 1 is complete, add deception on
   top of ramming (`deception_mode="false_velocity"` + `traitor_behavior="ram"`).
   - Honest expectation: ram+lie ≈ ram at normal sensing (LiDAR overrides lies — proven by the deception
     probe). It only bites meaningfully under **occlusion / degraded LiDAR** (when a lie about an unseen
     neighbor can't be cross-checked). So pair the false-signal step with an occlusion/NLOS stress regime
     to make it matter; otherwise it is a completeness check (defense robust to the combined attack).

---

## 1. Probe results (the decision)

| Attack | f | density 0.20 | density 0.30 | honest_success drop |
|--------|---|--------------|--------------|---------------------|
| **Deception** (false vel/pos) | 2–3 | ~95% | ~91% | **~0 pp (inert)** |
| **Ramming** (physical) | 2 | **77.38%** | **73.50%** | **~18 pp** |

- Baseline (no traitors): 95.55% / 91.10%. Files: `results/phase_c_probe/`.
- Ramming drove drone-collisions from ~0.4% to **~19%** → rammers land hits; honest drones can't fully dodge.

**VERDICT:** the swarm is **robust to communication attacks** (deception/jamming) because it is
LiDAR-grounded, but **vulnerable to physical adversaries** (ramming). The contribution becomes a
**behavioral defense against hostile movers**, not a comm-deception trust mechanism.

---

## 2. The new defense design (behavioral, LiDAR-based)

Rammers don't lie — so the detection signal is **motion**, not communication:
- A hostile drone moves **on an intercept course** toward an honest drone (closing fast, heading at it),
  instead of toward the goal. This is observable from **LiDAR** (relative position + inferred velocity) —
  **no communication needed.**
- Per-neighbor **threat score** = function of closing speed / time-to-collision / bearing alignment
  (the env already computes these "danger signals" for rewards). Feed it into the **reserved trust slot**
  and let the policy learn to **evade high-threat neighbors**.

**Models (headline = M1 vs M2):**
| Model | Trained vs rammers? | Explicit threat signal? | Role |
|-------|:---:|:---:|------|
| **M0** = `comm8_lidar` | No | No | vulnerability reference (the 18pp drop just measured) |
| **M1** | **Yes** | No | does *retraining alone* teach evasion? (baseline) |
| **M2** | **Yes** | **Yes** (behavioral threat score) | proposed defense |

Both M1/M2 transfer from `comm8_lidar`. Metric: `honest_success = reached / (n − f)`.

---

## 3. STEP-BY-STEP ACTION PLAN (with result boxes)

### STEP 1 — Scale the threat (cheap, eval-only, ~1 hr) → bring to Claude
Confirm how the drop scales with the number of rammers.
```powershell
python probe_ram.py 1
python probe_ram.py 3
```
**RESULTS (fill in):**
```
ram f=1: 0.20  honest_success 85.78%  (baseline 95.55%, drop +9.77pp)   timeout 2.17%   coll 12.06% (drone 10.11%)  |  honest_success 82.39%  (baseline 91.10%, drop +8.71pp)  timeout 5.00%  coll 12.61% (drone 10.17%)

ram f=2: 0.20  honest_success 77.38%  (baseline 95.55%, drop +18.17pp)  timeout 2.19%   coll 20.44% (drone 18.81%)  |  honest_success 73.50%  (baseline 91.10%, drop +17.60pp) timeout 4.38%  coll 22.12% (drone 19.44%)

ram f=3: 0.20  honest_success 70.00%  (baseline 95.55%, drop +25.55pp)  timeout 2.43%   coll 27.57% (drone 26.29%)  |  honest_success 67.50%  (baseline 91.10%, drop +23.60pp) timeout 4.93%  coll 27.57% (drone 25.57%)
(already have f=2: 0.20=77.38% / 0.30=73.50%)
```
**→ STEP 1 VERDICT (done):** ramming scales ~LINEARLY — **~8–9pp drop and ~10% drone-collisions per
rammer** (f=1→~9pp, f=2→~18pp, f=3→~25pp). Each rammer reliably kills ~0.8–1 honest drone (near the
1-kill ceiling). Strong, clean threat → proceed to build the defense (STEP 2).

### STEP 2 — Train M1 (retrain vs rammers, NO explicit signal) → bring to Claude
Decision test: does the swarm learn to evade rammers just from retraining?
- Build a training variant where some drones are set to `traitor_behavior="ram"` each episode
  (curriculum: 0 → 1 → 2 rammers). Transfer from `comm8_lidar`. Honest drones learn evasion via the
  existing collision penalty.
- Eval M1 vs f=2 rammers.

> ⚠️ **CRITICAL implementation point (easy to get wrong):** rammers are **scripted environment hazards,
> not learning agents.** Their actions are overridden by `_ram_action`, and they receive the −500
> collision penalty when they ram. If their transitions are fed to the shared PPO policy, learning is
> **corrupted** two ways: (1) the *stored* action (policy output) ≠ the *executed* action (ram override),
> breaking the on-policy assumption; (2) the rammers' −500 rewards would teach the honest policy the wrong
> lesson. **Fix:** treat rammers as part of the ENV — the VecEnv must expose only the **honest** drones as
> RL agents (num_envs = n_workers × num_honest), stepping the f rammers internally via `_ram_action` and
> **excluding their transitions from the PPO update.** This is the first real coding task of STEP 2.

**RESULTS (fill in):**
```
M1 (retrained vs rammers, no signal): 0.20 honest_success ____%  | 0.30 ____%
vs M0 (18pp drop) and baseline (95.55/91.10)
```
**→ Bring to Claude. DECISION (this is a likely fork — the architecture is strong):**
- **If M1 leaves a big gap** → the explicit threat signal (M2) is needed → STEP 3.
- **If M1 recovers MOST of the 18pp** (M1 ≈ baseline) → matched-condition success no longer separates M1
  from M2. Do NOT force a mechanism the data says is unnecessary. Instead, in priority order:
  1. **Test GENERALIZATION, not matched success.** Train M1/M2 on f=2 rammers, then evaluate on
     **unseen/harder** attacks (f=3–4, faster rammers, blocking, ram+lie, occlusion). An explicit
     threat-detection mechanism (M2) typically generalizes better to attacks it wasn't trained on — even
     if it ties M1 on the trained case. **That generalization gap is the contribution.**
  2. **Escalate difficulty until M1 breaks** (more/faster rammers, occlusion) → find the regime where
     implicit retraining fails but M2 holds.
  3. **If M1 ≈ M2 even at the hardest settings** → be honest: contribution becomes "adversarial-curriculum
     training yields emergent evasion" (real, but mechanism-light); drop the explicit trust mechanism.
  (This mirrors the deception finding: if the LiDAR-grounded policy is already robust, the value of an
   added signal shows up in *generalization/robustness*, not matched-condition success.)

### STEP 3 — Build M2 (retrain + behavioral threat signal) → bring to Claude
Only if STEP 2 leaves a gap worth closing.
- Compute per-neighbor threat score from LiDAR-sensed motion (closing speed / TTC / bearing); feed into
  the reserved sync trust slot; (apply Refinements from `PHASE_C_REFINEMENTS.md`: EMA-smooth the inferred
  velocity, aux-loss to wake the slot, track FPR/TTD/detection-rate).
- Train M2 (transfer from `comm8_lidar` or M1), eval vs f=2 rammers.

**RESULTS (fill in):**
```
M2 (retrained + threat signal): 0.20 honest_success ____%  | 0.30 ____%
M1 vs M2 gap = the defense's contribution
Detection: FPR ____%  TTD ____ steps  detection-rate ____%
```
**→ Bring to Claude for the headline read + paper framing.**

### STEP 4 — Sweep & write up
- f ∈ {1,2,3}, densities {0.20,0.30}, M0 vs M1 vs M2.
- Optional: blocking traitors (`traitor_behavior="block"` — not yet implemented).
- Add ORCA baseline; (venue-dependent) multi-seed.

---

## 4. When to bring results to Claude
- After **STEP 1** (ram scaling) — quick sanity.
- After **STEP 2** (M1) — the key decision (does retraining alone fix it?).
- After **STEP 3** (M2) — the headline (M1 vs M2 + detection metrics).
Paste the filled-in result boxes (or the CSVs in `results/phase_c_probe/` and the new training evals).

---

## 5. Honest caveats
- M1 might already recover most of the 18pp (the architecture is strong) — if so, the explicit signal's
  value is small; report that honestly (it's still a finding).
- Rammers self-destruct on contact (one kill each), so the drop is bounded ~f/(n−f); don't expect
  catastrophic collapse at small f.
- The defense is **sensing-based** (no comm) — consistent with the LiDAR-dominant finding. Frame the comm
  robustness (deception/jamming inert) as a *security property*, and the physical defense as the active
  contribution.
- Keep CTDE clean: threat score from own-LiDAR only; never feed the ground-truth traitor label to the policy.

---

## 6. Result file locations
- Probes: `results/phase_c_probe/` (deception + ram CSVs)
- Phase B reference: `PHASE_B_CONCLUSIONS.md`
- Probe verdict: `PHASE_C_PROBE_RESULT.md`
- Refinements (EMA / aux-loss / detection metrics): `PHASE_C_REFINEMENTS.md`
