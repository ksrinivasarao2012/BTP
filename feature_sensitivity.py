"""
Feature-sensitivity test: which parts of the observation does the policy
actually USE? Perturb (zero) each feature group on real observations and
measure the resulting change in the deterministic action.

High mean |dAction| => policy relies on that feature group.
Near-zero        => policy effectively ignores it.

This tells us why comm range (3 vs 8) barely matters: the load-bearing
features are the UNGATED ones (LiDAR / congestion), not the comm-gated ones.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

# local-block feature groups (indices within the 130-dim actor input)
GROUPS = {
    "ego_velocity      [0:2]":   (0, 2),
    "dijkstra_dir      [2:4]":   (2, 4),
    "dijkstra_dist     [4:5]":   (4, 5),
    "yaw               [5:6]":   (5, 6),
    "LiDAR             [6:54]":  (6, 54),
    "obs_neighbors(gated)[54:99]": (54, 99),
    "congestion        [99:100]": (99, 100),
    "sync(gated)       [100:120]": (100, 120),
    "trajectory        [120:130]": (120, 130),
}


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
    # Optional CLI: python feature_sensitivity.py <model_path> <comm_range>
    # Defaults reproduce the original comm=8 test.
    default_paths = ["models/apex_ultra_glide_v14_8_0m_final.zip",
                     "models/apex_ultra_glide_v14_final.zip"]
    path = sys.argv[1] if len(sys.argv) > 1 else next((p for p in default_paths if os.path.exists(p)), None)
    comm = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    if path is None or not os.path.exists(path):
        print(f"Model not found: {path}"); return
    print(f"[*] model: {path}")
    print(f"[*] eval communication_range: {comm}")
    model = PPO.load(path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    # collect real observations from a rollout (at the given comm range)
    env = SwarmLidarEnv_StepB10_8_0m(target_density=0.25, communication_range=comm)
    obs_dict, _ = env.reset(seed=123)
    obs_buffer = []
    finished, steps = set(), 0
    while obs_dict and steps < 150:
        active = [a for a in obs_dict.keys() if a not in finished]
        if not active:
            break
        for a in active:
            obs_buffer.append(obs_dict[a].astype(np.float32))
        act, _ = model.predict(np.array([obs_dict[a] for a in active]), deterministic=True)
        action = {a: act[k] for k, a in enumerate(active)}
        obs_dict, _, terms, truncs, _ = env.step(action)
        for a in active:
            if terms.get(a, False) or truncs.get(a, False):
                finished.add(a)
        steps += 1

    O = np.array(obs_buffer)  # (N, 650)
    N = len(O)
    base_actions, _ = model.predict(O, deterministic=True)

    print(f"\n[*] {N} real observations collected")
    print("=" * 64)
    print(f"{'feature group (zeroed)':<30}{'mean |dAction|':>16}{'max |dAction|':>16}")
    print("-" * 64)
    results = []
    for name, (lo, hi) in GROUPS.items():
        P = O.copy()
        P[:, lo:hi] = 0.0
        acts, _ = model.predict(P, deterministic=True)
        d = np.abs(acts - base_actions)
        results.append((name, d.mean(), d.max()))
    for name, m, mx in sorted(results, key=lambda r: -r[1]):
        print(f"{name:<30}{m:>16.4f}{mx:>16.4f}")
    print("=" * 64)
    print("Interpretation: large mean |dAction| = policy RELIES on that group;")
    print("near-zero = policy effectively IGNORES it.")
    print("If LiDAR/congestion >> obs_neighbors/sync, that explains 3m == 8m:")
    print("the load-bearing features are UNGATED by communication range.")


if __name__ == "__main__":
    main()
