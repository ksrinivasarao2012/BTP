# eval_comm_robustness.py
"""Evaluate communication robustness of the clean M0 model.

Pre-empts "isn't perfect, zero-latency 8 m comm unrealistic?". We do NOT modify the verified-clean env.
We perturb ONLY the COMMUNICATED fields in the observation right before the policy sees them (a noisy / lossy
radio); LiDAR, ego, goal and own-LiDAR congestion are never touched. Graceful degradation (no cliff) => the
policy is LiDAR-grounded and not fragilely comm-dependent.

Same structure as the other clean evals (eval_comm_blackout.py / eval_comm_sweep_clean.py): inline policy
classes, direct PettingZoo loop, seed + _is_map_solvable gate, finished set, batched model.predict.

Usage:
    python eval_comm_robustness.py                          # full sweep (18 combos), 200 maps/combo
    python eval_comm_robustness.py --n_maps 50              # quick test
    python eval_comm_robustness.py --start_idx 0 --end_idx 4   # combos 0..3 (one terminal of a 4-way split)
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import itertools
import argparse
import numpy as np
import pandas as pd
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

MODEL_PATH = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"   # CLEAN M0
RESULTS_DIR = "results/clean"
os.makedirs(RESULTS_DIR, exist_ok=True)
COMM = 8.0
DENSITIES = [0.20, 0.30]

# Parameters to sweep
noise_levels = [0.0, 0.1, 0.3]
dropout_probs = [0.0, 0.25, 0.5]
RNG = np.random.default_rng(12345)


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


def apply_comm_noise(obs_batch, noise_std, dropout_p):
    """Perturb ONLY communicated neighbour/sync fields of active in-range neighbours.

    obs_batch: np.ndarray [n_active, 650]. Returns a perturbed copy.
    neighbours [54:99] = 9 x {rel_pos(2), norm_vel(2), is_active(1)} (block k @ 54+5k)
    sync       [100:120] = 5 x {rel_vel(2), stagnation(1), pad(1)}    (slot m @ 100+4m)
    """
    if noise_std == 0.0 and dropout_p == 0.0:
        return obs_batch
    ob = obs_batch.copy()
    for i in range(ob.shape[0]):
        for k in range(9):
            b = 54 + 5 * k
            if ob[i, b + 4] > 0.5:               # is_active -> in-range neighbour
                if dropout_p > 0.0 and RNG.random() < dropout_p:
                    ob[i, b:b + 5] = 0.0         # lost packet
                elif noise_std > 0.0:
                    ob[i, b:b + 4] += RNG.normal(0.0, noise_std, size=4)
        for m in range(5):
            b = 100 + 4 * m
            if np.any(ob[i, b:b + 4] != 0.0):    # active slot
                if dropout_p > 0.0 and RNG.random() < dropout_p:
                    ob[i, b:b + 4] = 0.0
                elif noise_std > 0.0:
                    ob[i, b:b + 2] += RNG.normal(0.0, noise_std, size=2)
    return ob


def evaluate(model, noise_std, dropout_p, density, n_maps):
    """Run n_maps solvable maps for one (noise, dropout, density); return success/timeout/collision %."""
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=COMM, congestion_mode="lidar")
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    succ = to = coll = tot = 0
    for map_idx in range(n_maps):
        attempts = 0
        while True:
            seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
            obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
            if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                break
            attempts += 1
        finished = set()
        done = False
        while not done:
            active = [a for a in obs_dict.keys() if a not in finished]
            if not active:
                break
            obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
            obs_batch = apply_comm_noise(obs_batch, noise_std, dropout_p)
            act, _ = model.predict(obs_batch, deterministic=True)
            obs_dict, _, terms, truncs, infos = env.step({a: act[k] for k, a in enumerate(active)})
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a); tot += 1
                    cause = infos[a].get("cause")
                    if cause == "success": succ += 1
                    elif cause == "timeout": to += 1
                    elif cause == "collision": coll += 1
            if not env.agents:
                done = True
    env.close()
    tot = max(tot, 1)
    return {
        "noise_std": noise_std,
        "dropout_p": dropout_p,
        "density": density,
        "success": 100.0 * succ / tot,
        "timeout": 100.0 * to / tot,
        "collision": 100.0 * coll / tot,
    }


def main(start_idx=None, end_idx=None, n_maps=200):
    if not os.path.exists(MODEL_PATH):
        print(f"[!] model not found: {MODEL_PATH}"); return
    model = PPO.load(MODEL_PATH, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    combos = [(ns, dp, dens) for ns, dp in itertools.product(noise_levels, dropout_probs) for dens in DENSITIES]
    if start_idx is not None and end_idx is not None:
        combos = combos[start_idx:end_idx]
        print(f"[*] subset combos {start_idx}:{end_idx} ({len(combos)}) | {n_maps} maps/combo")
    else:
        print(f"[*] full sweep ({len(combos)} combos) | {n_maps} maps/combo")

    results = []
    for ns, dp, dens in combos:
        res = evaluate(model, ns, dp, dens, n_maps)
        results.append(res)
        print(f"[*] noise={ns} dropout={dp} d={dens:.2f}: "
              f"success {res['success']:.2f}% | timeout {res['timeout']:.2f}% | coll {res['collision']:.2f}%")

    csv_path = os.path.join(RESULTS_DIR, "comm_robustness.csv")
    df_new = pd.DataFrame(results)
    if os.path.exists(csv_path):
        df_new = pd.concat([pd.read_csv(csv_path), df_new], ignore_index=True)
    df_new.to_csv(csv_path, index=False)
    print(f"\n[OK] saved: {csv_path}")
    print("Expectation: graceful degradation (no cliff) -> LiDAR-grounded, not fragilely comm-dependent.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comm-robustness sweep (comm-only perturbation, slicing).")
    parser.add_argument("--start_idx", type=int, default=None, help="Start index of combo slice (inclusive)")
    parser.add_argument("--end_idx", type=int, default=None, help="End index of combo slice (exclusive)")
    parser.add_argument("--n_maps", type=int, default=200, help="Maps per combo (use 50 for a quick test)")
    args = parser.parse_args()
    main(start_idx=args.start_idx, end_idx=args.end_idx, n_maps=args.n_maps)
