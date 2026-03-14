# Phase B: Industrial Engineering Standards & Performance Roadmap

This document provides the technical specifications and diagnostic reasoning used to achieve **"Industrial Grade"** performance (95%+ Success Rate) in dense multi-agent obstacle environments.

---

## 🔍 1. Diagnostic Analysis: The 77% Performance Ceiling

Exhaustive benchmarking revealed that simple reward tuning cannot break the 90% barrier due to four structural "Shadow Killers":

### A. Kinematic Mismatch (Braking vs. Detection)
*   **The Math**: At 2.0 m/s, with 0.5 m/s² braking, a drone requires **0.4m** to stop.
*   **The Trap**: If LiDAR detects a wall at 0.3m, collision is physically inevitable. Drones learn to "fear" obstacles by crawling at 0.5 m/s to stay safe, leading to 100% timeouts in dense maps.
*   **Industrial Standard**: Increase Braking/Acceleration constant to **10.0** to allow "Snap Reactions" and high-speed confidence.

### B. Signal Sparsity (The Sampling Gap)
*   **The Math**: 16 rays = $22.5^\circ$ angular spacing. At 3m, the gap between rays is **>1.1m**.
*   **The Trap**: A 0.2m pillar can fit easily between rays. Drones "clip" obstacles because they literally cannot see them if they are perfectly centered between rays.
*   **Industrial Standard**: **Volumetric Sector-Scanning**. Instead of point-rays, each sensor channel samples the *minimum* distance within a $22.5^\circ$ Sector (Field of View).
*   **IEEE Justification**: This represents a "Multi-Channel FOV Integrator," similar to how real-world Ultrasonic or Wide-Beam Infrared arrays operate. It ensures **zero blind spots** by providing 100% spatial coverage of the $360^\circ$ plane while maintaining a low-dimensional 16-input vector.

### C. Neural Under-Capacity
*   **Specification**: Default SB3 architecture is `[64, 64]`.
*   **The Trap**: Mapping 67 inputs (LiDAR + 9 Neighbors + Ego) into 10-drone coordination is too complex for 4,000 parameters.
*   **Industrial Standard**: Scale to **`[256, 256, 128]`**. This provides the "cognitive headroom" needed for precise pathfinding in clustered environments.

### D. Toxic Reward Overlap (COM Expansion)
*   **The Trap**: "COM Expansion" (pushing drones away from the group center) works in open fields but is **lethal in corridors.** It pushes drones into the side-walls as they try to "expand" inside a narrow passage.
*   **Industrial Standard**: Disable COM Expansion in density stages > 10%. Replace with **Directional Flow** rewards.

---

## 👥 2. Social Interaction Model

### A. Reactive Repulsion (The "Hard" Buffer)
*   **Model**: $R_{rep} = -(d_{safe} - d_{ij}) \cdot 50.0$ for $d_{ij} < 0.21m$.
*   **Logic**: Acts as a virtual spring. We use a tight $1.2x$ safety radius multiplier to allow single-file formations.

### B. The "School Zone" (Kinetic Control)
*   **Logic**: Forces a 35% speed limit when drones are within 0.55m of neighbors.
*   *Benefit*: Prevents high-speed "shoving matches" in bottlenecks.

---

## 🏗️ 3. "Bravery & Flow" Curriculum

| Phase | Density | Timesteps | Safety Radius | Policy Arch |
| :--- | :--- | :--- | :--- | :--- |
| **B1: Sparse** | 5% | 2,000,000 | 0.18m | [256, 256, 128] |
| **B2: Moderate**| 10% | 2,000,000 | 0.18m | [256, 256, 128] |
| **B3: Dense** | 20% | 2,000,000 | 0.18m | [256, 256, 128] |
| **B4: Hyper-Dense**| 30% | 2,000,000 | 0.18m | [256, 256, 128] |

**Success Requirement**:
- Individual Success: **> 95%**
- Episode Success (Any): **> 99%**
- Collision Rate: **< 3%**
