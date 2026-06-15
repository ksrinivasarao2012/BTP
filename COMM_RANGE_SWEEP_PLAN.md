# Communication-Range Sensitivity Sweep — Plan

**Status:** planned (not yet run)
**Owner:** Phase B follow-up experiment
**Last updated:** 2026-06-14

---

## 1. Why are we doing this?

In Phase B we enforce an **8.0 m inter-agent communication range** and a **12.0 m LiDAR sensing range**. A reviewer will immediately ask:

> *"Why 8 m? Why 12 m? Did you just pick numbers that happen to work?"*

Right now we only have **two points**:
- **8 m** (model `v14_8.0m`) → ~91–99% success across densities
- **∞ / unlimited** (model `V14`) → ~91–99% success across densities

These two are **nearly identical**, which on its own is a *weak* result — it looks like communication doesn't matter, and the choice of 8 m looks arbitrary. A single point cannot answer "why this value."

**The fix:** measure performance across a *range* of communication values. This converts an arbitrary-looking constant into an empirically justified design point.

---

## 2. What is the purpose?

The sweep achieves three things at once:

1. **Justifies 8 m** — by showing it sits on the *flat* (no-degradation) part of the curve, not cherry-picked.
2. **Turns a weak result into a real finding** — a single "8 m ≈ unlimited" point becomes a **degradation curve** showing *where* communication starts to matter.
3. **Pre-empts the "arbitrary value" criticism** — the reviewer sees the full trade-off, not one hand-picked number.

**Supporting evidence we already have:** the binding diagnostic (`check_comm_binding.py`) showed the 8 m gate binds in ~10% of decision steps at density 0.30 but almost never removes a *nearest-5* neighbor. The sweep extends this: at tighter ranges (5 m, 3 m) the gate should bind hard and remove critical neighbors, so performance should drop — producing the curve.

---

## 3. How are we doing it?

### 3.1 Range set

Final curve: **{3 m, 5 m, 8 m, ∞}**

| Range | Model | Status |
|-------|-------|--------|
| ∞ (unlimited) | `V14` | ✅ already trained + evaluated |
| 8 m | `v14_8.0m` | ✅ already trained + evaluated |
| 5 m | `v14_5m` | ⬜ to train + evaluate |
| 3 m | `v14_3m` | ⬜ to train + evaluate |

> **12 m is intentionally dropped** — it is uninformative. Since 8 m ≈ ∞ already, 12 m (which lies between them) will also ≈ ∞. Testing it wastes a cycle.

### 3.2 Why each range must be **retrained** (not just re-evaluated)

We **cannot** take the V14 model and simply evaluate it at 3 m. V14 never saw zeroed-out (out-of-range) neighbors during training, so evaluating it at 3 m would measure a **train/test distribution mismatch**, not the true cost of a 3 m communication range. 

Therefore each range gets its **own model**, trained with that range enforced:
- **Transfer-learn from V14** (same as we did for 8 m),
- **Identical curriculum 0.30 → 0.35** (same as V14 and v14_8.0m),
- so the **only** difference between every model in the sweep is the communication range → clean causal comparison.

### 3.3 Mechanics (scripts to build)

1. **Parameterize the env** — make `communication_range` a constructor argument (default 8.0, backward-compatible, does not affect the existing 8 m run).
2. **Generic train script** — `python train_comm.py <range>` → fine-tunes from V14 at that range, saves a range-named model.
3. **Generic eval script** — `python eval_comm.py <range>` → runs the density sweep with that range enforced, using the **fixed** (de-double-counted) counting logic and the **same seeds** as all prior sweeps.
4. **Plot script** — reads all results and draws **success rate vs communication range**.

### 3.4 Controls held constant (so only range varies)

- Transfer source: V14 weights
- Curriculum: 0.30 → 0.35, 5M steps
- LiDAR range: 12 m (unchanged)
- Reward function: unchanged
- Eval seeds / maps: identical to existing sweeps (paired comparison)
- Counting logic: the fixed `finished`-set version (verified in both current eval scripts)

---

## 4. Scope options & time

Grounded in the actual v14_8.0m run (~50 min to train 5M steps; ~1 hr for a full 5-density eval). Runs **sequentially and unattended** — start it, check back.

| Scope | Eval densities | Train (2 models) | Eval | Total |
|-------|----------------|------------------|------|-------|
| Lean | 0.30 only | ~1.7 hr | ~50 min | **~2.5 hr** |
| **Recommended** | 0.20 + 0.30 | ~1.7 hr | ~1.5 hr | **~3–3.5 hr** |
| Full | all 5 densities | ~1.7 hr | ~2 hr | **~4 hr** |

**Recommended scope = 0.20 + 0.30.** One density gives a clean curve; two shows the trend holds across difficulty for little extra time. All five is overkill for this figure.

---

## 5. What will the result look like?

### 5.1 Expected data table (illustrative — actual numbers from the run)

| Comm range | Binds often? | Expected success @ 0.30 | Interpretation |
|------------|--------------|--------------------------|----------------|
| ∞ | never | ~91% (measured) | baseline |
| 8 m | ~10% of steps, far neighbors only | ~91% (measured) | no degradation |
| 5 m | frequently, starts hitting near neighbors | slightly lower (TBD) | onset of degradation |
| 3 m | constantly, removes nearest neighbors | clearly lower (TBD) | communication-starved |

> Note: 3 m is **below** the ~3–4 m spawn-cluster size, so its gate will bind hard and constantly. A noticeably lower 3 m result is **expected and desirable** — it is the degradation that gives the curve meaning. Do not be alarmed by it.

### 5.2 Expected figure

```
Success
 rate
 (%) │
 100 │  ●────────●────────●            ← ∞, 8m, (and 12m) flat: comm not limiting
     │                     \
     │                      \
  85 │                       ●         ← 5m: degradation begins
     │                        \
     │                         \
  70 │                          ●      ← 3m: communication-starved
     │
     └─────┬─────┬─────┬─────┬──────►  Communication range (m)
           3     5     8     ∞
                       ↑
              our chosen value (8m) sits on the flat region
```

### 5.3 The sentence this enables in the paper

> *"Performance is invariant to communication range down to ~8 m and degrades only below ~5 m, where the limit begins removing coordination-critical nearest neighbors. We therefore select 8 m as a conservative operating point on the flat region of this curve — large enough to be unrestrictive, small enough to demonstrate decentralized operation."*

This makes 8 m an **empirically justified** choice, not an arbitrary one.

---

## 6. Honest caveats

- **This justifies "robust to 8 m," not "robust to severe comms."** 8 m is on the flat part precisely because the swarm flies in tight formation. The curve makes that explicit and honest.
- **Each tighter range needs its own fine-tune** — there is no shortcut via re-evaluation (see 3.2).
- **The 3 m model may train to clearly lower performance** — expected, and the point of the experiment.
- **This is a Phase B supporting experiment**, not the headline. The headline contribution remains the Phase C trust mechanism.

---

## 7. Deliverables

- [ ] Parameterized env (`communication_range` constructor arg)
- [ ] `train_comm.py` (generic, range-argument)
- [ ] `eval_comm.py` (generic, range-argument, fixed counting, same seeds)
- [ ] `plot_comm_sweep.py` (success vs communication range)
- [ ] Trained models: `v14_5m`, `v14_3m`
- [ ] Results CSVs for 5 m and 3 m (combine with existing 8 m, ∞)
- [ ] Final figure: success vs communication range
- [ ] Paper subsection text (sentence in 5.3)
