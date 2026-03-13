# Trick Challenge: The Social Distancing Evaluation Bug

## The Problem
After fixing the JSON spawning logic so the drones were legally spaced `0.26m` apart, `edge_case_1.json` and `edge_case_4.json` *still* registered as a **100% Crash Failure** in the terminal, even though visually we could see the drones were not touching.

## Diagnosing the Issue
To figure out why the test suite was declaring a crash, we wrote a temporary `debug_edge_cases.py` script that intercepted the neural network immediately after Frame 1. 

The debug script proved that the physical distance between the drones was exactly `0.26m`—they had not crashed. 

So why was `test_suite_step_A.py` recording a crash? We looked at how the evaluation script tallied its metrics:
```python
# The old evaluation logic
if rewards[agent] <= -50.0:  
    episode_collision += 1
```
The test suite assumed that any drone finishing an episode with a reward score of `-50.0` or worse *must* have crashed, because crashing into a wall is `-100` and crashing into a drone is `-50`.

However, during Phase A training, we implemented the **Social Distancing Penalty**. To teach the drones to spread out, they are penalized exponentially the closer they get to each other. Because Edge Cases 1 and 4 deliberately spawn the drones right on the bleeding edge of each other's hitboxes, the environment slapped every single drone with a massive `-60` or `-70` Social Distancing penalty on Frame 1.

The test suite saw the `-70` reward, assumed it was a physical crash, manually marked the drones as dead, and ruined the evaluation.

## The Solution
Instead of having the test suite "guess" what happened based on the final float math of the reward signal, we gave the fundamental `swarm_env_step_A.py` physics engine the ability to explicitly broadcast the true cause of death.

We injected actual semantic tags into the Gym `infos` dictionary:
```python
# Inside the environment physics step()
if hit_drone:
    rewards[agent] = -50.0
    self.terminations[agent] = True
    self.infos[agent] = {"cause": "collision"}
```

We then rewrote the test suite to completely ignore the math, and simply check the tag:
```python
# The updated evaluation logic
cause = infos[agent].get("cause")
if cause == "collision":
    episode_collision += 1
```

Once the test suite was looking at the truth rather than guessing from the score, both edge cases functioned perfectly and evaluated to 100% Success.
