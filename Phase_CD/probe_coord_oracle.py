"""
COORDINATION ORACLE (TEST 1) — can healthy teammates body-block / screen a rammer
to protect its target?  Oracle = perfect-info interposition (upper bound on feasibility).

Cloned verbatim from probe_ram_oracle_smart.py (load M0, env, rammers, honest_success
metric, seeds, solvable gate, finished set).  ONLY the honest-action rule changes:

  Each step, for each rammer:
    - VICTIM  = the rammer's current target = its nearest ACTIVE honest drone
                (replicates env._ram_action targeting exactly).
    - BLOCKER = the nearest ACTIVE honest drone to the rammer that is NOT the victim.
    - Override the BLOCKER's action to INTERPOSE: steer toward a point BLOCK_GAP metres
      in front of the rammer on the rammer->victim line (i.e. get between them).
      Blend with the policy's obstacle avoidance:  clip(policy_act + W*interpose_unit, -1, 1).
  All other honest drones: policy action.

DECISION (printed):
  coord oracle > ~85%  -> coordination recovers success -> BUILD a learned screening defense.
  coord oracle ~80%    -> RULED OUT (blocker just trades itself for the victim).

Usage:
    python probe_coord_oracle.py 2 models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
Args: [f] [model_path] [n_maps] [W] [BLOCK_GAP]
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
COMM = 8.0
BLOCK_GAP = 0.5      # interpose this far in front of the rammer, on the rammer->victim line
W = 1.0              # interpose blend weight (added to policy action, then clipped)
BASELINE = {0.20: 95.55, 0.30: 91.10}
# reference: M0 ram f=2 = 77.4/73.5 | evasion oracle = 79.7/73.8 | baseline(no rammer) = 95.6/91.1


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


def nearest_active_honest(env, from_idx, traitors, exclude=None):
    """Replicates env._ram_action targeting: nearest ACTIVE honest drone to `from_idx`."""
    pos = env.positions[from_idx]
    best, best_d = None, 1e9
    for j in range(env.n_drones):
        if j == from_idx or j in traitors:
            continue
        if env.possible_agents[j] not in env.agents:
            continue
        if exclude is not None and j == exclude:
            continue
        d = np.linalg.norm(pos - env.positions[j])
        if d < best_d:
            best_d, best = d, j
    return best, best_d


def main():
    f = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    model_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    n_maps = int(sys.argv[3]) if len(sys.argv) > 3 else NUM_MAPS
    w = float(sys.argv[4]) if len(sys.argv) > 4 else W
    block_gap = float(sys.argv[5]) if len(sys.argv) > 5 else BLOCK_GAP
    traitors = set(range(f))
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] COORD ORACLE | model={model_path} | f={f} | W={w} BLOCK_GAP={block_gap}m | maps={n_maps}")
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
                print(f"  [{density:.2f}] {map_idx + 1}/{n_maps}")
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

                # --- compute interpose overrides: blocker_idx -> blended action ---
                overrides = {}
                act_by_idx = {amap[a]: act[k] for k, a in enumerate(active)}
                for r in traitors:
                    if env.possible_agents[r] not in env.agents:
                        continue
                    victim, _ = nearest_active_honest(env, r, traitors)
                    if victim is None:
                        continue
                    blocker, _ = nearest_active_honest(env, r, traitors, exclude=victim)
                    if blocker is None or blocker not in act_by_idx:
                        continue
                    # interpose point: BLOCK_GAP in front of the rammer, on rammer->victim line
                    rv = env.positions[victim] - env.positions[r]
                    nrv = np.linalg.norm(rv)
                    if nrv < 1e-6:
                        continue
                    block_pt = env.positions[r] + block_gap * (rv / nrv)
                    inter = block_pt - env.positions[blocker]
                    ni = np.linalg.norm(inter)
                    if ni < 1e-6:
                        continue
                    inter_u = (inter / ni).astype(np.float32)
                    blended = np.clip(act_by_idx[blocker] + w * inter_u, -1.0, 1.0).astype(np.float32)
                    overrides[blocker] = blended   # last rammer wins if a drone blocks two

                action = {}
                for k, a in enumerate(active):
                    idx = amap[a]
                    if idx in traitors:
                        action[a] = act[k]
                    elif idx in overrides:
                        action[a] = overrides[idx]
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
        row = {"density": density, "f": f, "defense": "coord_interpose",
               "oracle_honest_success": succ, "honest_timeout": 100.0 * h_timeout / denom,
               "honest_collision": 100.0 * h_coll / denom, "honest_drone_collision": 100.0 * h_drone / denom,
               "baseline_success": base, "W": w, "block_gap": block_gap}
        results.append(row)
        print(f"[*] d={density:.2f}: COORD oracle honest_success {succ:.2f}%  (baseline {base:.2f}%) "
              f"| timeout {row['honest_timeout']:.2f}% | coll {row['honest_collision']:.2f}% "
              f"(drone {row['honest_drone_collision']:.2f}%)")

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"oracle_coord_f{f}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 66)
    print("DECISION:")
    print("  coord oracle > ~85%  -> coordination RECOVERS -> BUILD a learned screening defense (M2)")
    print("  coord oracle ~80%    -> RULED OUT (blocker just trades itself for the victim)")
    print("  refs: M0 ram=77.4/73.5 | evasion oracle=79.7/73.8 | baseline(no rammer)=95.6/91.1")
    print("=" * 66)


if __name__ == "__main__":
    main()
