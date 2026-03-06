# Step A Checklist: 10 Honest Drones, 0 Traitors, 0 Obstacles

- [x] Create isolated `swarm_env_step_A.py` file.
- [x] Implement 10 Honest Drones in a 20x20 field with no static obstacles.
- [/] Verify rendering and physics step mechanics via random actions.
  - [x] Basic PyGame loop functioning.
  - [x] Fix boundaries (prevent drones from flying off-screen).
- [x] Implement $R_{goal}$ (distance delta to goal).
- [x] Implement $R_{safe}$ (large penalty for hitting walls or other drones).
- [x] Implement $R_{group}$ (small bonus for staying together).
- [x] Write `train_step_A.py` script using PPO Multi-Agent setup.
- [x] Train for 2M timesteps and save the base model weights.
