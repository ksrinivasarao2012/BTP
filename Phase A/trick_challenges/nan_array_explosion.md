# Trick Challenge: The NaN Array Explosion

## The Problem
During the very early training iterations of the PPO model in Phase A, the neural network would occasionally catastrophic fail in the middle of a 2,000,000 timestep curriculum.

The training logs in your terminal would suddenly start outputting `NaN` (Not a Number) for the Policy Loss, Value Loss, and Entropy. Once the neural network weights became `NaN`, the model was permanently corrupted and the entire training session had to be thrown out and restarted from scratch.

## Diagnosing the Issue
`NaN` explosions in Reinforcement Learning usually mean one of two things:
1. The Learning Rate is too high, causing the gradients to explode to infinity.
2. A mathematical `Divide by Zero` error occurred in the environment, injecting `Infinity` into the reward signal, which the neural network then copied into its weights.

We analyzed the Reward Function ($R_{goal}$) we implemented in `swarm_env_step_A.py`. To incentivize the drones to fly towards the goal, we were giving them a continuously scaling reward based on their distance inverse:

```python
# The original, buggy math
reward = 10.0 / dist_goal
```

When a drone spawned on the map, `dist_goal` might be $15.0$, meaning it received a small positive reward. As it got closer (e.g., $1.0m$), the reward increased to $10.0$. 

However, because we are working in continuous floating-point space, it was mathematically possible for a drone to physically cross the exact center-point coordinate of the goal ($X=10.000, Y=10.000$) on a single frame. 

When a drone's center perfectly matched the goal's center, `dist_goal` mathematically became exactly `0.0`. 

When Python executed `10.0 / 0.0`, it returned `Infinity`. This infinite reward was fed back into the Stable-Baselines3 PPO buffer, immediately causing the gradient tensors to explode into `NaN` and destroying the model.

## The Solution
When dealing with algorithms that divide by a dynamic distance, you must *always* add a tiny `epsilon` constant to the denominator to mathematically prevent the possibility of a clean zero division.

```python
# The corrected math
reward = 10.0 / (dist_goal + 1e-6)
```

By explicitly adding `1e-6` ($0.000001$), the closest the denominator can ever mathematically get to zero is `0.000001`. The resulting reward caps at a massive but safe integer `10,000,000` rather than `Infinity`, completely preventing the Neural Network from dissolving into `NaN`.
