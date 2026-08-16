# TA-MAPPO: Trust-Aware Multi-Agent Proximal Policy Optimization

A bio-inspired, trust-aware multi-agent reinforcement learning framework for resilient drone-swarm
navigation. A team of 10 drones learns (via **MAPPO / CTDE**) to reach a shared goal in a continuous
2-D arena using dual sensing (LiDAR + inter-agent communication), while staying resilient to
**Byzantine "traitor" drones** that broadcast fabricated sensor data.

---

## Project overview

The project runs as a curriculum of phases, each building on the previous one's trained model:

| Phase | Question | Status |
|---|---|---|
| **A** | Can 10 drones converge on a shared goal with zero obstacles/traitors? | ✅ Complete — 99.68% success |
| **B** | Can drones navigate around static obstacles using LiDAR? | ✅ Complete — 95.6% (density 0.20) / 91.1% (density 0.30) |
| **Collaborative perception** | Does sharing sensed obstacles between neighbours help under sensor dropout? | ✅ Complete — the anchor result (see below) |
| **Byzantine attack** | What happens when some drones broadcast fabricated ("phantom") obstacles? | ✅ Complete — attack characterised, dropout-independent |
| **Consistency-trust defense** | Can a self/non-self trust filter catch the liars? | ✅ Complete — works under ideal sensing, breaks under sensor noise |
| **Robust + temporal-trust defense** | Can the filter be made noise-aware, and can it catch a phantom hidden inside the noise band? | ✅ Complete — temporal (multi-frame) filter recovers the noise-band blind spot |

Everything from "Collaborative perception" onward is the current, active line of work and lives under
`Phase_CD/`. Phase A and Phase B are earlier, completed stages kept for provenance and reproducibility.

### Core ideas
- **Dual-sensing paradigm**: LiDAR (own sensing, cannot be spoofed by a neighbour) + inter-agent
  communication (broadcast, spoofable by traitors).
- **Collaborative perception (slot-fusion)**: neighbours' sensed obstacles are fused into a drone's own
  48-ray LiDAR channel via a per-direction MIN, so a drone that is temporarily blind (sensor dropout)
  can still navigate off what its neighbours see.
- **Byzantine false-obstacle attack**: traitor drones broadcast a *persistent, fabricated* obstacle (not
  present in the real map, so the map stays solvable). Because fusion is a MIN, one fabricated near
  obstacle can override even a fully-sighted honest drone's own LiDAR.
- **Consistency-trust ("T-cell") defense**: each drone keeps a running trust score per neighbour. If a
  drone is sighted in a spot a neighbour claims has an obstacle, and there is nothing there, that is a
  contradiction — the neighbour's trust drops and it gets excluded from fusion once trust falls below a
  threshold. This reads only what the drone itself physically senses (no privileged ground-truth labels).
- **Robust + temporal trust**: under sensor noise, a fixed-tolerance consistency check starts rejecting
  *honest* neighbours (two honest drones sensing the same obstacle disagree slightly). A noise-aware
  tolerance fixes that. A stealthier "camouflage" attack (phantom hugging a real obstacle) can still hide
  inside that noise band on any single frame — but its offset from what the ego drone itself senses is
  *persistently biased* across frames, while an honest disagreement is zero-mean. Accumulating that
  offset vector over time catches the camouflage liar that single-frame checking misses.
- **CTDE (Centralized Training, Decentralized Execution)**: a centralized critic sees global state during
  training; only the decentralized actor (local observations only) runs at evaluation/deployment.

---

## Repository structure

```text
BTP/
├── Phase A/                        # [COMPLETE] Phase A — basic swarm convergence, 0 obstacles/traitors
│   ├── swarm_env_step_A.py
│   ├── train_step_A.py
│   ├── test_suite_step_A.py        # 1K-episode evaluation suite
│   ├── k_fold_validation.py        # 5-fold statistical cross-validation
│   ├── models/                     # Phase A checkpoints
│   └── Project_Summary_Step_A.md   # full narrative incl. bug-fix history
│
├── Phase B/                        # [COMPLETE] Phase B — static obstacles, 48-ray vectorized LiDAR
│   └── Phase_B5_Synchronization/v10_IEEE_Final/
│
├── PhaseB2/                        # From-scratch MAPPO reimplementation (env, wrapper, networks, training)
│   ├── swarm_env.py, gym_wrapper.py, networks.py, train.py, evaluate.py
│   └── density_sweep_v14_*.py      # obstacle-density / solvability calibration sweeps
│
├── swarm_env_step_B10_8_0m.py      # Phase C/D base env (8 m gated comm, LiDAR congestion, traitor hooks)
├── models/                         # All trained model checkpoints (see "Models" below)
├── results/                        # Raw per-condition evaluation logs (do not hand-edit — regenerate via
│                                    # the eval scripts referenced in Phase_CD/PAPER_MASTER_PLAN.md §5)
│
└── Phase_CD/                       # [ACTIVE] Collaborative perception + Byzantine defense line
    ├── swarm_env_phasecd.py                    # experimental env: dropout hooks, collab-perception oracles
    ├── Collab_Perception/
    │   ├── env_collab_perception.py            # clean collaborative-perception env (slot-fusion)
    │   ├── env_byzantine_trust.py              # + Byzantine attack + consistency-trust defense
    │   ├── env_byzantine_adaptive.py           # + filter-aware adaptive attacker variants
    │   ├── train_raster.py, eval_raster.py, eval_parallel.py, eval_dropout_sweep.py, ...
    │   └── DESIGN_RASTER_TRUST.md, RUNBOOK_RASTER.md   # architecture + how to run
    ├── Noise_added/
    │   ├── env_noisy_byzantine.py              # + per-drone sensing noise + robust/temporal filters
    │   ├── eval_noise_robust.py, eval_temporal.py, eval_adaptive_attack.py
    │   ├── calibrate_density_realenv.py        # env-accurate density/solvability calibration
    │   └── results_027/                        # camera-ready result logs (density 0.27, 500 maps)
    ├── PAPER_MASTER_PLAN.md                    # full results ledger, parameter justifications, limitations
    ├── RESULTS_027_CAMERA_READY.md             # headline results table (see below)
    └── manuscript/                             # LaTeX source (not covered in this README)
```

---

## Getting started

### Prerequisites
- Python 3.10
- Conda (recommended)

### Installation
```bash
git clone <this-repo-url>
cd BTP

conda create -n swarm_rl python=3.10 -y
conda activate swarm_rl
pip install -r "Phase A/requirements.txt"
```
Key dependencies: `stable-baselines3`, `pettingzoo`, `gymnasium`, `torch`, `numpy`, `pygame`, `tensorboard`.

> On Windows, scripts are generally run by the environment's full Python path rather than relying on
> `conda activate` inside a non-interactive shell, e.g.
> `C:\Users\<you>\miniconda3\envs\swarm_rl\python.exe <script.py>`.

### Running Phase A (the completed foundational stage)
```bash
cd "Phase A"
python k_fold_validation.py            # 5-fold statistical validation suite
python test_suite_step_A.py visual     # visual PyGame rendering of test scenarios
```

### Running the current (Phase C/D) collaborative-perception + defense line
See `Phase_CD/Collab_Perception/RUNBOOK_RASTER.md` for the full build/run sequence, and
`Phase_CD/PAPER_MASTER_PLAN.md` §5 for the exact command that reproduces every result table below.
Representative commands (PowerShell, run python by full path):
```powershell
$py = "C:\Users\<you>\miniconda3\envs\swarm_rl\python.exe"

# Collaborative-perception zero-shot eval (comm ON vs OFF, under LiDAR dropout)
& $py Phase_CD\Collab_Perception\eval_dropout_sweep.py models\raster_slot_fusion_ON_stage2_final.zip models\raster_slot_fusion_OFF_stage2_final.zip 500

# Byzantine attack + consistency-trust defense (ideal sensing)
& $py Phase_CD\Collab_Perception\eval_parallel.py models\raster_slot_fusion_ON_stage2_final.zip 500 attackcmp 2 10

# Robust + temporal-trust defense under sensor noise
& $py Phase_CD\Noise_added\eval_temporal.py models\noise_robust_ON_stage2_final.zip 500 2 10 camouflage
```

---

## Key results

This section is organized as: the core navigation baselines, the current collaborative-perception +
Byzantine-defense line (the main line of work), then a set of supporting/validity experiments and one
earlier, shelved exploratory direction — all real results from the codebase, kept separate from the main
line so the narrative stays clear.

### Phase A — swarm convergence (5-fold CV, 50,000 simulated drones)
| Metric | Result |
|---|---|
| Drones | 10 honest, 20×20 continuous arena |
| Random spawns | **99.68%** mean success (±0.19% StdDev) |
| Dense 2×2 clusters | **95.78%** mean success (±0.42% StdDev) |
| Timeout rate | 0.00% |

### Phase B — static-obstacle navigation, no adversary (clean baseline M0)
| Obstacle density | Success |
|---|---|
| 0.20 | 95.6% |
| 0.30 | 91.1% |

### Phase B — what communication actually buys (range sweep + blackout ablation)
Before building the collaborative-perception line, the baseline communication channel itself (drones
share position/velocity within range) was ablated to see what it was for. 200 maps/density, paired seeds
across conditions:

| Condition | Success @ d=0.20 | Success @ d=0.30 | Collision rate @ d=0.30 |
|---|---|---|---|
| Unlimited range | 96.45% | 90.90% | 2.70% |
| 8 m (chosen) | 95.45% | 91.25% | 2.40% |
| 5 m | 95.60% | 90.70% | 3.10% |
| 3 m | 95.20% | 91.40% | 2.90% |
| **8 m → 0 (blackout, zero-shot)** | **90.65%** | **83.40%** | **12.55%** (~5.2×) |

**Finding 1 — range doesn't matter (down to 3 m):** success stays within ~1 pp across unlimited→3 m,
because the coordination-relevant neighbours are always nearby and captured at any of these ranges.
**Finding 2 — presence does matter:** cutting communication entirely (no retrain) costs 4.8–7.9 pp
success and inflates collisions 2.8–5.2×, worse at higher density. **Finding 3:** logged drone-drone
collisions stay at 0.0% with or without communication — LiDAR, not comm, is what prevents drone-drone
collisions; what comm buys is smoother anticipation that keeps drones from being forced into obstacles.
This result is why 8 m was selected as a conservative operating point on the flat part of the curve, and
it directly motivated giving the shared channel actual *content* (sensed obstacles) in the next phase
rather than just position/velocity. Full detail: `ABLATION_RESULTS.md`.

### Collaborative perception — comm is load-bearing under sensor dropout (the anchor result)
Density 0.27, 500 maps, zero-shot. "ON" = neighbours' sensed obstacles fused into a blind drone's own
LiDAR channel; "OFF" = own LiDAR only (no sharing).
| Condition | Drone-level success | Map-level (all 10 reach goal) |
|---|---|---|
| ON (shared map) | **89.34%** | **67.80%** |
| OFF (own LiDAR only) | **45.86%** | **10.40%** |
| **Gap** | **+43.48 pp** | **+57.40 pp**, CI [+52.80, +61.80] |

Across a dropout sweep (500 maps each), the ON/OFF gap **appears only once sensing is actually
impaired**: 0% dropout → ON≈OFF (−1.3 pp, not significant); 10% dropout (~33% blind) → **+41.4 pp**;
20% dropout (~50% blind) → **+50.8 pp**.

### Byzantine attack — persistent fabricated obstacles, dropout-independent
Under ideal (noise-free) sensing, k traitors of 10 broadcasting a fabricated "wall" obstacle:
| k (traitors) | honest success | drop vs k=0 |
|---|---|---|
| 0 | 93.87% | — |
| 1 | 89.70% | −4.16 pp |
| 2 | 82.88% | −10.99 pp |
| 3 | 80.67% | −13.20 pp |

The attack hurts by nearly the same margin regardless of LiDAR-dropout level (+10.5 to +12.0 pp damage
across 0%–60% dropout) — because the fusion rule is a MIN, a fabricated near-obstacle overrides even a
fully-sighted drone's own LiDAR. A stealthier "camouflage" mode (phantom hugging a real obstacle) is the
*stronger* attack: −12.46 pp at k=2 vs −9.36 pp for the plain wall.

### Consistency-trust defense — neutralizes the attack under ideal sensing
k=2 traitors, 500 maps, ideal sensing:
| attack | no defense | defense | recovery |
|---|---|---|---|
| wall | 84.50% | 93.37% | **+8.87 pp** (precision/recall 1.00/0.99) |
| camouflage | 81.40% | 93.20% | **+11.80 pp** (precision/recall 1.00/0.99) |

With no attack present, turning the defense on costs **~0 pp** (no false-gating harm to honest traffic).

### Sensor noise breaks a fixed-tolerance filter — and a noise-aware + temporal filter fixes it
Adding Gaussian noise to every drone's sensed obstacle positions makes two *honest* drones' reports of
the same obstacle disagree by design. A fixed-tolerance consistency check starts treating that
disagreement as a lie: at σ=0.6, a naive filter's precision collapses to 0.23 and it makes outcomes
**worse than no defense at all** (−8 to −27 pp). A noise-aware tolerance ("robust" filter) restores
precision (0.93–1.00) and safe no-harm behaviour, but a camouflage phantom hiding inside the widened
noise band still evades single-frame detection at high noise (recall collapses to 0.12–0.27).

**The fix — temporal trust**: instead of checking one frame, accumulate the *offset* between what a
neighbour reports and what the ego drone itself senses, over many frames. An honest disagreement
averages to zero over time; a camouflage lie has a persistent bias. Camera-ready results (density 0.27,
500 maps, randomized attack, traitor sweep f=1–3, worst case σ=0.6 sensing noise):

| f (traitors) | attack mode | robust-filter recovery | **temporal-filter recovery** | detection recall (robust → temporal) |
|---|---|---|---|---|
| 1 | camouflage | +1.9 pp (CI touches 0 — no better than nothing) | **+7.1 pp** [+5.0, +9.2] | 0.13 → 0.69 |
| 2 | camouflage | +3.4 pp | **+12.2 pp** [+9.8, +14.9] | 0.13 → 0.69 |
| 3 | camouflage | +5.3 pp | **+13.6 pp** [+10.9, +16.5] | 0.12 → 0.68 |
| 2 | wall | +3.7 pp | **+9.7 pp** [+7.5, +11.9] | 0.26 → 0.70 |

Temporal trust is at least as good as the single-frame robust filter at every noise level, never harms
honest traffic when there is no attack (no-harm differences all have confidence intervals spanning
zero), and its advantage over the single-frame filter widens as both the noise and the stealth of the
attack increase — i.e. it wins exactly where the simpler filter degrades.

### Stress test — traitor fraction up to a majority (f = 4–7 of 10)
Pushing past f=3 to the point where an honest drone's own neighbourhood no longer has an honest majority
(f=5 is a tie, f=6–7 are honest-minority), the temporal-filter recovery holds up at every level, with
confidence intervals that exclude zero throughout — while the single-frame robust filter's recovery at
f=7 is statistically indistinguishable from zero:

| f (traitors of 10) | temporal recovery [95% CI] | detection recall | detection precision |
|---|---|---|---|
| 4 | +14.7 [12.0, 17.6] | 0.66 | 0.93 |
| 5 (honest/traitor tie) | +15.2 [11.9, 18.4] | 0.67 | 0.96 |
| 6 (honest minority) | +15.1 [11.6, 18.6] | 0.67 | 0.97 |
| 7 (honest minority) | +10.9 [7.4, 14.5] | 0.66 | 0.98 |
| 7 — single-frame robust filter, for comparison | +1.9 [−1.3, 5.2] (not significant) | 0.26 | 0.94 |

Detection precision rises monotonically from 0.68 (f=1) to 0.98 (f=7) — the filter gets *more* precise as
the threat gets worse — and honest traffic is never penalized (no-harm differences stay flat, CIs span
zero, at every f). The honest caveat: absolute success still falls as f rises (48.8% → 41.9% at f=4→7) —
the filter recovers a stable *fraction* of the ceiling, not full invariance to how many traitors there are.

### Filter-aware adaptive attacker — no free lunch
To test whether an attacker that *knows* the temporal filter exists can defeat it, four adaptive attack
variants were swept (500 maps, f=1–3, σ up to 0.6):
- **Phantom-offset sweep** (how far the camouflage phantom's centre sits from the real obstacle it
  hugs): as the offset grows, both the harm it does *and* the filter's detection recall climb together —
  offset ≈ 0 is harmless and invisible (recall ~0), offset = 2.5 m is harmful (+8.5 to +18.8 pp damage)
  **and** caught (recall 0.66–0.98). The attacker cannot be both stealthy and harmful at once — this
  stealth/harm bind holds at every noise level tested (σ = 0, 0.2, 0.4).
- **Gap, per-frame jitter, and intermittent-duty variants** all fail to beat the filter across f=1–3:
  zero-mean jitter doesn't defeat a test that only cares about the *mean* offset, and diluting how often
  the lie is broadcast (duty cycling) reduces the attacker's own harm faster than it reduces detection.

### Robustness rebuttal experiments — lossy communication and density generalization
Two further stress tests probe whether the temporal-trust result depends on idealized assumptions
(500 maps/cell, σ=0.6, full k∈{1,2,3} × attack-mode matrix):

- **Comm packet loss (each neighbour's broadcast independently dropped, probability p per step):**
  recovery stays positive with a confidence interval excluding zero at every loss level tested
  (p = 0, 0.1, 0.2, 0.3), for both camouflage and wall attacks and all three traitor counts. Camouflage
  recovery declines only gently with loss (e.g. k=3: +13.6 → +13.2 pp from p=0 to p=0.3), detection
  recall stays essentially flat, and detection precision *rises* as packets are lost. The temporal
  advantage over the undefended case holds at every traitor count under loss. This directly answers the
  "your communication model is unrealistically perfect" objection.
- **Density generalization (same trained model, no retraining, densities 0.20/0.24/0.27/0.30):**
  recovery is flat across the calibrated range (~+12 pp at k=2 from 0.20 through 0.27) and still solidly
  positive at the densest setting tested (+8.8 to +10.9 pp at 0.30), confirming the headline result is
  not an artifact of the one density used for the main tables.
- **Independent reproduction check:** the full pipeline was re-run from scratch at k=2 as an unplanned
  sanity check. Every attacked-arm recovery number reproduced **bit-for-bit identical**, including
  confidence intervals; only the two attack-free arms showed ≤0.2 pp run-to-run wobble (source not yet
  pinned down, but every CI in both runs still spans zero there, so no conclusion is affected).

### Methodology checks (validity, not headline results)
- **Baseline reconciliation:** the collaborative-perception anchor model and the noise-robust model used
  for the attack/defense experiments were checked against each other by toggling communication on the
  *same* policy: the anchor model reproduces its own published 89.3%/45.9% ON/OFF split by construction,
  and the noise-robust model shows the same load-bearing communication effect (85.8% ON / 41.8% OFF,
  +44 pp) — confirming the two models sit on one consistent lineage rather than disagreeing baselines.
- **CTDE / communication-leakage audit:** the actor network was checked for what information it actually
  uses (`leak_test_local.py`, zeroing each observation block and measuring how much the trained policy's
  action changes). Result: the actor does not read the critic-only block (0.0% sensitivity) and does not
  rely on an internal-state field (stagnation, 0.2%) that earlier looked like a leak; it does measurably
  use neighbour position/velocity within the 8 m communication range (18.7%/10.4% sensitivity) — a
  legitimate, disclosed modeled-communication channel, not an unmodeled shortcut.

### Earlier exploratory direction — physical ramming (shelved, superseded by the line above)
Before collaborative perception, an earlier direction tested physical "ramming" traitors (drones that
steer to collide) against the clean Phase-B model, and tried three classes of physical defense — all
using perfect-information oracles as *upper bounds* before any training was attempted:

| Defense class | Best result (success %) | vs undefended baseline (95.6/91.1) |
|---|---|---|
| Evasion (LiDAR-aware dodging) | 79.7 / 73.8 | still well short |
| Coordination (a neighbour body-blocks the attacker) | 75.8 / 75.4 | still well short |
| Speed asymmetry (boost + flee) | 79.2 / 76.3 | still well short |

All three oracle upper bounds fell short of an ~85% viability bar, so no defense was trained for this
threat model — a genuine fundamental-limit finding (a decentralized swarm cannot out-manoeuvre an
equal-speed physical rammer in obstacle-dense space by evasion, coordination, or speed alone). The same
investigation found that broadcasting *false* neighbour positions ("comm deception") barely moves the
outcome, and that extending the communication range from 8 m out to 20 m is inert — the trained policy is
overwhelmingly LiDAR-driven. That null result is what motivated the pivot to the current line: instead of
sharing *position*, share *sensed obstacles* — which is exactly what the collaborative-perception
architecture above does, and where the Byzantine attack surface turned out to be real.

Full tables, confidence intervals, and the exact reproduction commands for every number above are in
`Phase_CD/PAPER_MASTER_PLAN.md` (§5, the results ledger) and `Phase_CD/RESULTS_027_CAMERA_READY.md`.
Raw per-condition logs live in `results/` and `Phase_CD/Noise_added/results_027/` — those directories are
generated output; regenerate them with the eval scripts rather than hand-editing.

---

## Model checkpoints

Selected trained models, all under `models/`:

| Model | Role |
|---|---|
| `apex_ultra_glide_v14_comm8_lidar_final.zip` | Phase B clean baseline (M0) — 8 m gated comm + LiDAR, no adversary |
| `raster_slot_fusion_ON_stage2_final.zip` | Collaborative perception, comm-fusion enabled |
| `raster_slot_fusion_OFF_stage2_final.zip` | Same architecture, comm-fusion disabled (ablation) |
| `noise_robust_ON_stage2_final.zip` | Noise-robustness fine-tuned (σ~U[0,0.6] domain randomization), the base for all camera-ready noise/temporal-trust results |
| `apex_ultra_glide_M1_ram_final.zip` | Retrained against physical-ramming traitors (earlier, shelved direction) |

---

## Documentation

- `Phase A/Project_Summary_Step_A.md` — Phase A full narrative, including the bug-fix history
- `PhaseB2/PLAN.md`, `PhaseB2/ARCHITECTURE.md` — MAPPO/CTDE design and the from-scratch reimplementation
- `Phase_CD/PAPER_MASTER_PLAN.md` — single source of truth for the current line: full results ledger,
  parameter justifications, disclosed limitations, file index
- `Phase_CD/Collab_Perception/DESIGN_RASTER_TRUST.md`, `RUNBOOK_RASTER.md` — collaborative-perception
  architecture and how to reproduce the training/eval pipeline
- `Phase_CD/PROJECT_READING_GUIDE.md` — guided tour of the codebase for a new reader
- `CLAUDE.md` — repository conventions and current status snapshot

## License
This project is part of academic research. Please contact the authors for usage permissions.
