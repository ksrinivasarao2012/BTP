# INTERNAL VALIDITY AUDIT — every claim verified against code (2026-07-10)

Reviewer-grade audit of the evaluation pipeline. Every answer cites the exact file and line
inspected on the audit date; nothing is answered from memory. Re-verify line numbers after any
refactor. Verdict key: ✅ verified · ⚠️ verified with required disclosure · 🟡 partial (open item).

---

## PART A — Map generation & protocol fairness

### A1. Are the same maps used across all comparison arms (base / attack / robust / temporal / no-harm)?
**✅ VERIFIED.** The episode seed depends ONLY on the map index, never on the condition:
`Phase_CD/Noise_added/eval_temporal.py:127`
```python
seed = 800_000_000 + int(0.20 * 100) * 10_000 + map_idx + attempts * 5_000
```
All arms replay the identical 500-map suite, making recovery and no-harm paired comparisons.
`eval_comm_loss.py` and `eval_density_sweep.py` import and reuse this same `_run`, so R3/R7
inherit the guarantee. (Cosmetic note: `int(0.20*100)*10_000` is a legacy constant from the
density-0.20 era — a fixed offset, harmless.)

### A2. Is every evaluated map solvable?
**✅ VERIFIED.** `eval_temporal.py:129` — after reset, `env._is_map_solvable(start_pos=...)` must
pass **from every drone's spawn position**; otherwise the map is regenerated with a bumped seed
(`attempts * 5_000`) until all pass. No episode is ever scored on an impossible map.

### A3. Do phantoms ever enter the real (physical) map?
**✅ VERIFIED — broadcast-only.** Phantoms are stored in `self._phantoms` and injected only into
traitors' broadcasts: `env_noisy_byzantine.py:217-220`. The generator reads `self.obstacles`
only to *place* camouflage (`env_byzantine_adaptive.py:46`), never writes it. The design is
stated in `env_byzantine_trust.py:10`: *"fabricated; NOT in self.obstacles, so the map stays
truly solvable."* The attack poisons beliefs, not physics.

### A4. Is the (randomized) attack identical across arms for the same map?
**✅ VERIFIED.** `env_byzantine_trust.py:64-68` — per-map phantom count is drawn AFTER the seeded
reset (comment: *"reproducible for a given episode seed"*), with `np.random.randint(lo, hi+1)`
— inclusive, so n_phantom ~ U{3,...,6} exactly as the paper claims. Radii come from the measured
real-obstacle mixture (`_radii_for`, line 87-89), independently confirmed by
`Noise_added/verify_randomized_attack.py`. Traitors are deterministic (`eval_temporal.py:99`:
`traitor_indices=list(range(k))`) — identical across arms; unbiased because spawns are
re-seeded per map.

### A5. Were thresholds/hyperparameters fixed before testing (not tuned on the test set)?
**✅ with one transparent nuance.** Workflow: probe (`probe_temporal_offset.py`, offset-signal
viability) → `selftest_temporal.py` → DEV selection (150 maps, density 0.25, stage-1 model,
FIXED attack) → **frozen** → camera-ready testing on a configuration differing on five axes
(500 fresh maps, density 0.27, stage-2 model, RANDOMIZED attack, f∈{1,2,3}). One single
parameter set (eps0=0.6, k_sigma=4, alpha=0.25, tau=0.4, eta=0.6, min_k=20 — constants at the
top of `eval_temporal.py`) is used in EVERY cell: both attacks, all sigma, all f, comm-loss,
densities. Nuance: the eps 0.6-vs-0.7 operating-point trade-off is reported using camera-ready
numbers and the Discussion says so openly ("we adopt the operating point that maximizes
recovered success"); the frozen point then generalized unchanged across loss/density/f —
held-out evidence in practice.

---

## PART B — Detector integrity, statistics, reproducibility

### B1. Verify no future-information leakage in the temporal detector.
**✅ VERIFIED.** `env_noisy_byzantine.py:116-147` (`_temporal_update`) reads only: the
neighbour's CURRENT broadcast (`bc_c`), ego's CURRENT noisy sensing (`self._sensed[idx]`,
line 127), and ego's position (line 128). Offsets are ADDED to running sums (line 139:
`b[0]+=d[0]; b[1]+=d[1]; b[2]+=1`) — no structure in the function contains information from
any later step. Per-episode isolation: `reset()` line 84-86 clears the memory
(`self._tbias = {}` — *"temporal memory is per-episode"*), so no cross-episode leakage.

### B2. Verify the detector is strictly causal.
**✅ VERIFIED.** The verdict at step t thresholds `||(sum_x/c, sum_y/c)||` over offsets from
steps <= t only, and fires only after the bucket holds >= `temporal_min_k = 20` PAST samples
(`env_noisy_byzantine.py:141-146`). `_sample_sensing` (line 150-154) guards one noise draw per
step (`if self._sense_step == self.steps: return`) shared across observers — no re-rolls, no
lookahead.

### B3. Verify no hidden simulator state / ground truth is available (defender & attacker).
**✅ defender · ⚠️ attacker (deliberate strong-adversary; disclose in threat model).**
- Defender verifies against its OWN NOISY view only: `_ego_judgement` line 179
  (`ego_seen = self._sensed[idx][self._in_range[idx]]`) and `_temporal_update` line 127.
  Ground-truth traitor labels are used ONLY for metric counting (`eval_temporal.py:156-161`),
  never for behaviour.
- Attacker reads the TRUE map to place camouflage (`env_byzantine_adaptive.py:46`) and
  broadcasts phantom centres EXACTLY (noise-free lie, `env_noisy_byzantine.py:109` — noise on
  the lie only via the explicit jitter knob). Strictly stronger than physically realizable →
  biases results AGAINST the defense (conservative). **Action: one disclosure sentence in
  Methods threat model.**
- Mild defender idealization: ego's own tracks are index-identified (perfect self-tracking of
  STATIC obstacles, line 134); broadcast-to-track association is realistic nearest-neighbour
  (line 133). The probe quantifies the realism cost: AUC 0.99 (oracle assoc) vs 0.85-0.90
  (realistic assoc). **Action: half-sentence disclosure.**

### B4. Verify all evaluation metrics are computed correctly.
**✅ VERIFIED.** `eval_temporal.py:133-154`: honest-drone success = `h_reached / h_total` with
traitors EXCLUDED from the denominator (lines 146-148) and success requiring
`infos[a]["cause"] == "success"` (line 149). Recovery = defended − undefended and
no-harm = defenseON-noattack − base are per-map differences of these rates (paired by A1).
Detection P/R: TP/FP/FN counted per (observer, accused) LINK vs the true traitor set
(lines 156-161), pooled over maps. Note: no separate "collision" metric is reported or
claimed — collisions are one failure cause inside (1 − success).

### B5. Verify confidence intervals are computed correctly.
**✅ VERIFIED.** `Noise_added/boot_ci.py`: percentile bootstrap, `_N_BOOT = 2000` resamples,
percentiles (2.5, 97.5) → proper 95% CI. Resampling is over MAP indices — the independent
unit — which respects within-map correlation of the 10 drones. Fixed `_SEED = 12345` →
reproducible intervals.

### B6. Verify the paired bootstrap is implemented correctly.
**✅ VERIFIED.** `boot_ci.py:32-41` (`diff_ci`): ONE index matrix `idx = rng.integers(0,n,...)`
is applied to BOTH arrays — `(a[idx].mean(axis=1) - b[idx].mean(axis=1))` — i.e., the same maps
enter both arms in every resample: the definition of paired. Used for recovery and no-harm.
`pr_ci` (line 44-60) bootstraps per-map TP/FP/FN sums with the same paired indices.

### B7. Verify all random number generators are seeded (Python, NumPy, PyTorch, CUDA).
**✅ for everything that matters — stated precisely.**
- NumPy: `swarm_env_step_B10_8_0m.py:225-227` — `reset(seed=...)` calls `np.random.seed(seed)`.
  ALL stochastic elements (map gen, spawns, dropout bursts, sensor noise, phantom
  randomization, comm-loss drops, jitter/duty) draw from `np.random` → all flow from the
  per-map seed.
- PyTorch/CUDA: NOT APPLICABLE at evaluation — policy runs `model.predict(...,
  deterministic=True)` (`eval_temporal.py:140`) on CPU (`_init`: `PPO.load(..., device="cpu")`,
  line ~86). No torch sampling occurs, so torch/CUDA seeds cannot influence results.
- Python `random` module: unused in the eval path. Bootstrap RNG: seeded 12345 (B5).

### B8. Verify results are reproducible across runs with the same seed.
**✅ EMPIRICALLY PROVEN (2026-07-10).** The full env (sigma=0.6, ~33% dropout, camouflage,
randomize_attack=True, comm_loss=0.2, robust+temporal ON) was run twice with seed 800_200_123
and fixed actions; SHA-256 over 40 steps of complete state (obstacles, phantoms, positions,
noisy sensing, trust matrices):
```
run1: 9d6310823b865dd075345ad029a2d7eb...
run2: 9d6310823b865dd075345ad029a2d7eb...   -> IDENTICAL
```
With a deterministic CPU policy, a single (env, seed) episode is bit-reproducible.
**⚠ AMENDED 2026-07-11 (full-pipeline evidence):** an unplanned re-run of the k=2 comm-loss +
density pipeline (`*_k2_run2.txt`) shows RECOVERY and its CIs reproduce EXACTLY in every cell
(+12.3/+12.7/+11.2/+9.5; +12.3/+12.1/+12.3/+8.8), detection precision identical, recall to
+-0.01 — but the two ATTACK-FREE arms (base, temp.nh) vary by <=0.2 pp between runs, so no-harm
shifts slightly (e.g. -0.2 vs -0.4). Every ATTACKED arm is deterministic. All no-harm CIs still
span zero, so no conclusion changes. Source of the clean-arm variation NOT yet identified ->
OPEN ITEM (investigate before the release repo; likely an RNG-consumption path that differs when
n_traitors=0). The honest claim is: 'headline results reproduce exactly; clean-arm cells carry
<=0.2 pp run-to-run variation', NOT 'the whole pipeline is bit-reproducible'.
Multiprocessing changes only task ORDER; each task is an independent (env, seed) pair.

### B9. Verify the Temporal method differs from Robust by only the intended component (clean ablation).
**✅ VERIFIED — textbook-clean.** `env_noisy_byzantine.py:225-237`: the temporal arm executes
the IDENTICAL robust check (lines 227-229, same eps0 + 4*sigma, same code object) plus exactly
ONE OR'd additional judgement (lines 230-232, `_temporal_update`). Both arms then share the
SAME EWMA (line 233-235, same alpha=0.25) and the SAME exclusion threshold (line 236,
tau=0.4). The eval configs differ in a single boolean (`temporal=True`,
`eval_temporal.py:206`). Every measured difference between arms is attributable to the
temporal test alone.

### B10. Verify hyperparameter sensitivity (window size, thresholds, ...).
**🟡 PARTIAL — the one genuine open item.**
- Exists: `k_sigma=4` derived from the sqrt(2)*sigma honest-disagreement bound
  (`PARAMETER_JUSTIFICATION_PHASE_CD.md:103`); eps 0.6-vs-0.7 trade-off reported in the
  Discussion; eps/min_k selected via dev-time sweeps (`selftest_temporal.py:48-49` exposes both
  as CLI args) on a DIFFERENT configuration than the test bed, then frozen for every
  camera-ready cell; the frozen point generalized unchanged across noise, traitor counts,
  packet loss, and densities.
- Missing: a systematic published sensitivity table (e.g., eta in {0.5,0.6,0.7} x min_k in
  {10,20,30} at the headline cell sigma=0.6/camouflage/f=2).
- **Option:** ~half-day run with the existing harness closes it pre-emptively; otherwise it is
  a standard, answerable revision request.

---

## Outstanding actions from this audit
1. [ ] Methods threat model: one sentence disclosing the strong-attacker grant (true map
   knowledge + noise-free fabrication) — biases against the defense, i.e., conservative. (B3)
2. [ ] Methods 3.6: half-sentence disclosing idealized ego self-tracking of static obstacles,
   citing the probe's realistic-association AUC 0.85-0.90 as the measured cost. (B3)
3. [ ] OPTIONAL: eta x min_k sensitivity sweep at the headline cell (~half day). (B10)

---

## PART C — Overhead, scaling, coverage, attacker capability (audited 2026-07-10)

### C1. Verify runtime overhead (latency per step).
**✅ MEASURED 2026-07-10** (10 drones, sigma=0.6, camouflage f=2, randomized attack, laptop CPU,
un-optimized Python; 150 steps after warmup):
```
no defense : 3.04 ms/env-step
robust     : 4.86 ms/env-step   (+1.82 ms)
temporal   : 6.30 ms/env-step   (+1.44 ms over robust  ->  ~144 us per drone per step)
```
The temporal filter's own cost is a nearest-neighbour association + a dict update per broadcast:
O(#claims x #own-tracks) per pair. Negligible against any real perception stack.
(Numbers are NOT yet in the paper — optional one-liner for Methods/Discussion.)

### C2. Verify memory overhead.
**✅ MEASURED.** After ~160 steps: 81 (ego,neighbour) pairs, 1512 buckets; each bucket = 2 float
sums + count -> ~47 KB for the WHOLE swarm episode. Upper bound n*(n-1)*M = 10*9*~30 = 2700
buckets ~ 86 KB. Cleared each episode (`reset`, `_tbias = {}`). Trivial.

### C3. Verify scalability with different swarm sizes.
**❌ NOT VERIFIED — deliberate, documented deferral.** All experiments use n=10 drones; other
swarm sizes require retraining the navigator (weeks) and were explicitly deferred
(`REJECTION_RISKS.md` R7 decision 2026-07-08; disclosed in Discussion assumption (v)).
What CAN be said: the defense itself is per-pair and local — compute grows O(neighbours x
claims) per drone, memory O(n^2 * M) worst case (C2) — and AerialTrust independently reports
trust estimation IMPROVING with agent density; but our behavioural claims are for n=10 only.

### C4. Verify performance across different map densities.
**✅ VERIFIED — R7 sweep, 500 maps/cell, densities {0.20, 0.24, 0.27, 0.30}, sigma=0.6 camo.**
Recovery k=2: +12.3 / +12.1 / +12.3 / +8.8 pp (all CIs > 0); k=1: +6.8 / +6.4 / +7.1 / +6.3.
No-harm ~0 at every density. Recall falls with clutter (0.78 -> 0.61) while precision rises
(0.81 -> 0.85). Raw: `results_027/density_sweep_camouflage_500{,_k1,_k3}.txt`. k=3: +15.9/+10.5/+13.5/+10.9 — done.

### C5. Verify performance across different numbers of obstacles.
**✅ VERIFIED via C4 — density IS the obstacle-count control.** `target_density` sets total
obstacle area; at 0.27 the measured mean is ~29.7 obstacles/map (`measure_env_stats.py`), and
the 0.20->0.30 sweep spans correspondingly fewer/more obstacles, with per-map count varying
naturally around the target. Phantom count additionally randomized U{3..6} per map (A4).

### C6. Verify performance across different numbers of traitors.
**✅ VERIFIED.** Camera-ready f in {1,2,3} full tables (temporal recovery +7.1 / +12.2 / +13.6 pp
at sigma=0.6 camo; precision RISES with f: 0.68 -> 0.82 -> 0.89). R3 comm-loss + R7 density
re-verified at k=1 and k=2 (`*_k1.txt`); k=3 pipeline built and queued
(`run_r3_r7_pipeline_k3.bat`). **UPDATE 2026-07-10: k=3 COMPLETE** — comm-loss recovery
+13.6/+14.1/+12.1/+13.2 across p∈{0,.1,.2,.3}; density +15.9/+10.5/+13.5/+10.9; all CIs>0,
no-harm ~0. The k∈{1,2,3} matrix is closed.

### C7. Verify the no-attacker (all honest) scenario.
**✅ VERIFIED — it is a first-class arm ("no-harm") in EVERY table.** Defense ON with k=0
traitors vs base: temporal no-harm -0.4 / -0.4 / -0.3 pp (f=1/2/3), CI spans zero; flat across
all noise levels, all packet-loss rates, and all densities. Contrast: the naive filter fails
exactly this test (-27.5 pp at sigma=0.4) — which is finding (iii) of the paper.

### C8. Verify failure cases are documented.
**✅ mostly documented, ONE gap found by this audit:**
Documented (Results/Discussion): (a) 31% of camouflage lies escape at sigma=0.6 (recall 0.69,
never claimed otherwise); (b) residual false flags at precision 0.80-0.82 — shown to be
ultra-stealthy, near-harmless buckets; (c) the navigation noise ceiling (53.4%) is NOT
recoverable by any defense (Section res-limit); (d) recovery shrinks at density 0.30
(+12.3 -> +8.8); (e) intermittent (duty) attacker halves recall to 0.41 — but its harm falls
faster (+5.0 pp); (f) neighbour-level exclusion discards the excluded drone's honest data
(assumption iii).
**GAP (new action item): the min_k warm-up window.** No verdict is possible before 20 samples
accumulate in a bucket — the swarm is protected only by the robust path during roughly the
first ~20 sightings of each (neighbour, track) pair, and a short-episode or late-joining
attacker would face only single-frame defenses. True by construction (B2), not currently
stated in the paper. -> add one sentence to Discussion.

### C9. Verify the attacker cannot access future observations.
**✅ VERIFIED.** Phantoms are generated ONCE at reset from reset-time state only
(`env_byzantine_adaptive.py:38-43` — obstacles, swarm centroid, goal); the per-step broadcast
(`env_noisy_byzantine.py:93-113`) re-emits those same phantoms with only a CURRENT-step
jitter/duty draw. Nothing downstream of the current step exists when either function runs.

### C10. Verify the attacker cannot access unavailable internal simulator variables.
**✅ VERIFIED by grep — the attack code never reads `self.trust`, `self._tbias`, or other
drones' `_sensed`.** Its complete read set: the true obstacle map (the DISCLOSED strong-attacker
grant, B3), the swarm centroid and goal (mission geometry an insider legitimately knows), and
its own attack knobs. Consequence worth one clarifying sentence: the attacker knows the defense
DESIGN (and the adaptive sweeps optimize its geometry against it offline), but it cannot
observe its own runtime trust score or adapt online within an episode.

---

## Outstanding actions (updated 2026-07-10, second pass)
1. [x] DONE — Methods threat model now discloses the strong-attacker grant AND design-aware-but-
   not-state-aware (methods.tex, end of sec 3.4). (B3, C10)
2. [x] DONE — Methods 3.6(c) now discloses idealized ego self-tracking with the probe AUC
   0.99-oracle vs 0.85-0.90-realistic as the measured cost. (B3)
3. [x] DONE — Discussion has a new 'The warm-up window' subsection (K_min=20 blind period,
   negligible at 1200 steps, matters for short encounters/late joiners). (C8)
4. [ ] OPTIONAL: eta x min_k sensitivity sweep at the headline cell (~half day). (B10)
5. [x] DONE — runtime/memory line added to Methods 3.6(c) (~0.15 ms/drone/step, <100 KB). (C1-C2)

---

## PART D — Data integrity: tables, figures, leakage, generators (audited 2026-07-10)

### D1. Verify all reported table values exactly match the raw results.
**✅ VERIFIED — every manuscript table traced to its raw file, cell by cell.**
- Anchor (89.34/45.86 drone; 67.80/10.40 map; +57.40 [52.80,61.80]) = `anchor_OFF_500.txt` EXACTLY.
  ⚠️⚠️ **AMENDED 2026-07-10 (Srinivasa's follow-up question exposed a misdescription):**
  `eval_slot_fusion_zero_shot.py` loads ONE model and toggles `use_shared_map` — so 89.34 AND 45.86 are
  both the **OFF-trained** policy (± shared data at test): an INFORMATION ABLATION, not a two-model
  comparison. The manuscript had described 89.3 as 'the trained sharing model' — WRONG; results.tex
  rewritten (single-policy ablation framing + the ON-trained model's native 87.7 as confirmation), ledger
  attribution corrected. The true two-model comparison is the dropout sweep (`eval_dropout_sweep.py`
  docstring: 'ON-trained vs OFF-trained models'), whose table text was already correct. Numbers unchanged
  everywhere; only descriptions fixed.
- Dropout table (-1.3 [-2.3,-0.4] / +41.4 [38.9,43.8] / +50.8 [48.3,53.3]) = `dropout_sweep_500.txt` exactly.
- Naive table = `naive_sweep_500.txt` exactly (incl. -27.5 at sigma=0.4 = 65.58-38.10).
- Temporal f=2 table = `eval_f2_{wall,camouflage}_500.txt` CI blocks exactly, incl. +12.2 [9.8,14.9].
  NOTE: raw quick-table row shows wall sigma=0.4 tmp.rec "+9.1" while the CI block says +9.2
  [6.7,11.6] — the quick row subtracts two already-rounded cells; the CI block is authoritative
  and matches the manuscript.
- Headline f in {1,2,3} = `eval_f{1,3}_camouflage_500.txt` rows exactly (44.4/+1.9/+7.1;
  35.3/+5.3/+13.6; precisions 0.68/0.82/0.89; no-harm -0.4/-0.4/-0.3).
- Bind table = `adaptive_offset_f2_500.txt` exactly (six rows verified earlier).

### D2. Verify all plotted figures are generated from the reported data.
**N/A — NO FIGURES EXIST YET.** Honest status: the 6-8 planned figures (FIGURES_PLAN.md) are not
generated. The plan already mandates one matplotlib script per figure reading from the ledger
numbers; when built, each script's input file must be one of the raw `results_027/*.txt` (not
hand-typed values). Re-run this check after figure generation.

### D3. Verify paper text matches tables and figures exactly.
**✅ VERIFIED for all quantitative prose.** Cross-checked: intro 89.3/45.9 and "more than 43 pp"
(43.48) ✓; "up to 22.5 pp" = 86.0-63.5 ✓; precision "1.00 -> 0.23" ✓; "destroying up to 27 pp"
= 27.5 at sigma=0.4 ✓; "0.13 -> 0.69" ✓; "+12.2 [9.8,14.9]" ✓; "37.6 -> 49.8 vs base 53.4" ✓;
no-harm "-0.4, CI spans zero" ✓; abstract numbers ✓. Figures: N/A (D2).

### D4. Verify no data leakage between training and evaluation.
**✅ VERIFIED.** `train_noise_robust.py:104` calls `env.reset(options=...)` with NO seed →
`swarm_env_step_B10_8_0m.py:226-227` (`if seed is not None`) never seeds NumPy during training →
training maps come from the unseeded global stream. Evaluation maps live in the dedicated
`800_000_000+` seed space used ONLY by eval scripts. Training cannot have seen the eval suite
(same generator DISTRIBUTION, disjoint realizations — the standard i.i.d. setup).

### D5. Verify train/test seeds or maps are independent.
**✅ VERIFIED — same evidence as D4:** training = unseeded stream; testing = explicit
`800M + 200_000 + map_idx (+5000*attempts)` per map. No overlap by construction.

### D6. Verify evaluation maps are never reused during parameter tuning.
**✅ with an honest nuance.** Tuning happened on the DEV configuration: 150 maps at density 0.25
(stage-1 model, fixed attack). The dev seed FORMULA is the same, so seed INDICES 0-149 overlap —
but with `target_density=0.25` the generator produces DIFFERENT worlds from the same seed, so the
0.27 test maps themselves were never evaluated during tuning. Additionally the camera-ready suite
is 500 maps (350 of which have indices never touched in dev), and the frozen parameters then
generalized unchanged across loss/density/f. Residual overlap is at the level of RNG indices,
not maps.

### D7. Verify communication-loss experiments use the intended communication model.
**✅ VERIFIED.** `env_noisy_byzantine.py:210-211`: inside the per-(receiver, sender) loop, per
step: `if self.comm_loss > 0 and np.random.random() < self.comm_loss: continue` — an independent
Bernoulli drop per (receiver, sender, step), where a dropped packet contributes NEITHER fusion
NOR verification evidence that frame. Exactly the model claimed in the paper and the ledger.
Range: `communication_range=10.0` in `_build_env` — matches the "10 m" in Methods.

### D8. Verify sensor-noise experiments use the claimed noise distribution.
**✅ VERIFIED.** `env_noisy_byzantine.py:163-167`: `np.random.normal(0, sigma, (n_drones, M, 2))`
— i.i.d. zero-mean isotropic Gaussian, independent across drones, obstacles, and steps, resampled
each step (guarded by `_sense_step`, one draw per step shared by all functions within the step).
Matches Methods eq. exactly (N(0, sigma^2 I_2), independent across j, m, t).

### D9. Verify obstacle generation matches the paper description.
**✅ VERIFIED.** Circular obstacles ✓; `target_density` fill ✓ (`swarm_env_step_B10_8_0m.py:18,21`);
solvability via gridded BFS with drone clearance ✓ (`_is_map_solvable`, line 187-192, clearance =
drone_radius + 0.05); plus the eval-side per-spawn re-check (A2). Empirical stats at 0.27 (~29.7
obstacles, 42/40/18 size mixture) measured by `measure_env_stats.py`.

### D10. Verify phantom generation matches the claimed distribution.
**✅ AFTER A MANUSCRIPT FIX made by this audit.** Count: n ~ U{3..6} inclusive ✓ (A4). Radii:
`_sample_radius` (`env_byzantine_trust.py`) draws classes at **40/40/20%** (small 0.2-0.5 /
medium 0.6-1.4 / large 1.5-2.5) — the paper previously said radii are drawn from "a 42/40/18%
mixture", which is the MEASURED real-obstacle mixture, not the sampler's probabilities.
**methods.tex corrected 2026-07-10**: now states the sampler is 40/40/20 over the generator's
radius ranges, *matched to* the measured 42/40/18 empirical distribution
(`verify_randomized_attack.py` confirms the resulting match). Wording is now exactly true.

## Part D actions
1. [x] DONE — methods.tex phantom-radius sentence corrected (40/40/20 sampler vs 42/40/18 empirical). (D10)
2. [ ] Release-repo README: document the anchor filename trap (paper anchor = `anchor_OFF_500.txt`). (D1)
3. [ ] After figures are generated: re-run D2 (each figure script must read raw `results_027/*.txt`). (D2)

---

## PART E — Distribution proofs, isolation, claim coverage (audited 2026-07-10)

### E1. Verify phantom generation matches the claimed distribution.
**✅ EMPIRICALLY RE-PROVEN** (beyond D10's code check): ran `verify_randomized_attack.py 60 camouflage`:
n_phantom counts {3:18, 4:14, 5:12, 6:16}, mean 4.43 (expect 4.5 for U{3..6}); radius bands
39/40/21% vs the sampler's 40/40/20% (matched to the real 42/40/18% mixture — manuscript wording
already corrected, D10). Fixed-radius mode (bind sweep) verified: n=4 only, radius {1.0} only —
the swept axis is unconfounded.

### E2. Verify attack randomization matches the paper specification.
**✅ — same evidence as A4 + E1.** Code: `randint(lo, hi+1)` inclusive, drawn after the seeded
reset (reproducible per map); paper says n~U{3,...,6}: exact match. Randomization ON for all
headline/f-sweep/comm-loss/density runs; OFF for the adaptive sweeps (by design, stated in both
paper and ledger).

### E3. Verify CIs and averages are computed over the correct number of maps.
**✅ VERIFIED.** `eval_temporal.py:210` builds exactly one task per (condition, map):
`[(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]`; line 229 fills `rates[ci][mi]`
exactly once per task (imap returns each task once); arrays are preallocated `zeros(n_maps)`.
`boot_ci` resamples `n = len(x)` = 500 indices per replicate (lines 22-27). Detection P/R pools
TP/FP/FN over the same 500 maps. No condition is averaged over a different n.

### E4. Verify no evaluation code accidentally modifies the environment state.
**✅ VERIFIED.** The eval loop calls only `env.reset(seed)`, `env.step(action)`,
`env._is_map_solvable()` (pure BFS on a temp grid), and `env.predicted_traitors()` —
inspected (`env_byzantine_trust.py:183-187`): a pure dict comprehension over `self.trust`,
no writes. Envs are cached per condition (`_G["env_key"]` check) and fully re-seeded/reset per
map; `reset()` clears trust, phantoms, temporal buckets (B1). No eval-side attribute writes.

### E5. Verify every experiment varies ONLY the studied variable.
**✅ VERIFIED.** All conditions are built by one constructor (`_cfg`) over a fixed base
(density 0.27 default, dropout 0.10/5, comm range 10 m, same model, same seeds/maps by A1);
arms differ only in {n_traitors, defense, temporal}; sweeps vary only their axis (noise; comm_loss;
density; offset/gap/jitter/duty with randomize_attack=False so radius/count stay fixed, E1).
Cross-file spot-check: base/no-harm cells reproduce across independent runs (+12.2 vs +12.3;
+13.6 vs +13.6; 53.4 vs 53.5) — consistent with only-the-variable changing.

### E6. Verify all claims about PRBI are supported by the PRBI paper incl. supplementary.
**✅ — the full-text audit COVERED the supplementary** (their appendix §11.3 intermittent-attack
experiment is IN our claims: "while it evaluates intermittent injection schedules..."). Every
PRBI sentence in the manuscript is quoted mechanism, 0-hit verified absence, explicitly
disclaimed inference, or about our own method; claim-by-claim verified by Srinivasa 2026-07-10.
(See the PRBI section of related.tex and the audit trail in PAPER_TODO.md.)

### E7. Verify every claim about our method is supported by experiments/analysis.
**✅ after this audit's fixes.** Spot-verified the strong claims: "never regresses on wall"
(temporal >= robust at every sigma: 13.9/14.1/9.2/9.7 vs 13.9/13.1/7.8/3.7 ✓, camo likewise ✓);
"no measured cost" (no-harm CIs span 0 in every table ✓); mechanism claim (zero-mean vs
persistent bias: derivation in Methods + probe AUC 0.99/0.85-0.90 ✓); bind claims (offset table +
9 sigma-x-f configs + jitter/duty/gap ✓); comm-loss/density claims (k in {1,2,3} ledger ✓).
Overclaims found & fixed during audits: "statistically comparable" (no test run — removed),
anchor description (information ablation, not two models — rewritten), "cannot escape" (recall
is 0.69 — softened), phantom-mixture wording (D10).

### E8. Verify every claim in the manuscript is supported by code, experiments, or citations.
**🟡 SUBSTANTIALLY — with a named remaining list.** Fixed this round: (a) intro "as is common"
(uncited commonality claim about MIN-fusion) -> now "implemented here by..., the choice that
respects any teammate's evidence"; (b) related.tex "work on learned inter-agent messages
typically perturbs latent vectors" (uncited literature generalization) -> deleted; the contrast
now describes only OUR attack surface.
**Still open (the complete known list):**
1. CAD (2 passages) — full text UNVERIFIED; "occupancy agreement"/"benign observer"/"feature
   maps" grouping are abstract-level inferences. [waiting on CAD.pdf]
2. TruPercept intro sentence ("at all", "because") — fix drafted, awaiting go.
3. Abstract-only citations: TrustFlip, 3D-TC2, ADoPT, SwarmRaft, CoDynTrust, Conformity —
   claims match abstracts; full-text checks pending (guide items).
4. "to our knowledge no prior work..." — inherently unfalsifiable, correctly hedged.

## Part E actions
1. [x] DONE — "as is common" removed (intro). (E8)
2. [x] DONE — uncited latent-message generalization deleted (related). (E8)
3. [ ] CAD full-text audit — blocked on CAD.pdf download. (E8)
4. [x] DONE 2026-07-10 — TruPercept intro corrected ('did not meaningfully improve', causes hedged
   as 'suspected'). Full TruPercept re-audit same day: all claims verbatim-verified against the PDF
   text (ligature-aware grep); one NEW error found & fixed — the baseline paragraph had placed
   TruPercept 'in surveillance settings' (it is autonomous driving; 'surveillance' = 0 hits in its
   text) — qualifier removed from related.tex.
