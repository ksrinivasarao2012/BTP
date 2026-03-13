import os
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import numpy as np

def extract_metrics(log_dir):
    # The log_dir IS the directory containing the tfevents file
    event_acc = EventAccumulator(log_dir)
    event_acc.Reload()
    
    # We want to look at the global average reward
    try:
        reward_events = event_acc.Scalars('rollout/ep_rew_mean')
        rewards = [e.value for e in reward_events]
        
        len_events = event_acc.Scalars('rollout/ep_len_mean')
        lengths = [e.value for e in len_events]
        
        return {
            "final_reward": rewards[-1],
            "max_reward": max(rewards),
            "final_ep_len": lengths[-1],
            "min_ep_len": min(lengths) # Shorter means they hit the goal or a wall faster
        }
    except Exception as e:
        print(f"Metrics missing for {log_dir}: {e}")
        return None

results = {}
base_dir = "./ppo_swarm_tensorboard_experiments"

for experiment in sorted(os.listdir(base_dir)):
    exp_path = os.path.join(base_dir, experiment)
    if os.path.isdir(exp_path):
        metrics = extract_metrics(exp_path)
        if metrics:
            # The folder name created by SB3 usually looks like "Exp_1_Baseline_1"
            results[experiment] = metrics

print("\n" + "="*50)
print(" 🏆 PPO HYPERPARAMETER EXPERIMENT RESULTS 🏆")
print("="*50)

for exp, data in results.items():
    print(f"\n{exp.upper()}:")
    print(f"  Final Average Reward: {data['final_reward']:.2f} (Max: {data['max_reward']:.2f})")
    print(f"  Final Episode Length: {data['final_ep_len']:.1f} (Min: {data['min_ep_len']:.1f})")

# Determine winner based on highest final sustained reward
if results:
    winner = max(results.keys(), key=lambda k: results[k]["final_reward"])
    print("\n" + "="*50)
    print(f"🥇 WINNING ALGORITHM: {winner}")
    print("="*50 + "\n")
