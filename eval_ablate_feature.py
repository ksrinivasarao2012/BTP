"""
Eval-time feature ablation on the EXISTING 8m model (NO retraining).

Loads v14_8.0m and runs the density sweep while ZEROING one feature group in the
observation before each action. Reports success / timeout / collisions, so you get
a PERFORMANCE-level importance for each feature (complements feature_sensitivity.py,
which measured action-level change).

Usage:
    python eval_ablate_feature.py none         # baseline (no ablation) -- sanity check
    python eval_ablate_feature.py lidar        # zero LiDAR [6:54]
    python eval_ablate_feature.py goaldir      # zero Dijkstra goal direction [2:4]
    python eval_ablate_feature.py neighbors    # zero obs_neighbors [54:99]
    python eval_ablate_feature.py sync         # zero sync features [100:120]
    python eval_ablate_feature.py congestion   # zero congestion [99]
    python eval_ablate_feature.py trajectory   # zero trajectory [120:130]
    python eval_ablate_feature.py egovel       # zero ego velocity [0:2]

NOTE: eval-time ablation overstates importance (out-of-distribution). It measures
this trained model's DEPENDENCE, not task NECESSITY (that needs retraining).
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

DENSITIES = [0.20, 0.30]
NUM_MAPS = 200
MODEL_PATH = "models/apex_ultra_glide_v14_8_0m_final.zip"
COMM = 8.0

FEATURE_GROUPS = {
    "none":       None,
    "egovel":     (0, 2),
    "goaldir":    (2, 4),
    "goaldist":   (4, 5),
    "yaw":        (5, 6),
    "lidar":      (6, 54),
    "neighbors":  (54, 99),
    "congestion": (99, 100),
    "sync":       (100, 120),
    "trajectory": (120, 130),
}


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
    group = sys.argv[1].lower() if len(sys.argv) > 1 else "none"
    if group not in FEATURE_GROUPS:
        print(f"Unknown group '{group}'. Options: {list(FEATURE_GROUPS)}")
        sys.exit(1)
    span = FEATURE_GROUPS[group]
    if not os.path.exists(MODEL_PATH):
        print(f"[!] model not found: {MODEL_PATH}"); return
    print(f"[*] EVAL-TIME ABLATION on {MODEL_PATH}")
    print(f"[*] zeroing feature group: {group} {span if span else '(none - baseline)'} | comm={COMM}m | no retrain")
    model = PPO.load(MODEL_PATH, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density, communication_range=COMM)
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
                obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
                if span is not None:
                    obs_batch[:, span[0]:span[1]] = 0.0   # <-- the ablation
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
                            else:  # fallback for models/runs where env didn't tag the type
                                # env always tags collision_type now; reaching here = stale env.
                                # Count separately so it is NEVER silently misclassified (shows as a gap in totals).
                                stats["unknown_collision"] = stats.get("unknown_collision", 0) + 1
                if not env.agents:
                    done = True
        env.close()

        tot = max(stats["total_drones"], 1)
        row = {
            "ablated_feature": group,
            "density": density,
            "success_rate": stats["success"] / tot,
            "timeout_rate": stats["timeout"] / tot,
            "drone_collision_rate": stats["drone_collision"] / tot,
            "total_collision_rate": (stats["wall_collision"] + stats["obstacle_collision"] + stats["drone_collision"]) / tot,
            "mean_steps_success": stats["total_steps_success"] / max(stats["success_count"], 1),
        }
        results.append(row)
        print(f"[*] ablate[{group}] d={density:.2f}: success {row['success_rate']*100:.2f}% | "
              f"timeout {row['timeout_rate']*100:.2f}% | drone-coll {row['drone_collision_rate']*100:.2f}% | "
              f"total-coll {row['total_collision_rate']*100:.2f}%")

    out_dir = os.path.join("results", "eval_ablation")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"ablate_{group}_metrics.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("Compare against baseline 'none': 8m = 95.45% / 91.25%.")


if __name__ == "__main__":
    main()
