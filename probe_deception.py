"""
DECEPTION PROBE (Phase C go/no-go test).

Loads the EXISTING comm8_lidar model (no retraining, no trust mechanism) and runs the
density sweep with f traitors whose BROADCAST is falsified (default: false velocity).
The traitors' true positions still appear in LiDAR (physical sensing is never faked);
they navigate normally and only LIE.

Question it answers: does a trusting swarm get hurt by liars?
  - big honest_success drop  -> deception is a real threat -> build the trust mechanism
  - little/no drop           -> swarm ignores lies (LiDAR-dominant) -> pivot (Phase D / harder attack)

Metric: honest_success = (honest drones that reached) / (n - f)   [traitors excluded]

Usage:
    python probe_deception.py                 # f=2, false_velocity
    python probe_deception.py 2 false_velocity
    python probe_deception.py 2 false_position
    python probe_deception.py 3 both
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
MODEL_PATH = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"  # CTDE-clean production base
COMM = 8.0
CONGESTION_MODE = "lidar"   # match how comm8_lidar was trained
BASELINE = {0.20: 95.55, 0.30: 91.10}   # comm8_lidar clean (no traitors), for reference


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
    mode = sys.argv[2] if len(sys.argv) > 2 else "false_velocity"
    traitors = set(range(f))   # drones 0..f-1 are the traitors
    if not os.path.exists(MODEL_PATH):
        print(f"[!] model not found: {MODEL_PATH}"); return
    print(f"[*] DECEPTION PROBE | model={MODEL_PATH}")
    print(f"[*] traitors={sorted(traitors)} (f={f}) | deception={mode} | comm={COMM}m | NO retrain, NO trust")
    model = PPO.load(MODEL_PATH, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=COMM, congestion_mode=CONGESTION_MODE)
        env.traitor_indices = set(traitors)
        env.deception_mode = mode

        h_reached = h_timeout = h_coll = h_drone_coll = h_total = 0   # HONEST-only tallies
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
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {a: act[k] for k, a in enumerate(active)}
                obs_dict, _, terms, truncs, infos = env.step(action)
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        if amap[a] in traitors:
                            continue   # exclude traitors from the metric
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
        drop = (base - succ) if base is not None else float('nan')
        row = {
            "density": density, "f": f, "deception": mode,
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
    out = os.path.join(out_dir, f"probe_f{f}_{mode}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 64)
    print("VERDICT GUIDE:")
    print("  drop large (e.g. >5pp)  -> deception hurts -> BUILD the trust mechanism (Phase C worth it)")
    print("  drop small (~0-2pp)     -> swarm ignores lies -> PIVOT to physical attack (Phase D)")
    print("=" * 64)


if __name__ == "__main__":
    main()
