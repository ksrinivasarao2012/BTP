# Parameter Justification & Citations — v14 (TA-MAPPO Phase B)

> **Created:** 2026-06-13
> All values verified from `swarm_env_step_B10.py` (the real v14 env). Each parameter
> is tagged with a **category** and, where a citation is appropriate, a **real,
> verifiable reference** (URL included).
>
> **Categories**
> - **A — Realism-anchored:** justified by a real sensor/platform/standard → needs a citation.
> - **B — Design / convention:** a stated design choice → no citation needed (self-justifying).
> - **C — Empirically calibrated:** justified by our own experiments → cite our own results.
>
> ⚠️ **Author note:** open each link and confirm the exact figure before putting it in the
> IEEE report. These are real sources located via search; you are the one signing the citation.

---

## Quick map

| Parameter | Value (line) | Category | Citation needed? |
|---|---|---|---|
| LiDAR max range | 12.0 m (L336) | A | ✅ RPLIDAR A1 |
| LiDAR angular resolution / ray count | 192 rays, ~1.9° (L62-64) | A + B | ✅ RPLIDAR A1 + ray-DRL |
| LiDAR obs encoding | 48-D (16 sectors × min/mean/std) (L368-372) | B | ❌ design |
| Communication range | 8.0 m (8_0m env L27) | A + B | ✅ UWB + field-scale |
| Drone radius | 0.15 m (L33) | B | ❌ (see note) |
| Safety radius | 0.19 m (L34) | B | ❌ design |
| Max velocity | 2.0 m/s (L32) | A + B | ✅ swarm-RL |
| Control rate `dt` | 0.1 s = 10 Hz (L30) | A + B | ✅ RPLIDAR A1 scan rate |
| Episode length | 1200 steps = 120 s (L31) | B | ❌ design |
| Field size | 20 × 20 m (L35) | B | ❌ design |
| Number of drones | 10 (L23) | B | ❌ design |
| Action space | 2D velocity ∈ [-1,1]² (L45) | B | ❌ convention (cite swarm-RL optional) |
| Observation (CTDE) | 650-D = 130 local + 520 global (L47-48) | A + B | ✅ MAPPO/CTDE |
| Algorithm | PPO / MAPPO (CTDE) | A | ✅ MAPPO |
| Obstacle density | 0.25–0.27 | C | ✅ our calibration |

---

## A — Realism-anchored parameters (cite these)

### 1. LiDAR max range = 12.0 m  &  10 Hz scan  &  ~1° angular resolution
**Exact hardware match: Slamtec RPLIDAR A1** — a 360° 2D laser scanner with **12 m range**,
1° angular resolution, 0.2 cm distance resolution, configurable up to **10 Hz** scan rate.
Our `max_range = 12.0`, `dt = 0.1 s` (10 Hz), and dense ray sampling line up with this unit.
- Slamtec RPLIDAR A1 datasheet (PDF): https://cdn-shop.adafruit.com/product-files/4010/4010_datasheet.pdf
- Product spec page: https://www.dfrobot.com/product-1125.html

> Suggested text: *"Each agent carries a simulated 360° 2-D LiDAR with a 12 m maximum range and a
> 10 Hz update rate, matching the specification of a commodity scanner (Slamtec RPLIDAR A1)."*

### 2. Ray-based LiDAR observation (192 rays)
The ray-based perception model — N evenly-spaced rays each returning nearest-obstacle distance
up to a max range — is the standard observation for LiDAR-driven DRL navigation.
- Hybrid UAV obstacle avoidance (reactive sensing + LiDAR + DRL), ScienceDirect 2026: https://www.sciencedirect.com/science/article/pii/S2590123026011850
- Autonomous aerial obstacle avoidance using LiDAR sensor fusion, PMC: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10306222/

### 3. Communication range = 8.0 m
Two-part justification: (a) **field-scale** — 8.0 m ≈ 40% of the 20 m arena, giving a meaningful
local neighborhood without global omniscience (design, no citation); (b) **realism** — onboard
inter-drone ranging/communication (UWB) is standard in real aerial swarms and operates at this
order of range with cm-level accuracy.
- Land & Localize: infrastructure-free nano-drone swarm with UWB localization, arXiv:2307.10255: https://arxiv.org/abs/2307.10255
- Onboard Ranging-based Relative Localization & Stability for Lightweight Aerial Swarms, arXiv:2003.05853: https://arxiv.org/pdf/2003.05853

> Suggested text: *"Inter-agent observation is limited to neighbours within an 8.0 m communication
> range (≈40% of the arena width), consistent with onboard UWB ranging used in real aerial swarms
> [2307.10255, 2003.05853], and precluding reliance on global privileged state (cf. our CTDE analysis)."*

### 4. Max velocity = 2.0 m/s
A conservative indoor swarm speed; decentralized quadrotor-swarm RL controllers operate in this
velocity regime. Cite a representative swarm-RL platform/paper.
- Decentralized Control of Quadrotor Swarms with End-to-end Deep RL, arXiv:2109.07735: https://arxiv.org/pdf/2109.07735
- QuadSwarm: Modular Multi-Quadrotor Simulator for Deep RL, arXiv:2306.09537: https://arxiv.org/abs/2306.09537

### 5. Algorithm & CTDE observation (650-D = 130 local + 520 global)
PPO trained MAPPO-style: centralized critic (global 520-D), decentralized actor (local 130-D) —
the standard CTDE pattern for cooperative multi-agent control.
- MAPPO for cooperative multi-UAV (target search), Springer 2025: https://link.springer.com/article/10.1007/s44163-025-00411-9
- Multi-Agent Deep RL for Multi-Robot Applications — Survey, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC10098527/

---

## B — Design / convention parameters (NO citation needed — state the rationale)

- **LiDAR encoding 48-D (16 sectors × {min, mean, std}):** 192 raw rays are compressed into 16
  angular sectors, each summarized by nearest distance, mean clearance, and clutter variance —
  a fixed-size, rotation-structured descriptor.
- **Drone radius 0.15 m / safety radius 0.19 m:** a conservative collision-bounding circle
  (not a physical frame dimension). *Honest note:* this is larger than a nano-drone (a Crazyflie
  is ~92 mm motor-to-motor), so do **not** cite Crazyflie for size — frame 0.15 m as a safety
  bounding radius. (Crazyflie ref, if you cite the nano-swarm class elsewhere: https://en.wikipedia.org/wiki/Crazyflie_2.0)
- **Episode length 1200 steps (120 s @ 10 Hz):** comfortably exceeds the ~14 s needed to cross the
  28 m diagonal at 2 m/s, allowing detours without artificial truncation.
- **Field 20 × 20 m — anchor to sensor-to-field ratios:**
  LiDAR range 12 m = **60%** of field width; communication range 8 m = **40%**; goal–start min
  distance 8 m; diagonal 28.3 m (~14 s at 2 m/s vs a 120 s episode → ~8× margin). At 20 m both
  perception (60%) and communication (40%) are *large but strictly local* → a genuinely
  partially-observable problem. If field ≤12 m the LiDAR sees wall-to-wall; if field ≤8 m comms are
  always global → both degenerate. So 20 m keeps the ranges in a meaningful 40–60% band.
- **Number of drones = 10 — anchor to the threat model:**
  10 enables a clean adversarial sweep of 10/20/30/40% (1–4 traitors); the worst case 6 honest /
  4 traitor = 60/40 is a *bare-majority-honest* Byzantine setting. The global obs is sized for 10
  (`g_pos = n_drones*2`, etc.).

> **HONEST LIMITATION (read this).** The above makes these choices *defensible*, not *derived*.
> The 40–60% ratio argument justifies a *range* of field sizes (≈15–25 m), not uniquely 20; and
> "10 drones for a 40% adversary sweep" is a reasonable threat model, not a forced value — 8 or 12
> would also work. **Arena size and swarm size are genuinely design choices**; no paper or law fixes
> them. The residual vagueness is irreducible *unless* you run an **ablation** (e.g. field ∈ {15,20,25},
> swarm ∈ {6,10,14}) and show the conclusions hold — that is the only way to fully remove it.
> Reviewers normally *accept* stated, reasonable design choices for these two, so this is usually fine.
>
> ⚠️ There is **no single "10-drone benchmark paper"** — do not claim one. Optional consistency refs:
> [arXiv:1807.06613], [Sage 2024], [MDPI Drones 2025].
- **Action space 2D velocity ∈ [-1,1]²:** normalized continuous velocity command (standard for
  swarm-RL; optionally cite arXiv:2109.07735 above).

---

## C — Empirically calibrated parameter (cite our own results)

- **Obstacle density 0.25–0.27:** chosen via a 10,000-map BFS solvability sweep at v14 parameters.
  0.25 = 97.86% solvable, 0.26 = 96.53%, 0.27 = 96.78% (last ≥95% pass), 0.28 = 94.30% (crosses the
  fairness bar), with Wilson 95% CIs. Agent success (real v14 model) stays high across the range.
  **Cite:** [`FINAL_PARAMETER.md`](FINAL_PARAMETER.md) (this repository).

---

## Honest gaps

- **Control rate 10 Hz:** I could not find a paper using *exactly* 2 m/s + 10 Hz; literature low-level
  controllers often run faster (25–500 Hz). Our 10 Hz is a *high-level decision/velocity* rate and is
  justified by matching the LiDAR's 10 Hz sensing rate (RPLIDAR A1) — state it that way, not as a
  low-level control claim.
- **Drone radius 0.15 m:** larger than a nano platform; justify as a safety bounding radius, not a
  hardware frame size.
- Verify every linked figure against the source before final submission.

## Sources
- [Slamtec RPLIDAR A1 datasheet](https://cdn-shop.adafruit.com/product-files/4010/4010_datasheet.pdf)
- [RPLIDAR A1 product spec (DFRobot)](https://www.dfrobot.com/product-1125.html)
- [Land & Localize — UWB nano-drone swarm (arXiv:2307.10255)](https://arxiv.org/abs/2307.10255)
- [Onboard Ranging-based Relative Localization (arXiv:2003.05853)](https://arxiv.org/pdf/2003.05853)
- [Hybrid UAV obstacle avoidance + DRL (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2590123026011850)
- [Aerial obstacle avoidance via LiDAR fusion (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10306222/)
- [MAPPO multi-UAV target search (Springer)](https://link.springer.com/article/10.1007/s44163-025-00411-9)
- [MARL multi-robot survey (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10098527/)
- [Decentralized quadrotor swarm RL (arXiv:2109.07735)](https://arxiv.org/pdf/2109.07735)
- [QuadSwarm simulator (arXiv:2306.09537)](https://arxiv.org/abs/2306.09537)
- [Survey on UAV Control with MARL (MDPI Drones 2025)](https://www.mdpi.com/2504-446X/9/7/484)
- [Deep RL for Swarm Systems (JMLR 2019, arXiv:1807.06613)](https://arxiv.org/abs/1807.06613)
- [RL-based aggregation for robot swarms — bounded arena, ~10 robots (Sage 2024)](https://journals.sagepub.com/doi/10.1177/10597123231202593)
- [Multi-UAV Formation Control with Obstacle Avoidance via RL (arXiv:2410.18495)](https://arxiv.org/pdf/2410.18495)
