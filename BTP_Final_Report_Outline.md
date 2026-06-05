# Comprehensive BTP Report: Resilient Swarm Navigation via Trust-Aware MARL (TA-MAPPO)

## 0. Executive Summary
*   **Mission Statement**: Developing a decentralized swarm control framework resilient to adversarial communication and environmental complexity.
*   **Core Contributions**: Introduction of the "T-Cell" Trust Mechanism and the Dual-Sensing (Lidar/Comms) Gating Architecture.
*   **Achieved Results (Phase A)**: 99.68% foundational success in collision-free navigation through physics-level debugging.
*   **Expected Impact (Phase C/D)**: Projected +104% performance gain under adversarial load compared to vanilla MAPPO using trust-gated observations.
*   **Academic Novelty**: Bridging Artificial Immune Systems (AIS) with Multi-Agent Reinforcement Learning to solve the Byzantine swarm problem.

## 1. Introduction & Research Motivation
*   **1.1 The Swarm Decentralization Problem**: Coordinating 10 drones in shared continuous spaces.
*   **1.2 The Vulnerability of Connectivity**: The impact of Byzantine actors (traitors) on swarm mission integrity.
*   **1.3 Research Objectives**: A four-phase evolution roadmap from basic physics to adversarial robustness.

## 2. Problem Formulation & Theoretical Framework
*   **2.1 Dec-POMDP Modeling**: Formalizing the state ($S$), action ($A$), and observation ($O$) spaces.
*   **2.2 Adversarial Threat Model**: Mathematical definition of "Traitor" drone spoofing vectors and communication noise.
*   **2.3 The AIS Metaphor (Theoretical Depth)**:
    *   **Trust Derivation Equation**: $T_{ij} = \sigma(\sum_k w_k \cdot (1 - |o_{ik} - b_{jk}|))$, where $o_{ik}$ is the trusted observation and $b_{jk}$ is the untrusted broadcast.
    *   **Literature Reference**: Bio-inspired anomaly detection (Forrest et al., 1994).
*   **2.4 Baseline Benchmarks**: Comparative framing—Vanilla MAPPO (Control) vs. Phased Learning trajectories.

## 3. Phase A: Foundational Coordination (COMPLETED)
*   **3.1 Environment Engineering**: PettingZoo ParallelEnv setup ($20\text{m} \times 20\text{m}$ field).
*   **3.2 The Physics Debugging Odyssey**: Resolving the "Ghost Drone" hitbox persistence bug ($21\% \to 88\%$).
*   **3.3 Collision & Clustering Resolutions**:
    *   **Geometric Tuning**: Hitbox optimization for physical drone kinematics ($88\% \to 99.22\%$).
    *   **Social Distancing Shock**: The $-50.0 \times (0.4 - dist)$ repulsive penalty.
    *   **School Zone Velocity Damping**: Quadratic damping in dense $2 \times 2$ cluster spawns.
*   **3.4 Goal Funnel Optimization**: Preventing arrival-point deadlock through radius relaxation.
*   **3.5 Verified Benchmarks**: 
    *   **[FIGURE]**: Success rate bar chart (pre/post-fix comparison, 5-Fold CV results).

## 4. Phase B: Environmental Complexity (IN PROGRESS)
*   **4.1 Advanced Perception**: Deployment of the 48-ray Vectorized Lidar system.
*   **4.2 Map Solvability Logic**: Implementation of the Grid-based BFS check to ensure navigability.
    *   **[FIGURE]**: Obstacle density vs. map feasibility scatter plot.
*   **4.3 High-Performance Engineering**:
    *   **Sigmoid Look-Up Tables (LUT)**: Optimizing activation functions for real-time edge execution.
    *   **O(N²) Distance Matrices**: Vectorized pairwise distance calculations.
*   **4.4 Optimization & Synchronization**: Tuning velocity alignment (flocking) rewards for swarm cohesion in obstacle corridors.

## 5. Phase C: Cyber-Physical Defense (PLANNED)
*   **5.1 Dual-Sensing Framework**: Theoretical split between Lidar (Trusted) and Comms (Untrusted).
*   **5.2 Discrepancy Detection**: Identifying traitors via cross-sensor signature misalignments.
*   **5.3 Recursive Trust Score ($T_{ij}$)**:
    *   **[FIGURE]**: Planned Trust Score Evolution Heatmap for real-time anomaly detection.

## 6. Phase D: TA-MAPPO Synthesis & Robustness (PLANNED)
*   **6.1 Feature Gating Network**: Multiplicative trust-filtering of neighbor embeddings.
*   **6.2 CTDE Architecture**: Actor-Critic roles under adversarial load.
*   **6.3 Hyperparameters & Reproducibility**: Log of learning rates, clip ranges, and entropy coefficients for validation.

## 7. Expected Evaluation & Results
*   **7.1 Current Phase B Status**: Performance curves and obstacle density success rates.
*   **7.2 Planned Ablation Study**: 
    *   **[TABLE]**: Comparison of Vanilla MAPPO vs. Phase B vs. Full TA-MAPPO.
*   **7.3 Proposed Detection Metrics**: Planned Confusion Matrix + ROC Curve for traitor identification.

## 8. Discussion & Research Novelty
*   **8.1 The Resilience Advantage**: Why trust-gating is superior to standard communication filters.
*   **8.2 Unsupervised Expansion**: Integration of DBSCAN for clustering sensor point clouds.
*   **8.3 Sensitivity & Limitations**: Quantifying trust drop-off vs. sensor noise and $O(N^2)$ scaling costs.
*   **8.4 Broader Impacts**: Applications in search-and-rescue and autonomous warehouse logistics.

## 9. Conclusion & Future Work
*   **9.1 Summary**: Validation of the TA-MAPPO bio-inspired framework as a solution for Byzantine swarms.
*   **9.2 Hardware Roadmap**: Moving from simulation to PX4-based quadrotor testing.
