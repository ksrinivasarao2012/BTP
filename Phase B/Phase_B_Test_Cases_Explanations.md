# Phase B Test Suite: Detailed Explanations

To ensure the Phase B Neural Network (PPO model) is robust and truly understands the physics of continuous obstacle avoidance, we have designed an 8-part testing suite. This suite specifically isolates unique geometric traps to prove the AI hasn't simply memorized a "greedy" forward-thrust policy.

Below is the detailed mathematical and geometric reasoning for each generated JSON test case.

---

## 🟢 Part 1: Basic Test Cases (Foundational Kinematics)

### 1. The Single Pillar (`basic_1_single_pillar.json`)
- **Map Layout:** A single massive $1.5m$ radius obstacle is placed exactly at the halfway coordinate between the spawning swarm and the goal coordinate.
- **The Rationale:** This evaluates the base condition of LiDAR-to-Motor coupling. If a drone cannot detect a massive object directly in front of it and slide 1 meter laterally to avoid it, the LiDAR sensors are fundamentally unplugged from the Actor network. This is the ultimate "sanity check" for the neural network.

### 2. The Asteroid Field (`basic_2_asteroid_field.json`)
- **Map Layout:** $15$ medium-sized obstacles ($R=1.0m$) scattered uniformly across the entire map ($15\%$ total area density). 
- **The Rationale:** This evaluates macro-level pathfinding. Drones should not all take the exact same route. As they spread out, the "Asteroid Field" guarantees they must constantly dynamically adjust their thrust vectors (weaving) while maintaining the global heading towards the $R_{goal}$ reward.

### 3. The Narrow Corridor (`basic_3_narrow_corridor.json`)
- **Map Layout:** Two massive $10m$-long rectangular obstacles (or a tight line of circular pillars) placed parallel to each other, forming a straight tunnel exactly $0.8m$ wide leading directly to the goal.
- **The Rationale:** This evaluates **Kinematic Precision**. The $0.8m$ gap is wide enough for a drone ($0.5m$ physical footprint) to pass safely, but only if they fly strictly straight. If their thrust vectors jitter, oscillate, or overshoot, they will clip the walls. Secondly, it evaluates **Formation Flying**. Since $10$ drones cannot fly shoulder-to-shoulder through a $0.8m$ gap, they must organically line up in single-file formation, proving the "School Zone" penalties from Phase A correctly force them to yield to traffic.

### 4. The Wall Hugger (`basic_4_wall_hugger.json`)
- **Map Layout:** Obstacles placed perfectly flush against the outer bounding walls of the $20 \times 20$ environment. The goal is placed deep inside a tight corner.
- **The Rationale:** This evaluates sensor disambiguation. A LiDAR ray returns a normalized float value `0.0` to `1.0`. The network must prove it can distinguish the geometry of the flat rectangular bounding box array from the static circular obstacles placed against it, allowing it to slide smoothly down the wall without snagging on the embedded circles.

---

## 🔴 Part 2: Extreme Edge Cases (Traps & Limitations)

### 5. The Great Concave Trap (`edge_1_u_shape_trap.json`)
- **Map Layout:** A massive, solid "C" or "U" shaped ring of obstacles placed directly between the swarm and the goal, with the open mouth facing the swarm.
- **The Rationale:** This evaluates susceptibility to **Local Minima**. A primitive AI uses a "greedy" policy—meaning it always takes an action that strictly decreases its absolute distance to the goal. If it does this here, it will fly straight into the pocket of the $U$-trap. Once inside, the only way out is to fly *backwards* (temporarily increasing its distance from the goal). A mature PPO network must prove its Critic Network understands long-term discounting, purposefully sacrificing short-term reward to fly around the massive blockade.

### 6. The Great Wall (`edge_2_flank_wall.json`)
- **Map Layout:** A continuous, unbroken line of obstacles spanning entirely across the $Y$-axis. The only way through is one tiny $0.6m$ gap hidden exclusively at the extreme top edge ($Y=19.5$) of the map.
- **The Rationale:** This evaluates extreme horizontal path planning. The swarm spawns on the left, the goal is on the right. Rather than flying straight, they must learn to fly $10m$ vertically "up" alongside the wall to find the single topological choke-point before flying horizontally again. 

### 7. The Micro-Minefield (`edge_3_micro_minefield.json`)
- **Map Layout:** **50 Tiny Obstacles** ($R=0.2m$) clustered globally throughout the map like a checkerboard.
- **The Rationale:** This explicitly evaluates the physics engine's **Ray-Sweeping** mathematical fix (outlined in the Phase B Justification document). Without Ray-Sweeping, a standard 16-ray LiDAR will fail to see $0.2m$ pillars at a distance, and the drones will crash into "invisible" objects. If the engine math is programmed flawlessly, the AI will perceive a chaotic but physically accurate map and "twitch-dodge" the pillars successfully.

### 8. The Claustrophobic Prison (`edge_4_claustrophobic_prison.json`)
- **Map Layout:** All 10 drones spawn directly on top of each other in the bottom-left corner. Immediately surrounding them 1 meter away is a tight arc of $1.5m$ boulders, leaving only a single $0.6m$ exit path.
- **The Rationale:** This is the ultimate crucible. It merges Phase A's "Cluster Panic" untangling penalty with Phase B's static geometry. The drones cannot burst outward to establish their 0.4m Social Distancing buffer because doing so will crash them directly into the boulder walls. They must dynamically untangle themselves *internally* while being compressed against hard static walls, and slowly funnel out the single exit door in an organized line. If they panic, they will instantly trigger $-100$ collision penalties and fail.
