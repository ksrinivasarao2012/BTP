# PATH B — Analysis / Characterization Paper (Honest, ~80% Already Done)

**Date:** 2026-06-16 · **Read first:** `PHASE_CD_PATHS_A_AND_B.md`.
**This file = the full write-up plan for Path B**, self-contained for a fresh chat.

---

## 1. The thesis (one paragraph)

> A LiDAR-grounded MARL drone swarm (CTDE PPO, 10 drones) is **robust to communication attacks** — deception
> (false position/velocity broadcasts) and jamming/blackout are **near-inert** because local LiDAR sensing
> overrides them — but is **vulnerable to physical adversaries** (ramming traitors). The physical loss scales
> **linearly** (~9pp per rammer) and is **fundamental**: even an *oracle* evader with perfect, ground-truth,
> obstacle- and LiDAR-aware dodging **cannot recover it** (caps at ~75-80% vs 95.6/91.1 clean). This motivates
> **coordination-based** defense (future work), since per-agent evasion is provably insufficient.

This is an honest "what works, what doesn't, and the **fundamental limit**" paper. Lower novelty than a working
defense, but **fully supported by data already collected** and zero risk of another bounded-angle surprise.

---

## 2. Evidence already in hand (results to write up)

| Result | Numbers | File(s) |
|---|---|---|
| CTDE-clean navigator | 95.55 / 91.10 (d=0.20/0.30) | `models/apex_ultra_glide_v14_comm8_lidar_final.zip` ✅ M0 |
| Feature-importance ablation | 2 methods agree | ⚠ **LEAKY** (ran on v14_8_0m) → RE-RUN on M0 |
| Comm range sweep | flat 3-8-∞ | ⚠ **LEAKY+confounded** (comm3/5=env, ∞=omniscient) → RE-RUN, congestion=lidar all ranges |
| Comm blackout | −5-8pp | ⚠ **LEAKY** (ran on v14_8_0m) → RE-RUN on M0 |
| **Deception probe (inert)** | ~0pp at f=2,3 | `probe_deception.py`, results/phase_c_probe/ |
| **Ram scaling** | f1≈−9, f2≈−18, f3≈−25 pp | `probe_ram.py`, `results/phase_c_probe/probe_ram_f*.csv` |
| **Oracle ceiling (naive)** | 77.9 / 74.6 | `probe_ram_oracle.py`, `oracle_evade_f2_d2.0.csv` |
| **Oracle ceiling (smart LiDAR)** | 75.0 / 79.6 | `probe_ram_oracle_smart.py`, `oracle_smart_f2.csv` |
| CTDE leakage test | clean (action invariant to global block) | (leakage test) |
| Collision-type logging fix | drone-coll ~10%/rammer | env `_observe`/`step` |

> ⚠ **Leakage audit (see `MODEL_LEAK_LEDGER.md`):** the 3 rows marked LEAKY were produced on
> `v14_8_0m` (ground-truth congestion) / `v14_final` (omniscient). Re-run on the clean **M0
> `comm8_lidar`** with `congestion=lidar` before citing. The probe/oracle/ram/deception rows are
> already on M0 (clean). Conclusions are expected to hold (clean M0 leans *more* on its own LiDAR).

References embedded everywhere: M0 ram f=2 = 77.4/73.5 · baseline = 95.6/91.1.

---

## 3. Remaining tasks (small — the ~20% left)

1. **Confirm the oracle ceiling at full 200 maps** (currently 30-map; signal already consistent).
   `python probe_ram_oracle_smart.py 2 models/apex_ultra_glide_v14_comm8_lidar_final.zip 200`
   `python probe_ram_oracle.py 2 2.0 models/apex_ultra_glide_v14_comm8_lidar_final.zip 200`
2. **One baseline** for the navigator comparison (ORCA via `evaluate_orca.py` if present, else cite).
3. **Ram scaling completeness:** ensure f=1,2,3 all saved (and optionally f=4 to show the breakdown trend).
4. *(Optional)* multi-seed (3 seeds) on the headline model for error bars.
5. **Write-up** (below).

---

## 4. Paper structure (IEEE; see `BTP_Final_Report_Outline.md`)

1. **Intro** — resilient swarm navigation; threat model (comm attacks vs physical adversaries); contribution =
   *characterization of the threat surface + a fundamental limit on local evasion.*
2. **System** — CTDE PPO navigator, split obs (202D local / 530D global), 48-ray vectorized LiDAR, reward terms.
3. **Navigator performance** — 95.6/91.1; feature-importance ablation (what the policy relies on).
4. **Communication is robust to attack** *(security property)* — range sweep flat; blackout −5-8pp; **deception inert**
   (LiDAR overrides lies). Explains *why*: sensing-grounded policy.
5. **Physical adversaries are the real threat** — ram scaling (linear ~9pp/rammer); collision-type breakdown.
6. **A fundamental limit** *(the key result)* — oracle evasion (naive + smart-LiDAR) both cap ~75-80%; rammer
   converts collisions→timeouts, not →success. Per-agent evasion is provably insufficient.
7. **Implication / future work** — physical resilience needs **coordination** (threat-sharing + trust), not local
   evasion. (Forward-reference Path A / `PATH_A_COORDINATION_DEFENSE.md`.)
8. **Conclusion.**

---

## 5. Honest framing notes (do NOT overclaim)

- Deception is inert **in this design** (comm ≤ LiDAR range, sensing-grounded) — state the scope, don't claim universality.
- Oracle is an **upper bound** (uses true positions) — it bounds *feasibility*, it is not a deployable policy.
- honest_success excludes traitors from the denominator — state this explicitly.
- No fabricated numbers; every claim cites a CSV in `results/phase_c_probe/`.

---

## 6. Invariants for a fresh chat (same as Path A §4)

Env `swarm_env_step_B10_8_0m.py`; load with `MAPPO_Policy_B5`/`MAPPO_Extractor_B5` (copy from
`probe_ram_oracle_smart.py`); densities [0.20,0.30]; congestion_mode="lidar"; comm=8.0; seeds
`900_000_000 + int(d*100)*10_000 + map_idx + attempts*5_000`; `finished` set to avoid double-count.
M0 = `models/apex_ultra_glide_v14_comm8_lidar_final.zip`.
