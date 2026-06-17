"""
STAGE 0 — GEOMETRY PRE-GATE (no training).

Question: if we shorten LiDAR below comm range, do drones ACTUALLY have neighbors in the
"comm-only" annulus  (lidar_range < distance <= comm_range)  during real episodes?
Only those neighbors carry NON-REDUNDANT information a trust mechanism could later defend.
If the annulus is almost always empty, comm cannot help regardless of retraining -> stop.

Method: roll out M0 on solvable maps (no adversary — this gate is about navigation value),
and for a grid of candidate thresholds (lidar x comm), measure per drone-step:
  - % of drone-steps with >= 1 neighbor in the annulus,
  - mean # of neighbors in the annulus,
  - mean # of the NEAREST-5 neighbors that fall in the annulus (the ones that matter most).

CAVEAT (printed): geometry is measured under M0's spacing (normal 12 m LiDAR), a PROXY for the
short-LiDAR regime. It bounds OPPORTUNITY, not learned use — the Stage 3 ablation is the real test.

Usage:
    python probe_comm_geometry.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
Args: [model_path] [n_episodes_per_density]
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
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
EPISODES_PER_DENSITY = 30
LIDAR_CANDS = [4.0, 5.0, 6.0]     # candidate (short) sensing ranges
COMM_CANDS = [8.0, 10.0, 12.0]    # candidate communication ranges (>= sensing)


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
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_eps = int(sys.argv[2]) if len(sys.argv) > 2 else EPISODES_PER_DENSITY
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] GEOMETRY PRE-GATE | model={model_path} | episodes/density={n_eps}")
    print(f"    lidar candidates={LIDAR_CANDS}  comm candidates={COMM_CANDS}")
    print("    (M0-spacing PROXY: bounds opportunity, not learned use; Stage 3 ablation is the real test)")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    # accumulators keyed by (density, lidar, comm)
    pairs = [(li, co) for li in LIDAR_CANDS for co in COMM_CANDS if co > li]
    rows = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density)  # default 12 m LiDAR, 8 m comm
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
        n_samples = 0
        # per pair: [steps_with_ge1_in_annulus, total_in_annulus, total_near5_in_annulus]
        acc = {p: np.zeros(3, dtype=np.float64) for p in pairs}

        for ep in range(n_eps):
            attempts = 0
            while True:
                seed = 800_000_000 + int(density * 100) * 10_000 + ep + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                    break
                attempts += 1

            finished = set(); done = False
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                # --- geometry over every active drone (no adversary) ---
                idxs = [amap[a] for a in env.agents]
                for i in idxs:
                    pos_i = env.positions[i]
                    others = np.array(sorted(np.linalg.norm(pos_i - env.positions[j]) for j in idxs if j != i))
                    if others.size == 0:
                        continue
                    n_samples += 1
                    near5 = others[:5]
                    for (li, co) in pairs:
                        in_ann = int(np.sum((others > li) & (others <= co)))
                        near5_ann = int(np.sum((near5 > li) & (near5 <= co)))
                        acc[(li, co)][0] += 1 if in_ann > 0 else 0
                        acc[(li, co)][1] += in_ann
                        acc[(li, co)][2] += near5_ann

                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {a: act[k] for k, a in enumerate(active)}
                obs_dict, _, terms, truncs, _ = env.step(action)
                for a in active:
                    if terms.get(a, False) or truncs.get(a, False):
                        finished.add(a)
                if not env.agents:
                    done = True
        env.close()

        s = max(n_samples, 1)
        print(f"\n[DENSITY {density:.2f}]  ({n_samples} drone-step samples)")
        print(f"  {'lidar':>5} {'comm':>5} | {'%steps annulus>=1':>17} | {'mean #in annulus':>16} | {'mean nearest5 in annulus':>24}")
        for (li, co) in pairs:
            pct = 100.0 * acc[(li, co)][0] / s
            mean_in = acc[(li, co)][1] / s
            mean_n5 = acc[(li, co)][2] / s
            print(f"  {li:>5.1f} {co:>5.1f} | {pct:>16.1f}% | {mean_in:>16.3f} | {mean_n5:>24.3f}")
            rows.append({"density": density, "lidar_range": li, "comm_range": co,
                         "pct_steps_annulus_ge1": pct, "mean_in_annulus": mean_in,
                         "mean_nearest5_in_annulus": mean_n5, "n_samples": n_samples})

    out_dir = os.path.join("Phase_CD", "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "comm_geometry.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 70)
    print("DECISION (bring to Claude — REVIEW CHECKPOINT 0):")
    print("  pick the (lidar, comm) pair with HIGH 'mean nearest5 in annulus' (the comm-only neighbors")
    print("  that matter) AND a sensor-citable lidar (~3-5 m). High occupancy -> comm CAN carry")
    print("  non-redundant info -> proceed to retrain. ~0 occupancy everywhere -> comm cannot help -> stop.")
    print("=" * 70)


if __name__ == "__main__":
    main()
