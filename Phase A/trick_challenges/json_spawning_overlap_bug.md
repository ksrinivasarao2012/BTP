# Trick Challenge: The JSON Spawning Overlap Bug

## The Problem
When visualizing the basic edge cases for the first time, `edge_case_1.json` (Instant Win) and `edge_case_4.json` (Extreme Claustrophobia) both instantly failed with a **100% Collision Rate** on Frame 1, causing the PyGame window to immediately close.

## Diagnosing the Issue
The purpose of these edge cases was to pack all 10 drones into a very tight space. 
To generate the JSON file, the original code used a simple loop adding a tiny random offset to a central point:
```python
"start_positions": [[cx + np.random.uniform(-0.1, 0.1), cy + np.random.uniform(-0.1, 0.1)] for _ in range(10)]
```
This logic restricted all 10 drones to a maximum physical box size of **0.20 meters**.

However, the physical drone-on-drone crash threshold established in `swarm_env_step_A.py` is **0.25 meters**. 

Because 10 drones were mathematically forced into a space smaller than the crash threshold of a single drone, every single drone spawned intrinsically inside the collision hitbox of its neighbors. On the very first frame of the simulation, the engine evaluated distances, registered 10 fatal crashes, and killed the entire swarm instantly.

## The Solution
We updated the `generate_basic_test_cases.py` script to use a strict, mathematically proven circular-packing algorithm. 

Using a `while` loop, the generator now checks the hypotenuse distance between a newly proposed XY coordinate and all previously placed coordinates. If the distance is `< 0.26` (just above the 0.25 crash threshold), it throws the coordinate away and rolls a new random point. It is mathematically impossible for the JSON generator to output a file with overlapping drones now.
