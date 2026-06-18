# Implementation Spec — Per-Gate Code Changes (Handoff to Implementer)

**Owner:** Srinivasa · **Created:** 2026-06-18 · **Scope:** `Phase_CD/Collab_Perception/`
**Companion doc:** `ARCHITECTURE_FIX_PLAN.md` (the *why*). This doc is the *how* — exact edits only.

---

## 0. READ THIS FIRST — rules for the implementer

1. **Do not run any command or training automatically.** Make the edit, then show Srinivasa the diff
   and the verification command. Wait for explicit "run it."
2. **One Gate at a time, in order.** Do NOT implement Gate 1 until Gate 0 results are approved, etc.
   Each Gate section says when to stop.
3. **Preserve every leak-safety invariant in §1.** A violation here is what gets the paper rejected
   (the project already survived one CTDE-leakage cleanup — do not reintroduce it).
4. **Edit only the files named in each Gate.** Do not refactor, rename, reformat, or "improve"
   unrelated code. Minimal diffs only.
5. **Match existing style:** `float32` everywhere, no new dependencies, no new global state beyond
   what is specified.

---

## 1. LEAK-SAFETY & BUG-SAFETY INVARIANTS (must hold after every edit)

These are hard constraints. After each edit, re-verify all of them.

- **L1 — Actor reads local only.** The actor/policy path may read **`obs[:178]`** only. Never let any
  actor code path index into `obs[178:]` (that is the 520-d critic/global block). In the extractors,
  `forward_actor` must slice `f[:, :LOCAL_NEW]` and `forward_critic` must slice `f[:, LOCAL_NEW:]`.
  Do not change these slice boundaries unless a Gate explicitly updates `LOCAL_NEW` everywhere at once.
- **L2 — Shared map is comm-gated, never ground truth.** The 48-d shared channel may include an
  obstacle **only if** some *other* drone `j` (a) is within `communication_range`, (b) is **not blind**
  (sender-gating), and (c) senses that obstacle within its `lidar_range`. This is exactly the existing
  logic in `_shared_lidar` (`swarm_env_raster.py:95–111`). Do not let the ego read the global obstacle
  list as its own knowledge. Do not remove the `self.lidar_blind[j]` sender-gate.
- **L3 — Goal position is allowed; the Dijkstra map is the privilege.** Using `self.goal` and the ego's
  own `self.positions[idx]` is legitimate (the goal is the shared, disclosed destination). The thing to
  remove for Gate 0 is the **global Dijkstra routed heading**; replacing it with a straight-line bearing
  is *strictly less* information, so it cannot add leakage.
- **L4 — Observation dimensions stay consistent.** Default layout: local `178` (= 130 base + 48 shared)
  + global `520` = `698`. If a Gate changes any width, it must update **all** of: env `OBS_DIM`/obs
  space, the actor `LOCAL_NEW` in every extractor copy (`train_raster.py`, `eval_raster.py`,
  `feature_importance_raster.py`, `surgical_expand_raster.py`), and the surgery. Gates below are
  designed to **avoid** width changes wherever possible — prefer those.
- **L5 — Training randomness unchanged.** Do not seed the dropout RNG during training. Any new seeding
  is **eval-only** (gated on `reset(seed=...)` being provided).
- **L6 — Probe path intact.** Do not break the existing `probe_lidar_slot` branch (`swarm_env_raster.py
  :144–147`). New code must run *before* or *after* it without altering it.
- **B1 — dtype/shape.** Every obs you build stays `np.float32` and keeps its declared length. Add a
  `assert obs.shape[-1] == EXPECTED` in any self-test you write.
- **B2 — No silent fallbacks.** If a value is missing, raise — do not substitute zeros that could be
  mistaken for "no obstacle."

---

## 2. GATE 0 — Straight-line-bearing probe (cheapest; do this first)

**Purpose:** measure SHARED_MAP feature-importance with the Dijkstra heading **removed**, to prove the
shared map *can* become load-bearing. No training; uses the existing Stage-0 model.

**Files to edit:** `swarm_env_raster.py`, `feature_importance_raster.py`. **No width change. No surgery.**

### Edit 0.1 — `swarm_env_raster.py`, add a flag to `__init__`

FIND (currently lines ~30–36):
```python
    def __init__(self, *args, lidar_dropout=0.0, dropout_sustain=20, use_shared_map=True,
                 probe_lidar_slot=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.lidar_dropout = lidar_dropout          # prob a non-blind drone goes blind this step
        self.dropout_sustain = dropout_sustain      # how many steps it stays blind
        self.use_shared_map = use_shared_map        # False -> comm-OFF (shared block zeroed)
        self.probe_lidar_slot = probe_lidar_slot    # probe-only: shared map -> lidar slot, 650-d
```
REPLACE WITH:
```python
    def __init__(self, *args, lidar_dropout=0.0, dropout_sustain=20, use_shared_map=True,
                 probe_lidar_slot=False, straight_line_goal=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.lidar_dropout = lidar_dropout          # prob a non-blind drone goes blind this step
        self.dropout_sustain = dropout_sustain      # how many steps it stays blind
        self.use_shared_map = use_shared_map        # False -> comm-OFF (shared block zeroed)
        self.probe_lidar_slot = probe_lidar_slot    # probe-only: shared map -> lidar slot, 650-d
        self.straight_line_goal = straight_line_goal  # GATE-0 PROBE: replace the global-Dijkstra
        #   routed heading at obs[2:4] with a naive straight-line bearing (goal-ego, no obstacle
        #   knowledge). Strictly less info than Dijkstra -> cannot add leakage (invariant L3).
```

### Edit 0.2 — `swarm_env_raster.py`, override `obs[2:4]` in `_observe`

FIND (currently lines ~139–142):
```python
    def _observe(self, agent):
        self._sample_dropout()
        idx = self.agent_name_mapping[agent]
        base = super()._observe(agent)        # 650: [local(130), global(520)] ; own lidar at [6:54]
```
REPLACE WITH:
```python
    def _observe(self, agent):
        self._sample_dropout()
        idx = self.agent_name_mapping[agent]
        base = super()._observe(agent)        # 650: [local(130), global(520)] ; own lidar at [6:54]

        if self.straight_line_goal:
            # GATE-0 PROBE: overwrite the Dijkstra heading at obs[2:4] with a unit straight-line
            # bearing to the goal. Uses only self.goal (disclosed destination) + ego position (L3).
            d = self.goal - self.positions[idx]
            n = float(np.linalg.norm(d))
            base[2:4] = (d / n).astype(np.float32) if n > 1e-6 else np.zeros(2, dtype=np.float32)
```
> Leave the rest of `_observe` (the `probe_lidar_slot` branch and the normal raster path) **exactly as
> is**. `self.goal` exists (`swarm_env_phasecd.py:83`); `np` is already imported.

### Edit 0.3 — `feature_importance_raster.py`, add a `--straight-line` switch

(a) After the imports / near `DROPOUT_SUSTAIN = 20` (line ~41), add a module flag:
```python
STRAIGHT_LINE = False  # set by --straight-line CLI flag; Gate-0 probe (remove Dijkstra heading)
```
(b) In `run(...)`, where the env is constructed (currently lines ~91–101), add the kwarg
`straight_line_goal=STRAIGHT_LINE` to the `SwarmLidarEnv_Raster(...)` call. Add it next to
`probe_lidar_slot=False`, e.g.:
```python
        probe_lidar_slot=False,
        straight_line_goal=STRAIGHT_LINE
```
(c) At the top of `main()`, parse and strip the flag BEFORE the positional args are read so positional
indexing is unchanged:
```python
def main():
    global STRAIGHT_LINE
    if "--straight-line" in sys.argv:
        STRAIGHT_LINE = True
        sys.argv = [a for a in sys.argv if a != "--straight-line"]
```
> The positional `sys.argv[1..6]` parsing stays exactly as written; stripping the flag first keeps it valid.

### Gate 0 verification (SHOW to Srinivasa, do not auto-run)
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
# with Dijkstra heading (control):
& $py Phase_CD\Collab_Perception\feature_importance_raster.py models\raster_blind_ON_stage0_final.zip 12 10 0.60 on 30
# without Dijkstra heading (probe):
& $py Phase_CD\Collab_Perception\feature_importance_raster.py models\raster_blind_ON_stage0_final.zip 12 10 0.60 on 30 --straight-line
```
**⏸ STOP. Bring Srinivasa both SHARED_MAP DROP numbers.** Decision in `ARCHITECTURE_FIX_PLAN.md` Gate 0.
Do not proceed to Gate 1 without approval.

---

## 3. GATE 1 — Slot-fusion into the LiDAR channel (REVISED after Gate 0 evidence)

> **Why this section was rewritten (2026-06-18).** Gate 0 showed removing the Dijkstra heading did **not**
> raise SHARED_MAP importance (drop stayed ≈0 / negative in both arms). Combined with `probe_raster.py`
> (~85–90% zero-shot when the shared map is routed into the **LiDAR slot `[6:54]`**) and feature
> importance (~0 when it sits in the separate `[130:178]` slot), the diagnosis is: **the information is
> sufficient, but the policy never reads the separate channel.** So the old "Variant A — fuse into
> `[130:178]`" plan was putting the fusion in the slot the policy *ignores*. **Superseded.** The fix is to
> fuse into the slot the policy already uses: `[6:54]`. **This reuses M0's existing 130-d weights — no new
> architecture, no surgery, no from-scratch training.**

### 3.1 What is already implemented (verify, do not rebuild)
`swarm_env_raster.py` now has a `slot_fusion=False` kwarg and a slot-fusion branch in `_observe`
(returns 650-d): when `slot_fusion=True`, it masks own LiDAR if blind, then if `use_shared_map=True` sets
`base[6:54] = min(own_lidar, shared)`. `eval_slot_fusion_zero_shot.py` runs M0 (130-d actor extractor)
ON vs OFF at lidar=8 m, dropout=0.20. **Leak-safety re-audited and PASSES:** writes only inside `[:130]`
(L1); `_shared_lidar` keeps sender-gating + comm-range (L2); obs width 650 matches M0 (L4); `reset(seed)`
seeds global RNG (`swarm_env_phasecd.py:243`) so ON/OFF dropout is approximately paired.

### 3.2 ⚠ REQUIRED CORRECTION — ONE obstacle channel, not two-48-dim-then-min
**Design reminder (the agreed pivot):** there is **no separate 48-dim shared channel** and **no
min-of-two-48-dim**. The slot `[6:54]` holds a **single** obstacle map cast **once** at `collab_range`
(12 m, M0's native scale). The current code computes own (48-d, /8 m) and shared (48-d, /12 m) and `min`s
them — that re-introduces two channels AND a scale mismatch (own normalized by `lidar_range`=8 m at
`swarm_env_phasecd.py:495`; shared by `collab_range`=12 m at `swarm_env_raster.py:116`). That confound can
inflate ON−OFF as a normalization artifact. Replace it with one cast over the **union** of obstacle sources.

**Fix — add one method, simplify the slot-fusion branch (`swarm_env_raster.py` only).** This is exactly the
proven `_probe_lidar` pattern, generalized: ego's own-sensed obstacles (only when not blind) ∪ neighbor-
shared obstacles (sender-gated, comm-range — only when `include_shared`) ∪ other drones, cast once at
`collab_range`, normalized once. Single 48-dim, single scale, no `min`.
```python
    def _fused_lidar(self, idx, include_shared):
        """Single obstacle channel for slot-fusion: ONE _cast48 over the union of sources, one scale."""
        pos = self.positions[idx]
        c_list, r_list = [], []
        if self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            keep = np.zeros(len(arr), dtype=bool)
            if not self.lidar_blind[idx]:                                   # ego's OWN sensing, within its range
                keep |= (np.linalg.norm(arr[:, :2] - pos, axis=1) <= self.lidar_range)
            if include_shared:                                             # neighbor-shared (sender-gated, L2)
                for j in range(self.n_drones):
                    if j == idx or self.possible_agents[j] not in self.agents or self.lidar_blind[j]:
                        continue
                    if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                        continue
                    keep |= (np.linalg.norm(arr[:, :2] - self.positions[j], axis=1) <= self.lidar_range)
            if keep.any():
                c_list.append(arr[keep, :2]); r_list.append(arr[keep, 2])
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:                                                         # keep M0's drone avoidance
            c_list.append(self.positions[others]); r_list.append(np.full(len(others), self.drone_radius, np.float32))
        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.collab_range) / self.collab_range   # ONE scale (12 m)
```
Then the slot-fusion branch in `_observe` collapses to:
```python
        if self.slot_fusion:
            base[6:54] = self._fused_lidar(idx, include_shared=self.use_shared_map)
            return base.astype(np.float32)
```
> Why this is correct and leak-safe: one `_cast48` at `collab_range` → M0 reads `[6:54]` on its native 12 m
> scale in BOTH arms (no artifact). ON = own ∪ shared ∪ drones; OFF = own ∪ drones (blind → drones/walls
> only). Sender-gating + comm-range preserved (L2); uses only ego/neighbor sensing, never global truth (L2/L3);
> width stays 650 (L4); the old blind-mask block and the `min`/rescale are **deleted**. Do **not** set
> `collab_comm=True`. When ego is blind and `include_shared=True`, this reproduces `_probe_lidar` → expect the
> ~85–90% anchor.

### 3.3 Gate 1 verification (SHOW to Srinivasa, do not auto-run)
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 200
```
Sanity anchor: with the scale fix, the ON arm at dropout=0.20 should be in the neighbourhood of
`probe_raster.py`'s ~85–90% (probe = pure shared on 12 m scale, all neighbours sighted). A wildly lower ON
number means the scale fix or the fusion is still off.

**Interpretation (per `eval_slot_fusion_zero_shot.py`):** ON−OFF > 3 pp → architecture fix validated, info
load-bearing zero-shot → proceed to a *light* fine-tune (1–3 M steps, not from scratch). 0.5–3 pp →
marginal, fine-tune to amplify. ≤0.5 pp → likely fundamental → `OPTION_1`.

> ⚠ Caveat to report with the number: n=200 unpaired-ish SE on the difference is ~4 pp, so a 3 pp call is
> noisy. For the *decision* run n≥500 and (Gate 3) seed the dropout RNG for true pairing + report a CI.

**⏸ STOP. Bring Srinivasa ON, OFF, ON−OFF (after the scale fix). Do not start any fine-tune without approval.**

---

## 4. GATE 2 — Retrain (no new code; commands only)

No code edits. After Gate 1 is approved, retrain ON one stage at a time, checking feature importance
between stages (watch for erosion). All commands are in `ARCHITECTURE_FIX_PLAN.md` §Phase 2. The
implementer's only job here is to **run on request and report the FI number at each ⏸ gate.**

---

## 5. GATE 3 — Honest baseline + hardened eval (only after Gate 2c approved)

Three independent, low-risk edits + one that needs sign-off. Files: `eval_raster.py`, `swarm_env_raster.py`.

### Edit 3.1 — fix eval sustain mismatch (`eval_raster.py`)
FIND (line ~30): `DROPOUT_SUSTAIN = 20`
REPLACE: `DROPOUT_SUSTAIN = 25   # match training Stage 3 (train_raster.py CURRICULUM)`

### Edit 3.2 — eval-only paired dropout RNG (`swarm_env_raster.py`) — preserves L5
Goal: identical blind patterns for ON vs OFF runs so the comparison is paired. Seed **only** when a seed
is passed to `reset` (eval passes one; training does not).
(a) In `reset` (currently lines ~47–52), after `out = super().reset(*args, **kwargs)`, capture the seed:
```python
        seed = kwargs.get("seed", None)
        if seed is not None:
            self._dropout_rng = np.random.default_rng(seed)   # eval: deterministic, paired ON/OFF
        elif not hasattr(self, "_dropout_rng"):
            self._dropout_rng = None                          # training: fall back to global np.random
```
(b) In `_sample_dropout` (currently line ~65), replace the single draw:
```python
            elif np.random.random() < self.lidar_dropout:
```
WITH:
```python
            elif (self._dropout_rng.random() if self._dropout_rng is not None
                  else np.random.random()) < self.lidar_dropout:
```
> This changes **nothing** in training (no seed → `_dropout_rng is None` → global `np.random`, identical
> to today). It only makes seeded eval deterministic.

### Edit 3.3 — bootstrap CI + n≥500 in the gate print (`eval_raster.py`)
At the end of `main()` where `comm_value` is printed (lines ~127–131), in addition to the point
difference, compute a paired bootstrap 95% CI over per-map success indicators and print it. Keep the
existing print; add the CI line. (Requires storing per-map success booleans for ON and OFF; if only one
tag is present in the CSV, skip the CI as today.) Run with `n_maps=500`. Implementer: show Srinivasa the
exact bootstrap snippet before wiring it in.

### Edit 3.4 — honest comm-OFF fallback ⚠ NEEDS SIGN-OFF (do not implement yet)
Replacing the "blind OFF drone sees zeros" strawman with a "last-known-LiDAR / speed-reduction" fallback
is a **modeling decision**, not a mechanical edit. Write the proposed approach (persist each drone's most
recent non-blind `base[6:54]` and reuse it while blind) and bring it to Srinivasa as a design note BEFORE
coding. Leak check: last-known own-LiDAR is the drone's *own* past sensing — not privileged — so it is
leak-safe, but the realism framing must be Srinivasa's call.

### Gate 3 verification (SHOW to Srinivasa)
```
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_blind_ON_final.zip  8 10 0.20 on  500
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_blind_OFF_final.zip 8 10 0.20 off 500
```
**⏸ STOP. Bring Srinivasa ON, OFF, the difference, and its 95% CI.** Gate passes if CI lower bound > 0.

---

## 6. ACCEPTANCE CHECKLIST (implementer ticks before handing back each Gate)

- [ ] Edited only the files named in the Gate; diff is minimal; no reformatting of untouched lines.
- [ ] Invariants L1–L6, B1–B2 all re-verified after the edit.
- [ ] No actor code path reads `obs[178:]`; `LOCAL_NEW`/slice boundaries unchanged (unless the Gate
      explicitly updated them everywhere).
- [ ] Shared channel still comm-range + sender-gated (L2); ego never reads global obstacle truth.
- [ ] Obs length unchanged (698) unless the Gate explicitly changed width in ALL required places.
- [ ] Training randomness unchanged (any new seeding is eval-only).
- [ ] Self-test prints expected shapes/values; identity-regime success within noise.
- [ ] Nothing was run without Srinivasa's go; commands were shown first.

## 7. WHAT THE IMPLEMENTER MUST NOT DO
- Do not modify `swarm_env_phasecd.py`, `swarm_env_step_B10_8_0m.py`, or any `models/*.zip`.
- Do not change `OBS_DIM`, `LOCAL_NEW`, `SHARED_DIM`, or critic width except where a Gate says so.
- Do not remove or weaken the sender-gate (`self.lidar_blind[j]`) or the comm-range check.
- Do not introduce new packages, threads, or global mutable state beyond `STRAIGHT_LINE` / `_dropout_rng`.
- Do not auto-run training or eval. Show the command; wait for Srinivasa.
