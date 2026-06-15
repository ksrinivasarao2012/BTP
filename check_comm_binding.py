"""
Communication-binding diagnostic for the 8.0m model.

Answers the key question for the paper:
  Does the 8.0m communication limit actually BIND during episodes,
  or do drones always stay within 8m (making the experiment vacuous)?

It rolls out the trained v14_8.0m policy and, at every timestep for every
active drone, measures how many neighbors fall OUTSIDE the 8m range, and
whether any of the 5 NEAREST neighbors are out of range.

Usage:
    python check_comm_binding.py
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

COMM_RANGE = 8.0
DENSITIES = [0.20, 0.30]
EPISODES_PER_DENSITY = 20


# --- policy classes (must match training architecture) ---
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


def load_model():
    paths = [
        os.path.join("models", "apex_ultra_glide_v14_8_0m_final.zip"),
        os.path.join("v14_8_0m", "models", "apex_ultra_glide_v14_8_0m_final.zip"),
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"[*] Loading model: {p}")
            return PPO.load(p, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    print(f"[!] Model not found in {paths}")
    sys.exit(1)


def main():
    model = load_model()

    print("\n" + "=" * 66)
    print("  COMMUNICATION-BINDING DIAGNOSTIC (range = 8.0 m)")
    print("=" * 66)

    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density)

        # accumulators over all (drone, step) samples
        n_samples = 0
        sum_others = 0          # active other drones visible in principle
        sum_in_range = 0        # within 8m
        sum_out_range = 0       # beyond 8m
        binds = 0               # samples with >=1 neighbor out of range
        near5_out_any = 0       # samples with >=1 of nearest-5 out of range
        sum_near5_out = 0       # total count of nearest-5 that are out of range

        for ep in range(EPISODES_PER_DENSITY):
            # solvable map, same seed scheme family as the sweeps
            attempts = 0
            while True:
                seed = 700_000_000 + int(density * 100) * 10_000 + ep + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                ok = all(env._is_map_solvable(start_pos=env.positions[env.agent_name_mapping[a]])
                         for a in env.possible_agents)
                if ok:
                    break
                attempts += 1

            finished = set()
            done = False
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break

                # ---- measure geometry for every active drone ----
                idxs = [env.agent_name_mapping[a] for a in env.agents]
                for i in idxs:
                    pos_i = env.positions[i]
                    others = [np.linalg.norm(pos_i - env.positions[j]) for j in idxs if j != i]
                    if not others:
                        continue
                    others.sort()
                    in_r = sum(1 for d in others if d <= COMM_RANGE)
                    out_r = len(others) - in_r
                    near5 = others[:5]
                    near5_out = sum(1 for d in near5 if d > COMM_RANGE)

                    n_samples += 1
                    sum_others += len(others)
                    sum_in_range += in_r
                    sum_out_range += out_r
                    binds += 1 if out_r > 0 else 0
                    near5_out_any += 1 if near5_out > 0 else 0
                    sum_near5_out += near5_out

                # ---- step the policy ----
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
        print(f"\n[DENSITY {density:.2f}]  ({n_samples} drone-step samples over {EPISODES_PER_DENSITY} episodes)")
        print(f"  mean active neighbors            : {sum_others / s:.2f}")
        print(f"  mean IN-range (<=8m)             : {sum_in_range / s:.2f}")
        print(f"  mean OUT-of-range (>8m)          : {sum_out_range / s:.2f}")
        print(f"  % drone-steps gate BINDS (>=1 out): {100.0 * binds / s:.1f}%")
        print(f"  % drone-steps a NEAREST-5 is out  : {100.0 * near5_out_any / s:.1f}%")
        print(f"  mean # of nearest-5 out of range  : {sum_near5_out / s:.3f}")

    print("\n" + "=" * 66)
    print("  INTERPRETATION")
    print("  - 'gate BINDS' high + 'nearest-5 out' LOW  -> robustness result (good):")
    print("        8m discards only distant neighbors; the critical nearest-5 stay in range.")
    print("  - 'gate BINDS' near 0%                      -> experiment is vacuous (8m never restricts).")
    print("=" * 66)


if __name__ == "__main__":
    main()
