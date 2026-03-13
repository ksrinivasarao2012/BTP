# Phase B: Theoretical Justifications

This document provides rigorous mathematical and theoretical justification for hyperparameter decisions regarding LiDAR, obstacle scaling, and pathfinding in Phase B of the TA-MAPPO environment.

---

## 1. Dynamic Obstacle Density vs Hardcoded Counts

In Phase B, the environment handles static geometry via **Percentage Density Coverage** rather than hardcoded obstacle counts (e.g., "spawn 20 obstacles"). A map set to 25% Density might spawn 5 massive boulders, or 45 small pillars. This requires two specific mathematical protocols to prevent environment breakage:

### A. The Minimum Bound Solution: LiDAR Ray-Sweeping
If a tiny obstacle (e.g., $R=0.2m$) is spawned, it is geographically capable of slipping "between" two of the drone's 16 discrete LiDAR rays, rendering it invisible.
**The Fix:** Rather than banning small obstacles, the physics engine will implement **Ray-Sweeping**. During the $\Delta t = 0.1s$ physics step, the 16 rays will sweep laterally to cover the gaps, mathematically testing line-segment collisions against the obstacle radii. This effectively transforms discrete 1D ray-casts into 2D continuous detection cones, ensuring no obstacle can evade detection regardless of its miniature size.

### B. The Maximum Bound Solution: Navigational Choke-Point Verification
If the generator spawns several massive obstacles (e.g., $R=3.5m$), their raw surface area can accidentally link together and wall off the map from edge to edge. 
**The Fix:** Bounding by pure numerical counts cannot prevent this. Instead, the environment's `reset()` function will employ a **Minimum Clearance Verifier**. After spawning the obstacles, it will compute a pairwise distance matrix between all obstacles and the walls. It verifies that a contiguous path of at least $0.6m$ width exists from the Spawning Zone to the Goal. If the random seed generates an unsolvable, physically walled-off labyrinth, the seed is rejected and the map is redrawn. This guarantees Markov Decision Process validity without artificially banning large structures.
