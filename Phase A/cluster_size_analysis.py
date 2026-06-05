import numpy as np
from stable_baselines3 import PPO
import supersuit as ss
import os
import sys
import matplotlib.pyplot as plt

# Fix for OpenMP duplicate library error
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.append(os.path.abspath("./Hardened_Baseline"))
sys.path.append(os.path.abspath("./Vanilla_Model"))

from swarm_env_step_A import SwarmLidarEnv_StepA
from swarm_env_vanilla import SwarmLidarEnv_Vanilla

def evaluate_box_size(model, env_class, box_size, num_episodes=100):
    env = env_class()
    env = ss.black_death_v3(env)
    env = ss.pettingzoo_env_to_vec_env_v1(env)
    env = ss.concat_vec_envs_v1(env, 1, num_cpus=1, base_class='stable_baselines3')
    
    successes = 0
    collisions = 0
    total_steps_all = 0
    total_drones = num_episodes * 10
    successes = 0
    collisions = 0
    
    for _ in range(num_episodes):
        cx, cy = np.random.uniform(5.0, 15.0, 2)
        positions = []
        half_box = box_size / 2.0
        for _ in range(10):
            for _ in range(1000):
                x = np.random.uniform(cx - half_box, cx + half_box)
                y = np.random.uniform(cy - half_box, cy + half_box)
                if all(np.linalg.norm(np.array([x,y]) - np.array(p)) >= 0.26 for p in positions):
                    positions.append([x, y])
                    break
            else:
                positions.append([cx + np.random.uniform(-half_box, half_box), cy + np.random.uniform(-half_box, half_box)])
        
        gx, gy = np.random.uniform(2, 18, 2)
        while np.linalg.norm(np.array([gx, gy]) - np.array([cx, cy])) < 10.0:
            gx, gy = np.random.uniform(2, 18, 2)
            
        options = {"start_positions": positions, "goal": [gx, gy]}
        obs = env.reset(options=options)
        
        # Track which drones have been accounted for
        drones_accounted_for = 0
        ep_steps = 0
        
        # We run until ALL 10 drones are finished (success, collision, or timeout)
        while drones_accounted_for < 10 and ep_steps < 600:
            action, _ = model.predict(obs, deterministic=True)
            obs, rewards, dones, infos = env.step(action)
            ep_steps += 1
            
            # Check EVERY info for a cause, even in step 0
            for info in infos:
                if "cause" in info:
                    if info["cause"] == "success": successes += 1
                    elif info["cause"] == "collision": collisions += 1
                    elif info["cause"] == "timeout": pass # timeouts handled by loop end
                    drones_accounted_for += 1
        
        # Any drones left after 600 steps are timeouts
        if drones_accounted_for < 10:
            drones_accounted_for = 10 # Close the episode
            
        total_steps_all += ep_steps
                    
    env.close()
    return (successes / total_drones) * 100, (collisions / total_drones) * 100, (total_steps_all / num_episodes)

def run_analysis():
    master_model_path = "./Hardened_Baseline/models/step_A_foundation_model"
    vanilla_model_path = "./Vanilla_Model/vanilla_fixed_physics_model"
    
    if not os.path.exists(master_model_path + ".zip") or not os.path.exists(vanilla_model_path + ".zip"):
        print("Models not found. Please check paths.")
        return

    print("Loading models...")
    master_model = PPO.load(master_model_path)
    vanilla_model = PPO.load(vanilla_model_path)
    
    # Range of box sizes from physically impossible to completely loose
    box_sizes = [0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    num_episodes = 100 # 1000 drones per size per model
    
    vanilla_successes, vanilla_collisions, vanilla_steps = [], [], []
    master_successes, master_collisions, master_steps = [], [], []
    
    print(f"Starting analysis over {len(box_sizes)} box sizes ({num_episodes} episodes each)...")
    
    for size in box_sizes:
        print(f"\nEvaluating Box Size: {size}m x {size}m")
        
        # Vanilla
        v_succ, v_coll, v_step = evaluate_box_size(vanilla_model, SwarmLidarEnv_Vanilla, size, num_episodes)
        vanilla_successes.append(v_succ)
        vanilla_collisions.append(v_coll)
        vanilla_steps.append(v_step)
        
        # Master
        m_succ, m_coll, m_step = evaluate_box_size(master_model, SwarmLidarEnv_StepA, size, num_episodes)
        master_successes.append(m_succ)
        master_collisions.append(m_coll)
        master_steps.append(m_step)
        
        print(f"    Vanilla -> Success: {v_succ:.1f}%, Steps: {v_step:.1f}")
        print(f"    Master  -> Success: {m_succ:.1f}%, Steps: {m_step:.1f}")

    # Plotting
    plt.figure(figsize=(18, 6))
    
    # Success Plot
    plt.subplot(1, 3, 1)
    plt.plot(box_sizes, vanilla_successes, marker='o', linestyle='--', label='Vanilla', color='red')
    plt.plot(box_sizes, master_successes, marker='s', label='Master', color='green')
    plt.title('Success Rate (%)')
    plt.xlabel('Box Size (m)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Collision Plot
    plt.subplot(1, 3, 2)
    plt.plot(box_sizes, vanilla_collisions, marker='o', linestyle='--', label='Vanilla', color='red')
    plt.plot(box_sizes, master_collisions, marker='s', label='Master', color='green')
    plt.title('Collision Rate (%)')
    plt.xlabel('Box Size (m)')
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Steps Plot
    plt.subplot(1, 3, 3)
    plt.plot(box_sizes, vanilla_steps, marker='o', linestyle='--', label='Vanilla', color='red')
    plt.plot(box_sizes, master_steps, marker='s', label='Master', color='green')
    plt.title('Average Steps (Efficiency)')
    plt.xlabel('Box Size (m)')
    plt.ylabel('Steps')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("cluster_analysis_plot.png", dpi=300)
    print(f"\nAnalysis complete! Plot saved to {plot_path}")
    
if __name__ == "__main__":
    run_analysis()
