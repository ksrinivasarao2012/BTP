import os
from stable_baselines3 import PPO
from swarm_env_step_A import SwarmLidarEnv_StepA
import numpy as np

def test_model(model_path, num_episodes=100):
    model = PPO.load(model_path)
    env = SwarmLidarEnv_StepA(render_mode=None)
    
    success_count = 0
    collision_count = 0
    total_steps = 0
    
    for _ in range(num_episodes):
        obs, info = env.reset()
        episode_success = 0
        episode_collision = 0
        
        while env.agents:
            actions = {}
            for agent in env.agents:
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
            
            obs, rewards, terminations, truncations, infos = env.step(actions)
            total_steps += 1
            
            for agent, term in terminations.items():
                if term and agent in rewards:
                    if rewards[agent] <= -50.0:
                        episode_collision += 1
                    elif rewards[agent] >= 50.0:
                        episode_success += 1
                        
        success_count += episode_success
        collision_count += episode_collision
        
    env.close()
    
    total_drones = num_episodes * 10
    success_rate = (success_count / total_drones) * 100
    collision_rate = (collision_count / total_drones) * 100
    timeout_rate = 100 - success_rate - collision_rate
    
    return success_rate, collision_rate, timeout_rate

results = {}
models_dir = "./models/experiments"

print("="*50)
print(" 🔬 EVALUATING EXPERIMENTAL MODELS (100 Episodes Each) 🔬")
print("="*50)

for file in sorted(os.listdir(models_dir)):
    if file.endswith(".zip"):
        path = os.path.join(models_dir, file)
        name = file.replace(".zip", "")
        print(f"Testing {name}...")
        
        # Suppress PyGame welcome message
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
        
        s_rate, c_rate, t_rate = test_model(path)
        results[name] = {"success": s_rate, "collision": c_rate, "timeout": t_rate}
        
print("\n" + "="*50)
print(" 🏆 FINAL RESULTS 🏆")
print("="*50)
for name, res in results.items():
    print(f"{name}:")
    print(f"  Success:   {res['success']:.1f}%")
    print(f"  Collision: {res['collision']:.1f}%")
    print(f"  Timeout:   {res['timeout']:.1f}%\n")

winner = max(results.keys(), key=lambda k: results[k]["success"])
print(f"🥇 BEST CONFIGURATION: {winner}")
