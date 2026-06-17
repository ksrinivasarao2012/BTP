"""
Eval for the Design-A collaborative-perception models (157-d actor). No adversary.

A1 SANITY: the surgically-expanded M0 must reproduce M0 at full sight ->
    python eval_collab.py models/collab_expanded_M0.zip 12 10 on 30      # expect ~92/95
A2 GATE: compare trained comm-ON vs comm-OFF at lidar=5 ->
    python eval_collab.py models/collab_l5_commON_final.zip  5 10 on  200
    python eval_collab.py models/collab_l5_commOFF_final.zip 5 10 off 200

Args: [model_path] [lidar_range] [comm_range] [hazard on|off] [n_maps]
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
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_collab import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
LOCAL_NEW = 157
GLOBAL = 520
OUT = os.path.join(_HERE, "results", "collab_eval.csv")


class MAPPO_Extractor_Collab(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], LOCAL_NEW
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :LOCAL_NEW]), self.value_net(f[:, LOCAL_NEW:])
    def forward_actor(self, f): return self.policy_net(f[:, :LOCAL_NEW])
    def forward_critic(self, f): return self.value_net(f[:, LOCAL_NEW:])


class MAPPO_Policy_Collab(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_Collab(self.features_dim, self.net_arch, self.activation_fn)


def main():
    if len(sys.argv) < 4:
        print("Usage: python eval_collab.py <model> <lidar> <comm> [on|off] [n_maps]"); return
    model_path = sys.argv[1]
    lidar_range = float(sys.argv[2])
    comm_range = float(sys.argv[3])
    hazard_on = (sys.argv[4].lower() == "on") if len(sys.argv) > 4 else True
    n_maps = int(sys.argv[5]) if len(sys.argv) > 5 else 200
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    tag = "commON" if hazard_on else "commOFF"
    print(f"[*] COLLAB EVAL | {os.path.basename(model_path)} | lidar={lidar_range} comm={comm_range} "
          f"hazard={tag} | maps={n_maps} | NO adversary")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_Collab}, device="cpu")

    new_rows = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=comm_range, congestion_mode="lidar",
                                         lidar_range=lidar_range)
        env.share_hazards = hazard_on
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
        reached = timeout = coll = c_obs = c_drone = total = 0
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
                            ct = infos[a].get("collision_type")
                            if ct == "obstacle": c_obs += 1
                            elif ct == "drone": c_drone += 1
                if not env.agents:
                    done = True
        env.close()
        d = max(total, 1)
        succ = 100.0 * reached / d
        new_rows.append({"model": os.path.basename(model_path), "hazard": tag, "lidar": lidar_range,
                         "comm": comm_range, "density": density, "success": succ,
                         "timeout": 100.0*timeout/d, "coll": 100.0*coll/d,
                         "coll_obstacle": 100.0*c_obs/d, "coll_drone": 100.0*c_drone/d, "n_maps": n_maps})
        print(f"[*] d={density:.2f}: success {succ:6.2f}% | coll {100.0*coll/d:5.2f}% "
              f"(obstacle {100.0*c_obs/d:5.2f} | drone {100.0*c_drone/d:5.2f}) | timeout {100.0*timeout/d:.2f}%")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df.to_csv(OUT, index=False)
    print(f"\n[OK] appended to: {OUT}")


if __name__ == "__main__":
    main()
