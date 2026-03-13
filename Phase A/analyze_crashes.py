import numpy as np
from stable_baselines3 import PPO
from swarm_env_step_A import SwarmLidarEnv_StepA

def analyze_crashes():
    env = SwarmLidarEnv_StepA(render_mode=None)
    model = PPO.load("./models/step_A_foundation_model")
    
    total_episodes = 500
    crash_steps = []
    goal_distances = []
    
    for _ in range(total_episodes):
        obs, _ = env.reset()
        
        # force a clustered spawn
        env.velocities = np.zeros((env.n_drones, 2), dtype=np.float32)
        cx = np.random.uniform(3.0, env.WIDTH - 3.0)
        cy = np.random.uniform(3.0, env.HEIGHT - 3.0)
        half = 1.0  # 2x2 box
        min_dist = 0.3
        placed = []
        for i in range(env.n_drones):
            for _ in range(500):
                x = np.random.uniform(cx - half, cx + half)
                y = np.random.uniform(cy - half, cy + half)
                if all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed):
                    placed.append([x, y])
                    break
            else:
                x = np.random.uniform(cx - half - 1, cx + half + 1)
                y = np.random.uniform(cy - half - 1, cy + half + 1)
                placed.append([x, y])
            env.positions[i] = [placed[-1][0], placed[-1][1]]
        
        obs = {agent: env._observe(agent) for agent in env.agents}
        
        done = False
        step = 0
        while env.agents and step < env.max_steps:
            actions = {}
            for agent in env.agents:
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
            
            obs, rewards, term, trunc, info = env.step(actions)
            
            # Check for crashes
            for agent in actions.keys():
                if term[agent] and rewards[agent] <= -50.0:
                    idx = env.agent_name_mapping[agent]
                    crash_steps.append(step)
                    goal_distances.append(np.linalg.norm(env.positions[idx] - env.goal))
            
            step += 1

    print(f"Total Crashes in {total_episodes} clustered episodes: {len(crash_steps)}")
    if crash_steps:
        print(f"Average Step of Crash: {np.mean(crash_steps):.1f}")
        print(f"Average Goal Distance at Crash: {np.mean(goal_distances):.2f}")
        print(f"Goal Distance Min/Max: {np.min(goal_distances):.2f} / {np.max(goal_distances):.2f}")
    
if __name__ == '__main__':
    analyze_crashes()
