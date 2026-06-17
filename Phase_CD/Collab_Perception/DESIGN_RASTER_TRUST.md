# Design — Rasterized shared-obstacle map + trust-weighted fusion (the working architecture)

## Why this design (what the probes forced us to)
- Sharing **individual** obstacles scales badly: nearest-per-neighbor (compact, 27-d) = **50%** blind; even
  k=5 nearest (135-d) = only **81%**. "Too huge and not enough." (`ego_blind_designA.csv`)
- Sharing **all** obstacles **rasterized into the LiDAR grid** = **88/90** blind (`full_blind`). Rasterization is
  **fixed-size regardless of obstacle count** — that's the property the per-obstacle channel lacked.
- So: navigate on a **rasterized shared-obstacle map** (fixed, rich), and put **attribution/trust in the
  fusion step**, not the observation.

**Established facts (no need to re-probe):** rasterized shared-map sufficiency = `full_blind` = **88/90**
(the env's `_ray_cast` already emits 16 sectors × {min,mean,std}; `full_blind` is that, ego-blind). CTDE-clean
(each value reconstructed from neighbor broadcasts + own position).

---

## Actor architecture
Observation (actor reads the local part; critic reads global 520):

| block | indices | dims | notes |
|---|---|---|---|
| existing local (incl. **own** LiDAR `[6:54]`) | `0:130` | 130 | own-lidar is the block masked under dropout |
| **shared-obstacle map** (rasterized, trust-filtered) | `130:178` | **48** | 16 sectors × {min,mean,std}, ego frame |
| *(optional)* trust-state block | `178:187` | +9 | per-neighbor trust scores (or +1 aggregate) — lets the policy be cautious |
| global / critic | `178:` (or `187:`) | 520 | unchanged |

Actor net (same shape as M0, wider input): `Linear(178 → h0) → … → action(2), log_std`. Critic unchanged.
**Surgery:** expand the actor's first layer `130 → 178`, zero-init the 48 new cols (same as A1, S=48).

---

## Trust-weighted fusion module (where the trust scores live)
```
per-neighbor obstacle reports (attributable: each tagged with neighbor j)
        │
   TRUST MODULE  — per-neighbor score t_j, updated LOCALLY:
     • agreement with ego's own LiDAR when active (does ego see what j reports?)
     • cross-neighbor consensus (outlier vs majority) — works even when ego is blind
     • temporal consistency of j's reports
        │  exclude / down-weight low-trust neighbors
        ▼
   trust-filtered obstacle set  ──►  rasterize (16 sectors, ego frame)  ──►  48-d map  ──► actor obs[130:178]
```
- **Attribution** is on the raw per-neighbor reports (trust can name + discount a liar); the 48-d map is the
  *output* of filtering, so the actor obs stays small.
- **Decentralized / no leak:** every `t_j` uses only the ego's own sensing + received broadcasts.
- **Module, not baked into the net** → ablatable; compare vs robust-fusion baselines (median, **Krum**,
  trimmed-mean) and report traitor-ID ROC. This is what makes the T-Cell mechanism's value *measurable*.

---

## Threat & dropout model (Lever 2 = sensor degradation)
- **Per-step, per-drone LiDAR dropout** (sensor failure: dust/occlusion/fault), sampled once/step, ideally
  **sustained** (a drone stays blind for a stretch, not flicker). Used in BOTH places consistently:
  - mask drone i's own LiDAR `[6:54]` if `lidar_blind[i]`;
  - **a blind sender shares nothing** — gate neighbor j's contribution by `not lidar_blind[j]` (the leak you
    caught: a blind drone cannot broadcast what it does not sense). Commit to the **failure** interpretation.
- **Attack (later):** a traitor broadcasts **false hazards** (phantom obstacles / hides real ones) on its
  reports → poisons the fused map → the trust module must catch it.

---

## Verification plan (oracle-before-build, honestly scoped)
1. **Representation sufficiency** — DONE (`full_blind` = 88/90). No re-probe needed (it *is* the S=48 raster).
2. **The architecture gate (training-only; no zero-shot shortcut for a separate channel):**
   build env (48-d shared-map channel + dropout + sender-gating) → surgery (130→178) → train
   **comm-ON vs comm-OFF under partial dropout**. `comm_value = ON − OFF`.
   - The bar is **partial-dropout**, not full-blind: the ego has its own lidar most steps and needs the map
     only during blind windows — a much easier bar than the 88 worst case.
   - ⛔ gate: `comm_value ≥ ~5 pp` AND feature-importance shows the shared-map block load-bearing.
3. **Attack + trust (only if gate passes):** false-hazard traitor → no-defense drop → trust-weighted fusion →
   recovery, at f=1,2,3, vs median/Krum baselines + traitor-ID ROC + no-traitor cost.

---

## Build steps + checkpoints
| step | artifact | check |
|---|---|---|
| B1 | `swarm_env_raster.py`: 48-d shared-map channel (ray-cast trust-filtered shared obstacles into a separate slot) + per-step dropout mask + sender-gating | obs dim = 698; dropout off ⇒ reproduces baseline |
| B2 | `surgical_expand_raster.py` (130→178, zero-init) | ⛔ expanded M0 @ no-dropout reproduces M0 |
| B3 | `train_raster.py` comm-ON/OFF under partial dropout | ⛔ **gate**: comm_value ≥ ~5 pp |
| B4 | false-hazard attack + trust module + baselines | ⛔ trust recovers vs Krum/median; ROC reported |

## Honest status
- The hard navigational-sufficiency question is **settled** (88) and the architecture is now fixed-size,
  attributable, decentralized, and small (48, +9 optional).
- The remaining real risk is the **same A2 risk**: will training make the policy *use* a separate channel?
  Lever 2's **partial dropout** is the mechanism that should create the gradient pressure that the no-dropout
  A2 lacked — tested at step B3. That is the make-or-break gate.
