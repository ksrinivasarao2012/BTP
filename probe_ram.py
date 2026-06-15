"""
PHYSICAL-AGGRESSION PROBE (ramming).

Loads the EXISTING comm8_lidar model (no retrain, no defense) and runs the density sweep
with f traitors that physically RAM the nearest honest drone (traitor_behavior="ram").
Traitors ignore the policy and steer to collide; honest drones can only dodge via LiDAR.

Question: does an active physical attacker hurt the swarm (where lying did not)?
  - honest_success drops + drone_collision rises -> ramming is the REAL threat -> build a Phase D defense
  - barely drops                                  -> swarm dodges well -> exceptionally robust, reframe

Metric: honest_success = (honest reached) / (n - f)   [traitors excluded]

Usage:
    python probe_ram.py        # f=2 rammers
    python probe_ram.py 3      # f=3 rammers
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
MODEL_PATH = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM = 8.0
CONGESTION_MODE = "lidar"
BASELINE = {0.20: 95.55, 0.30: 91.10}


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
    f = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    model_path = sys.argv[2] if len(sys.argv) > 2 else MODEL_PATH   # optional: eval a different model (e.g. M1)
    traitors = set(range(f))
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] RAM PROBE | model={model_path}")
    print(f"[*] traitors={sorted(traitors)} (f={f}) | behavior=RAM | comm={COMM}m")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=COMM, congestion_mode=CONGESTION_MODE)
        env.traitor_indices = set(traitors)
        env.traitor_behavior = "ram"
        env.deception_mode = "none"   # pure physical attack (lying proven inert)

        h_reached = h_timeout = h_coll = h_drone_coll = h_total = 0
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
                attempts += 1

            amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
            finished = set()
            done = False
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)   # traitor actions overridden in env
                action = {a: act[k] for k, a in enumerate(active)}
                obs_dict, _, terms, truncs, infos = env.step(action)
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        if amap[a] in traitors:
                            continue
                        h_total += 1
                        cause = infos[a].get("cause")
                        if cause == "success":
                            h_reached += 1
                        elif cause == "timeout":
                            h_timeout += 1
                        elif cause == "collision":
                            h_coll += 1
                            if infos[a].get("collision_type") == "drone":
                                h_drone_coll += 1
                if not env.agents:
                    done = True
        env.close()

        denom = max(h_total, 1)
        succ = 100.0 * h_reached / denom
        base = BASELINE.get(density)
        drop = base - succ
        row = {
            "density": density, "f": f, "behavior": "ram",
            "honest_success": succ,
            "honest_timeout": 100.0 * h_timeout / denom,
            "honest_collision": 100.0 * h_coll / denom,
            "honest_drone_collision": 100.0 * h_drone_coll / denom,
            "baseline_success": base, "drop_vs_baseline": round(drop, 2),
        }
        results.append(row)
        print(f"[*] d={density:.2f}: honest_success {succ:.2f}%  (baseline {base:.2f}%, drop {drop:+.2f}pp) "
              f"| timeout {row['honest_timeout']:.2f}% | coll {row['honest_collision']:.2f}% "
              f"(drone {row['honest_drone_collision']:.2f}%)")

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"probe_ram_f{f}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 64)
    print("VERDICT GUIDE:")
    print("  big drop + drone_collision up -> RAMMING hurts -> build Phase D defense (real threat)")
    print("  small drop                    -> swarm dodges well -> exceptionally robust, reframe story")
    print("=" * 64)


if __name__ == "__main__":
    main()
