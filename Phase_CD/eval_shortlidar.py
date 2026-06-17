"""
STAGE 3 GATE EVAL — no-adversary honest_success for a short-LiDAR model.

Evaluates ONE model in the EXACT regime it was trained in (lidar_range + comm_range must be
passed so the env matches). No traitors (this gate measures navigation value of comm).
Appends a row to results/phase_c_probe/comm_value_ablation.csv and prints comm_value if both
the comm-ON and comm-OFF rows for a given lidar are present.

Usage (run once per model):
    python eval_shortlidar.py models/short_lidar5_comm10_final.zip 5 10 200
    python eval_shortlidar.py models/short_lidar5_comm0_final.zip  5 0  200
Args: [model_path] [lidar_range] [comm_range] [n_maps]
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
# --- run from anywhere: put repo root and script folder on path + resolve relative paths ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
    sys.argv[1] = os.path.abspath(sys.argv[1])
os.chdir(_ROOT)
# -------------------------------------------------------------------------------------------
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
OUT = os.path.join("Phase_CD", "results", "comm_value_ablation.csv")


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
    if len(sys.argv) < 4:
        print("Usage: python eval_shortlidar.py <model_path> <lidar_range> <comm_range> [n_maps]")
        sys.exit(1)
    model_path = sys.argv[1]
    lidar_range = float(sys.argv[2])
    comm_range = float(sys.argv[3])
    n_maps = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    tag = "commOFF" if comm_range == 0 else "commON"
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] GATE EVAL | {model_path} | lidar={lidar_range} comm={comm_range} ({tag}) | maps={n_maps} | NO adversary")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    new_rows = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=comm_range, congestion_mode="lidar",
                                         lidar_range=lidar_range)
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
        reached = timeout = coll = total = 0
        coll_drone = coll_obstacle = coll_wall = 0
        for map_idx in range(n_maps):
            attempts = 0
            while True:
                seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                    break
                attempts += 1
            finished = set(); done = False
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {a: act[k] for k, a in enumerate(active)}
                obs_dict, _, terms, truncs, infos = env.step(action)
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        total += 1
                        c = infos[a].get("cause")
                        if c == "success": reached += 1
                        elif c == "timeout": timeout += 1
                        elif c == "collision":
                            coll += 1
                            ctype = infos[a].get("collision_type", "unknown")
                            if ctype == "drone": coll_drone += 1
                            elif ctype == "obstacle": coll_obstacle += 1
                            elif ctype == "wall": coll_wall += 1
                if not env.agents:
                    done = True
        env.close()
        denom = max(total, 1)
        succ = 100.0 * reached / denom
        new_rows.append({"model": os.path.basename(model_path), "tag": tag, "lidar_range": lidar_range,
                         "comm_range": comm_range, "density": density, "honest_success": succ,
                         "timeout": 100.0 * timeout / denom, "collision": 100.0 * coll / denom,
                         "collision_drone": 100.0 * coll_drone / denom,
                         "collision_obstacle": 100.0 * coll_obstacle / denom,
                         "collision_wall": 100.0 * coll_wall / denom,
                         "n_maps": n_maps})
        print(f"[*] d={density:.2f}: no-adversary honest_success {succ:.2f}%  "
              f"(timeout {100.0*timeout/denom:.2f}% coll {100.0*coll/denom:.2f}% "
              f"[drone {100.0*coll_drone/denom:.2f}% obstacle {100.0*coll_obstacle/denom:.2f}% wall {100.0*coll_wall/denom:.2f}%])")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df.to_csv(OUT, index=False)
    print(f"\n[OK] appended to: {OUT}")

    # if both ON and OFF present for this lidar, print comm_value
    for density in DENSITIES:
        sub = df[(df["lidar_range"] == lidar_range) & (df["density"] == density)]
        on = sub[sub["tag"] == "commON"]["honest_success"]
        off = sub[sub["tag"] == "commOFF"]["honest_success"]
        if len(on) and len(off):
            cv = float(on.iloc[-1]) - float(off.iloc[-1])
            print(f"  comm_value @ lidar={lidar_range} d={density:.2f}: ON {float(on.iloc[-1]):.2f}% - OFF {float(off.iloc[-1]):.2f}% = {cv:+.2f} pp")
    print("=" * 66)
    print("GATE (REVIEW CHECKPOINT 2): comm_value >= ~5-10 pp -> comm used & poisonable -> build trust defense.")
    print("                            comm_value ~ 0          -> comm redundant -> fundamental-limit paper.")
    print("=" * 66)


if __name__ == "__main__":
    main()
