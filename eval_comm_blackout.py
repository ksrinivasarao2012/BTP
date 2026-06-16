"""
Blackout evaluation script.
Loads the model trained with communication range 8.0m, but evaluates it in an environment
with communication range set to 0.0m (complete communication blackout).
Outputs results to results/comm_sweep/comm8_to_0m_blackout_metrics.csv.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]   # recommended scope
NUM_MAPS = 200


class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], 130
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], 520
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f): return self.policy_net(f[:, :130])
    def forward_critic(self, f): return self.value_net(f[:, 130:])


class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)


def main():
    model_path = os.path.join("models", "apex_ultra_glide_v14_comm8_lidar_final.zip")  # CLEAN M0
    if not os.path.exists(model_path):
        print(f"[!] Model not found: {model_path}")
        sys.exit(1)
        
    print(f"[*] Loading model (trained at 8.0m range): {model_path}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    print("\n" + "=" * 60)
    print(f"  COMM-BLACKOUT EVAL | Model range=8m | Eval range=0m | {NUM_MAPS} maps/density")
    print("=" * 60)

    for density in DENSITIES:
        # Enforce communication_range = 0.0m
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density, communication_range=0.0, congestion_mode="lidar")
        stats = {"success": 0, "timeout": 0, "wall_collision": 0, "obstacle_collision": 0,
                 "drone_collision": 0, "total_drones": 0, "total_steps_success": 0,
                 "success_count": 0, "discarded_maps": 0}

        for map_idx in range(NUM_MAPS):
            if (map_idx + 1) % 100 == 0:
                print(f"  [{density:.2f}] {map_idx + 1}/{NUM_MAPS}")
            attempts = 0
            while True:
                seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                ok = all(env._is_map_solvable(start_pos=env.positions[env.agent_name_mapping[a]])
                         for a in env.possible_agents)
                if ok:
                    break
                stats["discarded_maps"] += 1
                attempts += 1

            agent_map = {a: env.agent_name_mapping[a] for a in env.possible_agents}
            finished = set()
            done = False
            step_count = 0
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {a: act[k] for k, a in enumerate(active)}
                active_pos = {a: env.positions[agent_map[a]].copy() for a in active}
                obs_dict, _, terms, truncs, infos = env.step(action)
                step_count += 1
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        cause = infos[a].get("cause")
                        stats["total_drones"] += 1
                        if cause == "success":
                            stats["success"] += 1
                            stats["total_steps_success"] += step_count
                            stats["success_count"] += 1
                        elif cause == "timeout":
                            stats["timeout"] += 1
                        elif cause == "collision":
                            ctype = infos[a].get("collision_type")
                            if ctype == "drone": stats["drone_collision"] += 1
                            elif ctype == "obstacle": stats["obstacle_collision"] += 1
                            elif ctype == "wall": stats["wall_collision"] += 1
                            else:  # fallback for runs where env didn't tag the type
                                # env always tags collision_type now; reaching here = stale env.
                                # Count separately so it is NEVER silently misclassified (shows as a gap in totals).
                                stats["unknown_collision"] = stats.get("unknown_collision", 0) + 1
                if not env.agents:
                    done = True
        env.close()

        tot = max(stats["total_drones"], 1)
        row = {
            "comm_range": 0.0,
            "comm_label": "8to0_blackout",
            "density": density,
            "success_rate": stats["success"] / tot,
            "timeout_rate": stats["timeout"] / tot,
            "total_collision_rate": (stats["wall_collision"] + stats["obstacle_collision"] + stats["drone_collision"]) / tot,
            "mean_steps_success": stats["total_steps_success"] / max(stats["success_count"], 1),
        }
        results.append(row)
        print(f"[*] Blackout 8m->0m d={density:.2f}: success {row['success_rate']*100:.2f}% | "
              f"timeout {row['timeout_rate']*100:.2f}% | coll {row['total_collision_rate']*100:.2f}%")

    out_dir = os.path.join("results", "clean", "comm_sweep")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "comm8_to_0m_blackout_metrics.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")


if __name__ == "__main__":
    main()
