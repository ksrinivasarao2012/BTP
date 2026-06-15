import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
import time
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10 import SwarmLidarEnv_StepB10

# ======================================================
#  MAPPO Custom Policy classes matching Phase B10 v14
# ======================================================
class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers = []
        last_layer_dim_pi = 130
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

        vf_layers = []
        last_layer_dim_vf = 520
        for curr_layer_dim in net_arch['vf']:
            vf_layers.append(nn.Linear(last_layer_dim_vf, curr_layer_dim))
            vf_layers.append(activation_fn())
            last_layer_dim_vf = curr_layer_dim
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

    def forward(self, features): return self.policy_net(features[:, :130]), self.value_net(features[:, 130:])
    def forward_actor(self, features): return self.policy_net(features[:, :130])
    def forward_critic(self, features): return self.value_net(features[:, 130:])

class MAPPO_Policy_B5(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)


# ======================================================
#  Main Evaluation Logic
# ======================================================
def main():
    # Check both potential model paths for robustness
    model_paths = [
        os.path.join("models", "apex_ultra_glide_v14_final.zip"),
        os.path.join("v10_IEEE_Final", "v14_Best_Model_Archive", "model", "apex_ultra_glide_v14_final.zip")
    ]
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
            
    if model_path is None:
        print(f"Error: Model not found at any expected location: {model_paths}")
        sys.exit(1)

    print(f"[*] Loading model from: {model_path}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    print("[*] Model loaded successfully.")

    # Target densities to evaluate
    densities = [0.10, 0.15, 0.20, 0.25, 0.30]
    num_maps = 200
    n_drones = 10

    results = []

    print("\n" + "=" * 60)
    print(f"  STARTING SWEEP EVALUATION ({num_maps} Maps per Density)")
    print("=" * 60)

    for density in densities:
        print(f"\n[DENSITY {density:.2f}] Initializing environment...")
        env = SwarmLidarEnv_StepB10(render_mode=None, target_density=density)

        # Counters for this density
        stats = {
            "success": 0,
            "timeout": 0,
            "wall_collision": 0,
            "obstacle_collision": 0,
            "drone_collision": 0,
            "total_drones": 0,
            "total_steps_success": 0,
            "success_count": 0,
            "discarded_maps": 0,
            "fallback_count": 0
        }

        t0 = time.time()

        for map_idx in range(num_maps):
            # Report progress
            if (map_idx + 1) % 100 == 0:
                elapsed = time.time() - t0
                print(f"  -> Progress: {map_idx + 1}/{num_maps} maps completed | Elapsed: {elapsed:.1f}s")

            # Solvability loop: Keep resetting until we get a map that is 100% solvable for all 10 drones
            attempts = 0
            while True:
                current_seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=current_seed, options={"spawn_mode": "clustered"})
                
                # Check solvability for all 10 drones
                map_fully_solvable = True
                for agent in env.possible_agents:
                    idx = env.agent_name_mapping[agent]
                    pos = env.positions[idx]
                    if not env._is_map_solvable(start_pos=pos):
                        map_fully_solvable = False
                        break
                
                if map_fully_solvable:
                    # Capture the fallback count from the environment reset
                    stats["fallback_count"] += getattr(env, "fallback_count", 0)
                    break
                
                stats["discarded_maps"] += 1
                attempts += 1

            done = False
            step_count = 0
            finished = set()  # agents already tallied (prevents double-counting stale terminations)

            # Store mapping of agent names to their indices
            agent_mapping = {agent: env.agent_name_mapping[agent] for agent in env.possible_agents}

            while not done:
                active_agents = [a for a in obs_dict.keys() if a not in finished]
                if not active_agents:
                    break

                obs_batch = np.array([obs_dict[agent] for agent in active_agents])
                action_batch, _ = model.predict(obs_batch, deterministic=True)
                action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}

                # Before stepping, keep track of active positions to check drone-drone collision source
                active_positions = {agent: env.positions[agent_mapping[agent]].copy() for agent in active_agents}

                obs_dict, rews, terms, truncs, infos = env.step(action_dict)
                step_count += 1

                # Tally terminations/truncations
                for agent in active_agents:
                    if (terms.get(agent, False) or truncs.get(agent, False)) and agent not in finished:
                        finished.add(agent)
                        cause = infos[agent].get("cause")
                        stats["total_drones"] += 1

                        if cause == "success":
                            stats["success"] += 1
                            stats["total_steps_success"] += step_count
                            stats["success_count"] += 1
                        elif cause == "timeout":
                            stats["timeout"] += 1
                        elif cause == "collision":
                            # Retrieve coordinates to categorize the collision type
                            px, py = active_positions[agent]

                            # 1. Wall collision
                            hit_wall = min(px, env.WIDTH - px, py, env.HEIGHT - py) <= 0.05

                            # 2. Obstacle collision
                            hit_obstacle = False
                            for ox, oy, orad in env.obstacles:
                                if (px - ox)**2 + (py - oy)**2 < (env.drone_radius + orad)**2:
                                    hit_obstacle = True
                                    break

                            # 3. Drone-to-drone collision
                            hit_drone = False
                            for other_agent in active_agents:
                                if other_agent == agent:
                                    continue
                                ox, oy = active_positions[other_agent]
                                if (px - ox)**2 + (py - oy)**2 < (2 * env.drone_radius)**2:
                                    hit_drone = True
                                    break

                            # Attribute the collision type
                            if hit_drone:
                                stats["drone_collision"] += 1
                            elif hit_obstacle:
                                stats["obstacle_collision"] += 1
                            elif hit_wall:
                                stats["wall_collision"] += 1
                            else:
                                # Fallback default
                                stats["obstacle_collision"] += 1

                if not env.agents:
                    done = True

            # Safety check: if env loop ended but some agents weren't accounted for
            # (shouldn't happen with proper done flags)

        env.close()

        total = max(stats["total_drones"], 1)
        success_rate = stats["success"] / total
        timeout_rate = stats["timeout"] / total
        wall_rate = stats["wall_collision"] / total
        obstacle_rate = stats["obstacle_collision"] / total
        drone_rate = stats["drone_collision"] / total
        total_collision_rate = (stats["wall_collision"] + stats["obstacle_collision"] + stats["drone_collision"]) / total
        mean_steps = stats["total_steps_success"] / max(stats["success_count"], 1)

        print(f"[*] Density {density:.2f} Finished. Success: {success_rate*100:.2f}% | Wall Coll: {wall_rate*100:.2f}% | Obs Coll: {obstacle_rate*100:.2f}% | Drone Coll: {drone_rate*100:.2f}% | Timeout: {timeout_rate*100:.2f}% | Fallbacks: {stats['fallback_count']} | Clean Maps: {num_maps}/{num_maps + stats['discarded_maps']}")

        results.append({
            "density": density,
            "success_rate": success_rate,
            "timeout_rate": timeout_rate,
            "wall_collision_rate": wall_rate,
            "obstacle_collision_rate": obstacle_rate,
            "drone_collision_rate": drone_rate,
            "total_collision_rate": total_collision_rate,
            "mean_steps_success": mean_steps,
            "clean_maps": num_maps,
            "discarded_maps": stats["discarded_maps"],
            "fallback_count": stats["fallback_count"]
        })

    # Save results to CSV
    df = pd.DataFrame(results)
    results_dir = os.path.join("v10_IEEE_Final", "results", "v14_sweep")
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, "v14_density_sweep_metrics.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n[OK] Swept metrics saved to: {csv_path}")

    # ======================================================
    #  PLOTTING GRAPHICAL OUTPUTS
    # ======================================================
    print("[*] Generating line graphs...")
    
    # Set up matplotlib style
    plt.rcParams.update({
        'font.size': 11,
        'font.family': 'sans-serif',
        'axes.edgecolor': '#cccccc',
        'axes.linewidth': 0.8
    })

    fig, axs = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    axs = axs.ravel()

    # Graph 1: Success Rate
    axs[0].plot(df["density"], df["success_rate"] * 100, marker='o', color='#008080', linewidth=2, label="Success Rate")
    axs[0].set_title("Swarm Success Rate vs Obstacle Density")
    axs[0].set_xlabel("Obstacle Density")
    axs[0].set_ylabel("Success Rate (%)")
    axs[0].set_ylim(0, 105)
    axs[0].grid(True, linestyle='--', alpha=0.5)
    axs[0].legend()

    # Graph 2: Breakdown of Collisions
    axs[1].plot(df["density"], df["wall_collision_rate"] * 100, marker='s', color='#FFA500', linewidth=1.5, label="Wall Collision")
    axs[1].plot(df["density"], df["obstacle_collision_rate"] * 100, marker='^', color='#FF4500', linewidth=1.5, label="Obstacle Collision")
    axs[1].plot(df["density"], df["drone_collision_rate"] * 100, marker='d', color='#8B0000', linewidth=1.5, label="Drone-Drone Collision")
    axs[1].plot(df["density"], df["total_collision_rate"] * 100, marker='o', color='#000000', linewidth=2, linestyle='--', label="Total Collisions")
    axs[1].set_title("Collision Rate Breakdown vs Obstacle Density")
    axs[1].set_xlabel("Obstacle Density")
    axs[1].set_ylabel("Collision Rate (%)")
    axs[1].grid(True, linestyle='--', alpha=0.5)
    axs[1].legend()

    # Graph 3: Timeout Rate
    axs[2].plot(df["density"], df["timeout_rate"] * 100, marker='o', color='#4682B4', linewidth=2, label="Timeout Rate")
    axs[2].set_title("Swarm Timeout Rate vs Obstacle Density")
    axs[2].set_xlabel("Obstacle Density")
    axs[2].set_ylabel("Timeout Rate (%)")
    axs[2].set_ylim(0, 105)
    axs[2].grid(True, linestyle='--', alpha=0.5)
    axs[2].legend()

    # Graph 4: Mean Navigation Steps (to success)
    axs[3].plot(df["density"], df["mean_steps_success"], marker='o', color='#6A5ACD', linewidth=2, label="Mean Steps")
    axs[3].set_title("Mean Steps to Success vs Obstacle Density")
    axs[3].set_xlabel("Obstacle Density")
    axs[3].set_ylabel("Environment Steps")
    axs[3].grid(True, linestyle='--', alpha=0.5)
    axs[3].legend()

    plt.tight_layout()
    plot_path = os.path.join(results_dir, "v14_density_sweep_graphs.png")
    plt.savefig(plot_path)
    plt.close()

    print(f"[OK] Plots successfully saved to: {plot_path}")
    print("=" * 60)
    print("  SWEEP COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
