# Phase 4 — Trust-Aware Defense Against Byzantine Neighbors

**Owner:** Srinivasa  
**Date:** 2026-06-19  
**Status:** Ready to implement  
**Scope:** Add T-Cell trust gating to defend against traitor drones

---

## Overview

**Phase 3 Result (Drone-Level):**
```
ON  (slot fusion + shared):   94.12%
OFF (own LiDAR only):         53.08%
Difference:                   +41.04 pp
```

Communication is load-bearing. Now add adversarial resilience: **T-Cell trust module** learns to down-weight malicious neighbors.

---

## 1. Architecture: T-Cell Trust Gate

**Current slot-fusion pipeline (Phase 3):**
```
Ego LiDAR + Sender-gated neighbor obstacles → min() → obs[6:54] → M0 actor
```

**Phase 4 modification:**
```
Ego LiDAR + Weighted neighbor obstacles → min() → obs[6:54] → M0 actor
                         ↑
                    T-Cell gate
                  (learned per-neighbor)
```

**T-Cell Gate = learned weights [w₀, w₁, ..., w₉] for each neighbor.**
- w ∈ [0, 1]: how much to trust this neighbor's obstacles
- Training: learn to set w=1 for honest neighbors, w≈0 for traitors
- Inference: actor navigates using trusted obstacles only

---

## 2. Traitor Models (Byzantine Neighbors)

**Three traitor behaviors (test separately):**

### A. False Obstacle Broadcasting
- Traitor broadcasts **fake obstacles** (not in the world)
- Goal: make honest drones crash into non-existent barriers
- Attack: ego drone avoids phantom obstacles, loses navigation

### B. Silence (No Broadcasting)
- Traitor goes mute: broadcasts nothing
- Goal: starve the shared map when ego is blind
- Attack: ego drone gets no help during LiDAR dropout

### C. Ramming
- Traitor intentionally moves toward ego drone
- Goal: physical collision (past work showed -9 pp/rammer)
- Attack: ego must avoid traitor while navigating

**Focus for Phase 4:** Start with **A (false obstacles)** and **B (silence)**.

---

## 3. Implementation Steps

### Step 1: Add T-Cell Gate to `swarm_env_raster.py`

**File:** `swarm_env_raster.py`

Add new method (after `_fused_lidar`):

```python
def _fused_lidar_with_trust(self, idx, trust_weights=None):
    """Fused obstacles with per-neighbor trust gating.
    
    trust_weights: [w₀, w₁, ..., w₉] where w ∈ [0,1]
                   If None, defaults to all-1s (no gating).
    """
    pos = self.positions[idx]
    c_list, r_list = [], []

    # Ego's own obstacles (always trusted)
    if not self.lidar_blind[idx] and self.obstacles:
        arr = np.array(self.obstacles, dtype=np.float32)
        c_list.append(arr[:, :2])
        r_list.append(arr[:, 2])

    # Sender-gated neighbor obstacles (now with trust weighting)
    if self.obstacles:
        arr = np.array(self.obstacles, dtype=np.float32)
        centers, radii = arr[:, :2], arr[:, 2]
        
        for j in range(self.n_drones):
            if j == idx or self.possible_agents[j] not in self.agents:
                continue
            if self.lidar_blind[j]:  # SENDER-GATING
                continue
            if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                continue
            
            # Get trust weight for neighbor j
            w_j = trust_weights[j] if trust_weights is not None else 1.0
            if w_j < 0.01:  # Skip if trust is near-zero
                continue
            
            dj = np.linalg.norm(centers - self.positions[j], axis=1)
            keep = (dj <= self.lidar_range)
            
            if keep.any():
                c_list.append(centers[keep])
                r_list.append(radii[keep] * w_j)  # Scale radius by trust weight

    # Drones
    others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
    if others:
        c_list.append(self.positions[others])
        r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))

    if c_list:
        centers = np.concatenate(c_list)
        radii = np.concatenate(r_list)
    else:
        centers = np.empty((0, 2), np.float32)
        radii = np.empty((0,), np.float32)

    return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range
```

Also add traitor injection:

```python
def __init__(self, ..., traitor_indices=None, traitor_behavior=None, **kwargs):
    # ... existing init ...
    self.traitor_indices = traitor_indices or []  # Which drones are traitors
    self.traitor_behavior = traitor_behavior or "false_obstacles"  # "false_obstacles", "silence", "ramming"
```

---

### Step 2: Traitor Obstacle Broadcasting Logic

**In `_fused_lidar_with_trust`, modify neighbor contribution:**

```python
for j in range(self.n_drones):
    # ... existing checks ...
    
    # Traitor behavior: false obstacles
    if j in self.traitor_indices and self.traitor_behavior == "false_obstacles":
        # Broadcast fake obstacles (random positions, far from real obstacles)
        fake_centers = np.random.uniform(0, self.WIDTH, size=(5, 2)).astype(np.float32)
        fake_radii = np.full(5, 0.5, dtype=np.float32)
        c_list.append(fake_centers)
        r_list.append(fake_radii)
        continue
    
    # Traitor behavior: silence
    if j in self.traitor_indices and self.traitor_behavior == "silence":
        continue  # Don't contribute anything
    
    # ... normal neighbor contribution ...
```

---

### Step 3: T-Cell Trust Module (In the Actor)

**New PyTorch module in `train_slot_fusion.py`:**

```python
class TCellTrustGate(nn.Module):
    """Learns per-neighbor trust weights [w₀, ..., w₉]."""
    
    def __init__(self, n_drones=10, hidden_dim=64):
        super().__init__()
        self.n_drones = n_drones
        # Input: [ego_blind_flag (1) + neighbor_relative_pos (9*2) + neighbor_comm_activity (9)]
        input_dim = 1 + 9*2 + 9  # = 28
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_drones)
        )
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, ego_state):
        """
        ego_state: [ego_blind, neighbor_rel_pos (18D), neighbor_comm_active (9D)]
        Output: trust_weights [w₀, ..., w₉] ∈ [0,1]
        """
        logits = self.net(ego_state)
        return self.sigmoid(logits)  # w ∈ [0, 1]
```

**Integrate into actor:**

```python
class MAPPO_Extractor_WithTrust(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # ... existing actor/critic networks ...
        self.trust_gate = TCellTrustGate(n_drones=10)
    
    def forward(self, f):
        # f is 650-d: [local(130), global(520)]
        # Extract ego state for trust gating
        ego_state = self._prepare_trust_input(f[:, :130])  # 28-d
        trust_weights = self.trust_gate(ego_state)  # [10,]
        
        # Pass trust weights to env (via callback or observation augmentation)
        # ... implementation detail ...
        
        return self.policy_net(f[:, :LOCAL]), self.value_net(f[:, LOCAL:])
```

---

### Step 4: Training with Traitors Active

**New script: `train_slot_fusion_with_trust.py`**

Similar to `train_slot_fusion.py`, but:
- Load trained ON model from Phase 3: `models/raster_slot_fusion_ON_stage2_final.zip`
- Add traitor drones (parameterized: num_traitors, traitor_behavior)
- Train T-Cell gate to learn trust weights
- Use lower LR (1e-5) to preserve Phase 3 weights, adapt trust gate

**Curriculum (1M steps total):**
```
Stage 0 (500k): 1 traitor (false obstacles)
Stage 1 (500k): 2 traitors (1 false, 1 silence)
```

---

### Step 5: Evaluation Against Traitors

**New eval script: `eval_trust_defense.py`**

Test scenarios:

```python
SCENARIOS = [
    ("baseline", 0, None),              # 0 traitors (sanity check)
    ("1_false", 1, "false_obstacles"),  # 1 traitor broadcasting fake obstacles
    ("2_silent", 2, "silence"),         # 2 traitors broadcasting nothing
    ("1f_1s", 2, "mixed"),              # 1 false + 1 silent
    ("ramming", 1, "ramming"),          # 1 traitor ramming
]
```

For each scenario, measure:
- **Drone-level success rate** (primary metric)
- **Trust weights learned** (did T-Cell identify traitors?)
- **per-neighbor contribution** (which drones are down-weighted?)

---

## 4. Full Training & Eval Commands

### Train T-Cell Trust Gate (1M steps)

```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"

# Load Phase 3 ON model, add traitors, train trust gate
& $py Phase_CD\Collab_Perception\train_slot_fusion_with_trust.py on 0
& $py Phase_CD\Collab_Perception\train_slot_fusion_with_trust.py on 1
```

Saves: `models/raster_slot_fusion_trust_ON_stage{0|1}_final.zip`

### Evaluate Against Traitors (5 scenarios × 200 maps each)

```powershell
# Baseline (0 traitors, sanity check)
& $py Phase_CD\Collab_Perception\eval_trust_defense.py models\raster_slot_fusion_trust_ON_stage1_final.zip baseline 200

# 1 traitor (false obstacles)
& $py Phase_CD\Collab_Perception\eval_trust_defense.py models\raster_slot_fusion_trust_ON_stage1_final.zip 1_false 200

# 2 traitors (silence)
& $py Phase_CD\Collab_Perception\eval_trust_defense.py models\raster_slot_fusion_trust_ON_stage1_final.zip 2_silent 200

# 1 false + 1 silent
& $py Phase_CD\Collab_Perception\eval_trust_defense.py models\raster_slot_fusion_trust_ON_stage1_final.zip 1f_1s 200

# 1 traitor (ramming)
& $py Phase_CD\Collab_Perception\eval_trust_defense.py models\raster_slot_fusion_trust_ON_stage1_final.zip ramming 200
```

---

## 5. Success Criteria (Decision Gates)

| Scenario | Target | Pass |
|----------|--------|------|
| Baseline (0 traitors) | ≥92% | Sanity check: trust module doesn't hurt |
| 1 false obstacle | ≥75% | T-Cell learns to ignore phantom obstacles |
| 2 silent traitors | ≥70% | Can navigate with partial communication |
| 1f + 1s mixed | ≥68% | Handles multiple traitor types |
| 1 ramming | ≥60% | Can evade + navigate (hardest) |

**Final gate:** Baseline ≥92% AND all scenarios ≥60% → **Trust-aware defense is validated.**

---

## 6. Expected Results & Narrative

**Phase 3 → Phase 4 Progression:**

```
Phase 3: 
  ON (no traitors):      94.12% drone success
  Communication proves essential (+41 pp)

Phase 4:
  ON (1 traitor):        ~80% drone success
  ON (2 traitors):       ~70% drone success
  
  Trust weights analysis:
    Honest neighbors:     w ≈ 0.9–1.0 (trusted)
    Traitor neighbors:    w ≈ 0.0–0.2 (down-weighted)
  
  Conclusion: Swarm learns to identify and ignore Byzantine neighbors.
```

**Paper Narrative:**
```
1. Communication is load-bearing (Phase 3: +41 pp)
2. But opens a vulnerability to adversarial neighbors
3. T-Cell trust gate defends by learning per-neighbor weights
4. Even with k traitors, swarm maintains >60% success
5. TA-MAPPO: Trust-Aware MARL for Byzantine-resilient swarms
```

---

## 7. Timeline

- **Step 1–2 (Code):** ~4 hours (add T-Cell to env + actor)
- **Step 3 (Training):** ~6 hours (1M steps with traitors)
- **Step 4 (Eval):** ~5 hours (5 scenarios × 200 maps)
- **Total:** ~15 hours → **Phase 4 complete**

---

## 8. Deliverables

Final Phase 4 package:
- ✅ `raster_slot_fusion_trust_ON_stage1_final.zip` (trained trust model)
- ✅ `eval_trust_defense_results.csv` (results across 5 scenarios)
- ✅ Per-neighbor trust weight analysis (which drones are trusted?)
- ✅ Paper figure: drone success vs. num_traitors (with CI)

---

## 9. Implementation Order

1. **Today:** Implement Steps 1–2 (T-Cell + traitor logic in env)
2. **Tomorrow (morning):** Implement Steps 3–4 (trust module in actor, training script)
3. **Tomorrow (afternoon):** Run training (1M, 6 hours)
4. **Tomorrow (evening):** Run evals (5 scenarios, 5 hours)
5. **Write-up:** Document results, finalize paper narrative

