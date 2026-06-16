"""
ORACLE-EVASION feasibility test (no training) — is evading a rammer even POSSIBLE?

Runs the chosen model vs f rammers, but OVERLAYS a perfect, ground-truth-informed dodge on
the honest drones: whenever a rammer is within EVADE_DIST, the honest drone's action is
overridden to steer directly away (full throttle). This measures the CEILING of evasion.

Interpretation:
  oracle  >> M0/M1 (collisions drop, success rises)  -> evasion is POSSIBLE -> build M2 (it has headroom)
  oracle  ~  M0/M1 (collisions stay high)            -> evasion IMPOSSIBLE  -> M2 won't help; reframe
  collisions drop but timeouts rise (success flat)   -> goal-vs-dodge dilemma (M2 must learn WHEN to dodge)

NOTE: the oracle uses true positions (an upper-bound oracle). It is NOT a deployable policy —
it answers "is evasion feasible at all?", which bounds whether a learned defense can work.

Usage:
    python probe_ram_oracle.py                 # M0 base, f=2, EVADE_DIST=2.0
    python probe_ram_oracle.py 2 2.0 models/apex_ultra_glide_M1_ram_final.zip
Args: [f] [evade_dist] [model_path]
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
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM = 8.0
FLEE_WEIGHT = 1.0   # dodge strength ADDED on top of the policy (which still avoids obstacles)
BASELINE = {0.20: 95.55, 0.30: 91.10}
# reference (no oracle): M0 ram f=2 = 77.38/73.50 ; M1 ram f=2 = 80.44/74.38


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
    evade_dist = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    model_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL
    n_maps = int(sys.argv[4]) if len(sys.argv) > 4 else NUM_MAPS   # optional: fewer maps for a quick test
    traitors = set(range(f))
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] ORACLE-EVASION TEST | model={model_path} | f={f} | EVADE_DIST={evade_dist}m")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=COMM, congestion_mode="lidar")
        env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

        h_reached = h_timeout = h_coll = h_drone = h_total = 0
        for map_idx in range(n_maps):
            if (map_idx + 1) % 100 == 0:
                print(f"  [{density:.2f}] {map_idx + 1}/{NUM_MAPS}")
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
                action = {}
                for k, a in enumerate(active):
                    idx = amap[a]
                    if idx in traitors:
                        action[a] = act[k]   # rammer action ignored by env anyway
                        continue
                    # ORACLE EVASION: if a rammer is within EVADE_DIST, flee directly away
                    pos = env.positions[idx]
                    nearest_d, nearest_r = 1e9, None
                    for tj in traitors:
                        if env.possible_agents[tj] in env.agents:
                            d = np.linalg.norm(pos - env.positions[tj])
                            if d < nearest_d:
                                nearest_d, nearest_r = d, tj
                    if nearest_r is not None and nearest_d < evade_dist:
                        flee = pos - env.positions[nearest_r]
                        n = np.linalg.norm(flee)
                        if n > 1e-6:
                            flee_u = (flee / n).astype(np.float32)
                            # OBSTACLE-AWARE dodge: keep the policy's action (which avoids obstacles/goal)
                            # and ADD a repulsion away from the rammer -> dodge without flying into walls.
                            action[a] = np.clip(act[k] + FLEE_WEIGHT * flee_u, -1.0, 1.0).astype(np.float32)
                        else:
                            action[a] = act[k]
                    else:
                        action[a] = act[k]
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
        succ = 100.0 * h_reached / denom
        base = BASELINE.get(density)
        row = {"density": density, "f": f, "evade_dist": evade_dist,
               "oracle_honest_success": succ, "honest_timeout": 100.0 * h_timeout / denom,
               "honest_collision": 100.0 * h_coll / denom, "honest_drone_collision": 100.0 * h_drone / denom,
               "baseline_success": base}
        results.append(row)
        print(f"[*] d={density:.2f}: ORACLE honest_success {succ:.2f}%  (baseline {base:.2f}%) "
              f"| timeout {row['honest_timeout']:.2f}% | coll {row['honest_collision']:.2f}% "
              f"(drone {row['honest_drone_collision']:.2f}%)")

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"oracle_evade_f{f}_d{evade_dist}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 66)
    print("DECISION:")
    print("  oracle >> M0/M1 (coll drops, success rises) -> evasion POSSIBLE -> BUILD M2 (has headroom)")
    print("  oracle ~ M0/M1 (coll stays high)            -> evasion IMPOSSIBLE -> reframe defense")
    print("  coll drops but timeout rises (success flat) -> goal-vs-dodge dilemma (M2 learns WHEN to dodge)")
    print("  reference: M0 f=2 = 77.4/73.5 ; M1 f=2 = 80.4/74.4")
    print("=" * 66)


if __name__ == "__main__":
    main()
