"""
BEYOND-SENSING COMM PROBE — is there NON-REDUNDANT information in the communication
channel worth protecting (i.e. does a trust mechanism have anything to defend)?

WHY: comm deception was INERT because comm range (8 m) < LiDAR range (12 m): every drone
you HEAR about you can already SEE, so lying is pointless. If we extend comm BEYOND LiDAR,
drones learn about teammates/rammers they cannot yet sense. The question:

  Does raising communication_range > 12 m improve honest_success vs RAMMERS?
    - YES (rises with range) -> comm carries non-redundant beyond-sensing info -> a liar could
      poison it -> a T-Cell TRUST defense has a real target -> POSITIVE "Trust-Aware" paper alive.
    - NO  (flat / falls)     -> local sensing dominates; comm is redundant -> nothing to protect
      -> confirms & explains the FUNDAMENTAL-LIMIT result.

CONFOUND (report honestly): M0 was TRAINED at communication_range=8.0. At eval we feed it
neighbor slots that were zeros in training. A POSITIVE result is therefore decisive (it helps
DESPITE no retraining); a NULL is suggestive but not final (M0 may simply not exploit info it
was never trained on). A positive here justifies a retrain at extended comm.

Usage:
    python probe_comm_range.py 2 models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
Args: [f] [model_path] [n_maps]
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
# --- run from anywhere: put repo root on path + resolve relative model/result paths there ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)
# -------------------------------------------------------------------------------------------
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
NUM_MAPS = 200
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM_RANGES = [8.0, 12.0, 16.0, 20.0]   # 8 = trained baseline; 12 = LiDAR range; 16/20 = beyond sensing
BASELINE = {0.20: 95.55, 0.30: 91.10}   # no-rammer reference
# reference: M0 ram f=2 @ comm8 = 77.4/73.5


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


def run(model, density, comm_range, traitors, n_maps):
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode="lidar")
    env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

    h_reached = h_timeout = h_coll = h_drone = h_total = 0
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
            action = {a: act[k] for k, a in enumerate(active)}   # pure policy (rammers handled in env.step)
            obs_dict, _, terms, truncs, infos = env.step(action)
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a)
                    if amap[a] in traitors:
                        continue
                    h_total += 1
                    c = infos[a].get("cause")
                    if c == "success": h_reached += 1
                    elif c == "timeout": h_timeout += 1
                    elif c == "collision":
                        h_coll += 1
                        if infos[a].get("collision_type") == "drone": h_drone += 1
            if not env.agents:
                done = True
    env.close()
    denom = max(h_total, 1)
    return {"density": density, "f": len(traitors), "comm_range": comm_range,
            "honest_success": 100.0 * h_reached / denom,
            "honest_timeout": 100.0 * h_timeout / denom,
            "honest_collision": 100.0 * h_coll / denom,
            "honest_drone_collision": 100.0 * h_drone / denom,
            "baseline_no_rammer": BASELINE.get(density)}


def main():
    f = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    model_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    n_maps = int(sys.argv[3]) if len(sys.argv) > 3 else NUM_MAPS
    traitors = set(range(f))
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] COMM-RANGE PROBE | model={model_path} | f={f} | ranges={COMM_RANGES} | maps={n_maps}")
    print("    (LiDAR range = 12 m; ranges > 12 m feed M0 beyond-sensing neighbor info)")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for cr in COMM_RANGES:
        for density in DENSITIES:
            row = run(model, density, cr, traitors, n_maps)
            results.append(row)
            print(f"[*] comm={cr:>4.1f}m d={density:.2f}: honest_success {row['honest_success']:.2f}% "
                  f"| timeout {row['honest_timeout']:.2f}% | coll {row['honest_collision']:.2f}% "
                  f"(drone {row['honest_drone_collision']:.2f}%)")

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"comm_range_f{f}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 70)
    print("DECISION:")
    print("  honest_success RISES with comm range -> non-redundant beyond-sensing info exists")
    print("    -> a liar can poison it -> TRUST defense has a target -> POSITIVE Trust-Aware paper alive")
    print("  honest_success FLAT/FALLS -> local sensing dominates, comm redundant")
    print("    -> nothing to protect -> confirms & explains the FUNDAMENTAL-LIMIT result")
    print("  (M0 trained at comm=8 -> a POSITIVE is decisive; a NULL is suggestive, not final)")
    print("=" * 70)


if __name__ == "__main__":
    main()
