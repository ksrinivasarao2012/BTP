# Trick Challenge: Cluster Panic (The Untangling Problem)

## The Problem
After relaxing the goal radius, the **1K Random Spawns** test reached an incredible **99.68% Success Rate**. 

However, when we subjected the model to the **1K Clustered Stress Test** (where all 10 drones spawn shoulder-to-shoulder inside a strict `2x2` box), the success rate plummeted back down to **~89.4%**. 

## Diagnosing the Issue
By visually watching PyGame renderer, we observed **Cluster Panic**.

Because the goal was far away, the drones immediately attempted to accelerate to max speed (`v=1.0`) to get the $R_{goal}$ distance reward. But because they spawned inside a tight 2x2 cluster, accelerating instantly caused them to slam into their neighbors before they had time to spread out into a safe formation. The neural network had no concept of "waiting its turn" or "slowing down in traffic."

## The Solution
We solved this by injecting two completely new, dynamic rules into the physical $R_{safe}$ reward function:

### 1. The "School Zone" Speed Limit
```python
if dist < 0.55:
    speed = np.linalg.norm(self.velocities[agent])
    if speed > 0.35: # 35% of max speed
        rewards[agent] -= 10.0 * (speed**2) 
```
If a drone detects neighbors within `0.55m`, and it attempts to fly faster than `35%` of its maximum speed, it is hit with a severe quadratic penalty. This mathematically forced the AI to learn that it must move *slowly* when tangled in a cluster, preventing the instant acceleration crashes.

### 2. The Social Distancing Shock
```python
if dist < 0.4:
    rewards[agent] -= 50.0 * (0.4 - dist)
```
Since physical crashes happen at `0.25m` (and end the simulation), we created an invisible "warning ring" at `0.4m`. If a drone crosses into this warning space, it receives a harsh repulsive penalty. This taught the network the concept of "personal space," forcing it to proactively steer away from neighbors before a fatal physical collision could even occur.
