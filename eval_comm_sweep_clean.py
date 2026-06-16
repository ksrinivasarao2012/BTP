"""
CLEAN comm-range sensitivity sweep (replaces the leaky per-range sweep).

The old sweep trained ONE model per comm range, but those used congestion_mode="env" (ground-truth
count = leak) and the unlimited point used the omniscient v14_final. This clean version instead takes
the single VERIFIED-CLEAN model M0 (apex_ultra_glide_v14_comm8_lidar_final, 8 m comm + LiDAR congestion)
and evaluates it at DIFFERENT EVAL-TIME communication ranges. It answers the deployment question:
"does the LiDAR-grounded policy degrade if comm is restricted/extended at deployment?" with no leak.

Output: results/clean/comm_sweep/comm_range_sweep_clean.csv

Run: & "C:\\Users\\Srinivasa\\miniconda3\\envs\\swarm_rl\\python.exe" eval_comm_sweep_clean.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"   # CLEAN M0
DENSITIES = [0.20, 0.30]
NUM_MAPS = 200
RANGES = [0.0, 3.0, 5.0, 8.0, 1e9]   # 0=blackout ... 1e9=unlimited (eval-time gating)


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


def run(model, comm, density):
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm, congestion_mode="lidar")
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    s = {"succ": 0, "to": 0, "coll": 0, "drone": 0, "tot": 0}
    for map_idx in range(NUM_MAPS):
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
            obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
            act, _ = model.predict(obs_batch, deterministic=True)
            obs_dict, _, terms, truncs, infos = env.step({a: act[k] for k, a in enumerate(active)})
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a); s["tot"] += 1
                    c = infos[a].get("cause")
                    if c == "success": s["succ"] += 1
                    elif c == "timeout": s["to"] += 1
                    elif c == "collision":
                        s["coll"] += 1
                        if infos[a].get("collision_type") == "drone": s["drone"] += 1
            if not env.agents:
                done = True
    env.close()
    tot = max(s["tot"], 1)
    return {"success_rate": s["succ"] / tot, "timeout_rate": s["to"] / tot,
            "collision_rate": s["coll"] / tot, "drone_collision_rate": s["drone"] / tot}


def main():
    if not os.path.exists(MODEL):
        print(f"[!] model not found: {MODEL}"); return
    print(f"[*] CLEAN comm-range sweep (eval-time gating) | model={MODEL} | congestion=lidar | {NUM_MAPS} maps")
    model = PPO.load(MODEL, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    rows = []
    for comm in RANGES:
        for density in DENSITIES:
            r = run(model, comm, density)
            label = "inf" if comm >= 1e8 else f"{comm:.0f}m"
            rows.append({"comm_range": comm, "comm_label": label, "density": density, **r})
            print(f"[*] comm={label:<5} d={density:.2f}: success {r['success_rate']*100:.2f}% | "
                  f"timeout {r['timeout_rate']*100:.2f}% | coll {r['collision_rate']*100:.2f}%")
    out_dir = os.path.join("results", "clean", "comm_sweep")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "comm_range_sweep_clean.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("Expectation: ~flat across ranges -> swarm is LiDAR-grounded, comm range is not load-bearing.")


if __name__ == "__main__":
    main()
