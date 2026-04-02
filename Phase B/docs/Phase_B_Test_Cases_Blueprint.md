# Phase B Test Suite Blueprint: Basic & Edge Cases

To ensure the Phase B Neural Network (PPO model) is robust and truly understands the physics of continuous obstacle avoidance (rather than just memorizing paths), we must subject it to a rigorous, hand-crafted suite of geometric challenges.

This document outlines the **8 defining test cases** (4 Basic, 4 Edge) required to mathematically validate the swarm's intelligence.

---

## 🟢 Part 1: Basic Test Cases (Foundational Mechanics)
These tests ensure the model has learned the absolute minimum required physics linking its LiDAR sensors to its motor thrust vectors.

### 1. The Single Pillar
- **Description:** A single, large obstacle ($R=1.5m$) generated exactly halfway dead-center between the Swarm Spawn and the Goal. 
- **The Reason:** This is the "Hello World" of obstacle avoidance. It tests whether a drone's neural network has learned to prioritize sideways lateral thrust over greedy forward thrust. If the model fails this, it has not learned to read its LiDAR at all.

### 2. The Asteroid Field (Uniform Scatter)
- **Description:** $15$ medium-sized obstacles ($R=1.0m$) scattered uniformly across the map ($15\%$ total area density). 
- **The Reason:** Tests general, chaotic pathfinding. The drones must dynamically weave through randomized columns without losing track of the global goal vector. It guarantees the model did not just memorize a "go left" policy.

### 3. The Narrow Corridor
- **Description:** Two massive obstacles form a straight, narrow tunnel (exactly $0.8m$ wide) leading directly to the goal.
- **The Reason:** A test of **Kinematic Precision**. The $0.8m$ gap is wide enough for a drone ($0.5m$ physical footprint) to pass, but the drone must fly directly down the center. If their thrust vectors jitter or oscillate, they will clip the walls. It also forces the swarm to line up in single-file formation, proving the "School Zone" penalties from Phase A still function under external pressure.

### 4. The Wall Hugger
- **Description:** Obstacles placed exactly on the outer bounding walls of the $20 \times 20$ environment.
- **The Reason:** Tests sensor disambiguation. The LiDAR returns similar distance floats whether it hits the map's boundary wall or a static circular obstacle. The network must prove it can distinguish and slide smoothly along combinations of boundaries without snagging in corners.

---

## 🔴 Part 2: Extreme Edge Cases (Pathfinding & Traps)
These tests push the simulation to the mathematical limits of the $0.5m$–$1.5m$ geometric bounds defined in the Theoretical Justifications document. They are designed to break naive "greedy" AI.

### 5. The Great Concave Trap (The $U$-Shape)
- **Description:** A massive, solid "C" or "U" shaped ring of obstacles placed exactly between the swarm and the goal, with the opening facing the swarm.
- **The Reason / The Danger:** This targets **Local Minima**. A basic "greedy" AI will fly straight into the pocket of the $U$-shape because that is the shortest mathematical path to the goal. Once inside, it will get stuck, refusing to fly backwards (away from the goal) to escape the trap. A mature PPO network must prove it can sacrifice short-term distance rewards to navigate around the massive blockade.

### 6. The Great Wall (The Flank Test)
- **Description:** A continuous, unbroken line of obstacles spanning entirely across the $Y$-axis, with only one tiny $0.6m$ gap hidden exclusively at the extreme top or bottom edge of the map.
- **The Reason:** This tests long-term, non-linear path planning. The swarm spawns on the left, the goal is on the right. Rather than flying straight, they must fly $10m$ "up" or "down" alongside the wall to find the single topological choke-point. 

### 7. The Micro-Minefield (LiDAR Ray-Sweep Validation)
- **Description:** **50+ Tiny Obstacles** ($R=0.2m$, dense surface area) clustered throughout the map.
- **The Reason:** This explicitly tests the physics engine's **Ray-Sweeping** minimum-bound fix. Standard 16-ray LiDAR will fail to see $0.2m$ pillars at a distance. If the Ray-Sweeping algorithm works flawlessly, the AI will perceive a chaotic but physically accurate map and twitch-dodge the pillars. If the engine math fails, the PyGame renderer will show drones inexplicably crashing into "invisible" pillars.

### 8. The Claustrophobic Prison
- **Description:** All 10 drones spawn grouped tightly in the bottom-left corner. Immediately surrounding them is a tight arc of $1.5m$ boulders, leaving only a single $0.6m$ exit path.
- **The Reason:** This combines Phase A's **Cluster Panic** with Phase B's **Static Geometry**. The drones cannot just burst outward; they must dynamically untangle themselves from each other *while* being pressed against hard static walls, and slowly funnel out the single exit door in an organized, orderly line. If they panic, they will instantly trigger $-100$ collision penalties and fail.
