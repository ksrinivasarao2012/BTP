# CTDE Leakage Investigation & Reviewer Rebuttal

**Date:** 2026-06-16 · **Model under test:** `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (M0)
**Test script:** `leak_test_local.py` (reproducible) · **Prior memory:** `CTDE_AUDIT_B10.md`
**Purpose:** document whether M0 leaks privileged information (a CTDE violation), and give precise,
honest answers to reviewer questions — including "isn't there still a slight risk?" and "are you sure
there is no leak at evaluation time?"

---

## 1. The concern (plain statement)

M0 was built by **transfer learning**: weights were initialized from `apex_ultra_glide_v14_final.zip`,
which was trained in `swarm_env_step_B10.py`. That **source environment was leaky** — its actor received
**ungated, ground-truth positions and velocities of ALL drones** (omniscience), plus other agents'
internal **stagnation counters**, plus a **ground-truth congestion count**. A reviewer could reasonably
ask: *did the final model inherit that cheating?*

---

## 2. The core principle (why this is answerable cleanly)

**Leakage is an execution-time information-access property, not a property stored in weights.**
Transfer learning copies the *network weights*; it does not copy "the right to see privileged data."
What matters is **what M0's actor is actually fed at run time**, which is decided entirely by M0's
*current* environment (`swarm_env_step_B10_8_0m.py`) and by the network wiring — not by the source model.

Two structural facts about M0's current setup:
1. **Wiring (architecture):** the policy/extractor splits the observation:
   `actor = policy_net(obs[:, :130])`, `critic = value_net(obs[:, 130:])`.
   At deployment/eval, Stable-Baselines3 `predict()` runs **only the actor**. The global block
   `obs[130:650]` is fed *only* to `value_net`, which is **never invoked at execution**.
   ⇒ The global/critic state **cannot** influence actions at eval **by construction**.
2. **Range gating:** in `_observe`, any neighbor farther than `communication_range = 8.0 m` has its
   position/velocity **zeroed** (`swarm_env_step_B10_8_0m.py`, lines 471–501). ⇒ No omniscience; the
   actor only ever receives neighbor data from within an 8 m radio range.

---

## 3. The test (verify, don't assume)

`leak_test_local.py`: collect 4000 real honest-drone observations (no traitors, comm = 8 m,
congestion = LiDAR), take M0's deterministic action for each, then **zero one field group at a time** and
measure how much the action changes (mean L2, relative to action magnitude). If the action is invariant to
a field, the actor does not use it.

### Results

| Field zeroed (in actor block `[0:130]`) | Δ action | Verdict |
|---|---|---|
| **LiDAR** `[6:54]` (sanity check) | **174.8 %** | test is sensitive ✓ (large change when removing real sensing) |
| **GLOBAL / critic block** `[130:650]` | **0.0 %** | actor ignores it (matches the structural guarantee) ✓ |
| **STAGNATION** (neighbors' internal counters) | **0.2 %** | leak did **not** persist — effectively unused ✓ |
| **NEIGH_VEL** (communicated neighbor velocity) | **18.7 %** | actor **uses** it (within 8 m = comm channel) |
| **SYNC_RELVEL** (closest-5 relative velocity) | **10.4 %** | actor **uses** it (within 8 m = comm channel) |

(The LiDAR row is a control: if zeroing the real sensor had *not* changed actions, the test would be
meaningless. It changes them the most — so the test is trustworthy.)

---

## 4. Conclusion (plain words)

- The two things that made the **source** a true CTDE violation are **gone in M0**:
  - **Omniscience** (seeing far-away drones): impossible now — the env zeros anything beyond 8 m.
  - **Internal stagnation state of other agents:** measured **0.2 %** → the actor effectively ignores it.
- The **critic/global state cannot affect actions at eval by construction**, and the measurement confirms it (0.0 %).
- **What M0 genuinely uses** beyond its own LiDAR is **nearby (≤ 8 m) neighbor position + velocity** (~10–19 %).
  This is **not leakage** — it is a **modeled short-range communication channel** (a radio). It is a *design
  assumption*, not privileged omniscience, and it must simply be **disclosed** in the paper.
- Corollary for the deception result: comm **does** influence the action (~19 %), so the correct framing is
  *"the swarm's success is robust to corrupted broadcasts because LiDAR grounds collision avoidance,"* **not**
  *"comm is ignored."*

**One-line verdict:** M0 is not a cheater that slipped through transfer learning. Field-by-field testing
shows it dropped the privileged signals and keeps only a realistic 8 m comm link, which is fine to use as
long as it is disclosed.

---

## 5. Reviewer rebuttal — exact answers

### Q: "There's still a slight risk of leakage, isn't there?"
**A (honest + precise):** There are two categories, and we separate them.
1. **Privileged/global information (true CTDE leak):** *structurally impossible at execution.* The actor
   network only takes `obs[:130]`; the global state `obs[130:650]` is an input to the value head only,
   which is not evaluated during decentralized execution. We additionally verified empirically that zeroing
   the global block changes the policy's action by **0.0 %**, and that the neighbors' internal stagnation
   counters change it by **0.2 %**. So there is **no residual dependence** on privileged data.
2. **The 8 m communication channel:** this is a *modeled, disclosed assumption*, not a leak — each drone
   shares its position/velocity with peers within 8 m (a short-range radio). This is standard for small
   swarms. The only idealization is that it is **noise-free and zero-latency**; we discuss this as a
   limitation and (optionally) show robustness to comm noise/dropout (see §6).
   The honest residual "risk" is therefore **not** privileged information — it is the *optimism of a perfect
   comm link*, which we bound experimentally rather than assume away.

### Q: "Are you sure there is no leak at *evaluation* time?"
**A:** Yes, for privileged information — and the argument is structural, not just empirical:
- At eval, SB3 `predict()` runs **only the actor** (`policy_net(obs[:130])`). The global/critic block is
  literally **not part of the actor's forward pass**, so it cannot affect the action. (The 0.0 % measurement
  is a confirmation of correct wiring, not the sole basis of the claim.)
- Within the actor block, the **only** non-ego fields are neighbor data, and those are **hard-gated to 8 m**
  by the environment (out-of-range → zeros). So at eval the agent can only ever use locally-sensed LiDAR +
  ≤ 8 m communicated neighbor state. Both are available to a real decentralized drone.
- The one thing we do **not** claim is that the 8 m comm is *realistic in fidelity* (it is perfect and
  instantaneous). That is an assumption we disclose, and we can demonstrate the policy degrades gracefully
  under comm noise/latency/dropout if asked (§6).

### Q: "You used transfer learning from a leaky model — doesn't that taint the results?"
**A:** Transfer learning copies weights, not data-access rights. Leakage is determined by what the deployed
network reads, which is fixed by M0's environment and wiring — both verified clean above. The source's
omniscient inputs are physically unavailable to M0 at run time (zeroed beyond 8 m; global block not in the
actor path), so the source's leakage cannot manifest. We confirmed the policy does **not** rely on the
previously-leaked fields (global 0.0 %, stagnation 0.2 %).

---

## 6. What to put in the paper (and an optional pre-empt)

**Mandatory disclosure (one paragraph in System / Observation section):**
> "Each drone observes its own LiDAR (48 rays, 12 m) and receives position and velocity broadcasts from
> peers within an 8 m communication range; communication is modeled as perfect and zero-latency. The
> centralized critic additionally uses the global state during *training only*; it is not used at execution.
> The actor's forward pass consumes only the local + ≤ 8 m communicated observation, preserving
> decentralized execution."

**Optional robustness experiment to pre-empt "are you sure" (recommended):**
Run an **eval-time comm-degradation ablation** — add Gaussian noise / random dropout / latency to the
broadcast position+velocity and report honest_success vs the clean comm baseline. If success degrades
gracefully, it directly answers the reviewer: the policy does not *depend* fragilely on perfect comm, and
its core competence is LiDAR-grounded. (Implementation: reuse the `_falsify_broadcast` hook path or add a
`comm_noise_std` / `comm_dropout_p` to `_observe`; clone an existing eval script.)

---

## 7. Reproduce

```
& "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe" leak_test_local.py
```
Expected: LiDAR large (~175 %), GLOBAL 0.0 %, STAGNATION ~0.2 %, NEIGH_VEL ~19 %, SYNC_RELVEL ~10 %.
Evidence files: this doc, `leak_test_local.py`, memory `CTDE_AUDIT_B10.md` (RESOLUTION section).
