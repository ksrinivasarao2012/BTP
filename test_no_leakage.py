"""
Rigorous data-leakage test for evaluation.

The observation vector is 650-dim: [0:130] = LOCAL (actor), [130:650] = GLOBAL
(critic-only). If the policy is CTDE-correct, the action must depend ONLY on the
local [0:130] block and be COMPLETELY invariant to the global [130:650] block.

Test:
  1. Randomize ONLY the global block [130:650] -> action must NOT change (no leak).
  2. Randomize ONLY the local block [0:130]    -> action SHOULD change (sanity).
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m


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
    paths = [
        "models/apex_ultra_glide_v14_8_0m_final.zip",
        "models/apex_ultra_glide_v14_final.zip",
    ]
    model_path = next((p for p in paths if os.path.exists(p)), None)
    if model_path is None:
        print("No model found."); return
    print(f"[*] model: {model_path}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    env = SwarmLidarEnv_StepB10_8_0m(target_density=0.25, communication_range=8.0)
    obs_dict, _ = env.reset(seed=123)
    rng = np.random.default_rng(0)

    # Roll out a real episode; at every step test global-invariance on REAL obs,
    # and collect the real actions to prove the actor is input-sensitive.
    max_global_diff = 0.0
    real_actions = []
    finished = set()
    steps = 0
    while obs_dict and steps < 120:
        active = [a for a in obs_dict.keys() if a not in finished]
        if not active:
            break
        for ag in active:
            obs = obs_dict[ag].astype(np.float32)
            a0, _ = model.predict(obs, deterministic=True)
            real_actions.append(a0)
            # randomize ONLY the global block, several times, on this REAL obs
            for _ in range(5):
                o = obs.copy()
                o[130:] = rng.normal(0, 3, size=520).astype(np.float32)
                a, _ = model.predict(o, deterministic=True)
                max_global_diff = max(max_global_diff, float(np.max(np.abs(a - a0))))

        act, _ = model.predict(np.array([obs_dict[a] for a in active]), deterministic=True)
        action = {a: act[k] for k, a in enumerate(active)}
        obs_dict, _, terms, truncs, _ = env.step(action)
        for a in active:
            if terms.get(a, False) or truncs.get(a, False):
                finished.add(a)
        steps += 1

    real_actions = np.array(real_actions)
    action_spread = float(np.max(real_actions, axis=0).max() - np.min(real_actions, axis=0).min())
    action_std = float(real_actions.std())

    print("\n" + "=" * 64)
    print(f"samples tested: {len(real_actions)} real (drone,step) observations")
    print(f"TEST 1  max action change when GLOBAL [130:650] randomized : {max_global_diff:.3e}")
    print(f"SANITY  spread of real actions across rollout             : {action_spread:.3e}")
    print(f"SANITY  std of real actions across rollout                : {action_std:.3e}")
    print("=" * 64)
    if max_global_diff < 1e-6 and action_std > 1e-6:
        print("RESULT: PASS -> actions vary with LOCAL input but are PERFECTLY")
        print("        invariant to GLOBAL state. No data leakage in evaluation.")
    elif max_global_diff >= 1e-6:
        print("RESULT: FAIL -> actor responds to global state. LEAKAGE PRESENT.")
    else:
        print("RESULT: INCONCLUSIVE -> actions constant across rollout (check model).")


if __name__ == "__main__":
    main()
