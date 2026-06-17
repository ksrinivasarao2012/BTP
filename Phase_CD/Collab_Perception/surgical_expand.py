"""
STAGE A1 — Transfer surgery: expand M0's actor input 130 -> 157 (zero-init the 27 new hazard
weights) so the expanded model is BEHAVIOURALLY IDENTICAL to M0 (hazard block contributes 0),
then learns to use shared hazards during Stage-A2 training.

Only ONE weight changes: mlp_extractor.policy_net.0.weight  [h,130] -> [h,157] (cols 130:157 = 0).
Everything else (rest of policy_net, value_net, action head, value head, log_std) is copied verbatim.

Usage:
    python surgical_expand.py [m0_path] [out_path]
Defaults: models/apex_ultra_glide_v14_comm8_lidar_final.zip -> models/collab_expanded_M0.zip
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import torch
import torch.nn as nn
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
# this file lives 2 levels deep: Phase_CD/Collab_Perception/  -> repo root is two dirnames up
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

LOCAL_OLD = 130          # M0 actor-local width
LOCAL_NEW = 157          # + 27 shared-hazard dims
GLOBAL = 520             # critic width (unchanged)
OBS_NEW = LOCAL_NEW + GLOBAL   # 677
M0_DEFAULT = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
OUT_DEFAULT = "models/collab_expanded_M0.zip"
EXPAND_KEY = "mlp_extractor.policy_net.0.weight"


# --- OLD policy (M0): actor on f[:, :130], critic on f[:, 130:] ---
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


# --- NEW policy (Design A): actor on f[:, :157], critic on f[:, 157:] ---
class MAPPO_Extractor_Collab(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], LOCAL_NEW
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :LOCAL_NEW]), self.value_net(f[:, LOCAL_NEW:])
    def forward_actor(self, f): return self.policy_net(f[:, :LOCAL_NEW])
    def forward_critic(self, f): return self.value_net(f[:, LOCAL_NEW:])


class MAPPO_Policy_Collab(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_Collab(self.features_dim, self.net_arch, self.activation_fn)


class _Stub(gym.Env):
    """Minimal env to instantiate the new policy with the right (677-d obs, 2-d action) spaces."""
    def __init__(self):
        self.observation_space = spaces.Box(-np.inf, np.inf, (OBS_NEW,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (2,), np.float32)

    def reset(self, *, seed=None, options=None):
        return np.zeros(OBS_NEW, np.float32), {}

    def step(self, action):
        return np.zeros(OBS_NEW, np.float32), 0.0, False, False, {}


def main():
    m0_path = sys.argv[1] if len(sys.argv) > 1 else M0_DEFAULT
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT_DEFAULT
    if not os.path.exists(m0_path):
        for cand in (os.path.join("models", os.path.basename(m0_path)), os.path.abspath(m0_path)):
            if os.path.exists(cand):
                m0_path = cand; break
    if not os.path.exists(m0_path):
        print(f"[!] M0 not found: {m0_path}"); return

    print(f"[*] loading M0: {m0_path}")
    m0 = PPO.load(m0_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    net_arch = m0.policy.net_arch
    act_fn = m0.policy.activation_fn
    print(f"    net_arch={net_arch}  activation={getattr(act_fn,'__name__',act_fn)}")

    new = PPO(MAPPO_Policy_Collab, _Stub(),
              policy_kwargs={"net_arch": net_arch, "activation_fn": act_fn}, device="cpu")

    m0_sd = m0.policy.state_dict()
    new_sd = new.policy.state_dict()
    copied = expanded = 0
    mismatched = []
    for k in list(new_sd.keys()):
        if k == EXPAND_KEY and k in m0_sd:
            w = torch.zeros_like(new_sd[k])
            w[:, :LOCAL_OLD] = m0_sd[k]            # copy M0's 130 input weights; cols 130:157 stay 0
            new_sd[k] = w; expanded += 1
        elif k in m0_sd and m0_sd[k].shape == new_sd[k].shape:
            new_sd[k] = m0_sd[k].clone(); copied += 1
        else:
            mismatched.append((k, tuple(new_sd[k].shape), tuple(m0_sd[k].shape) if k in m0_sd else None))
    new.policy.load_state_dict(new_sd)

    # verification
    sd = new.policy.state_dict()
    ok_copy = torch.allclose(sd[EXPAND_KEY][:, :LOCAL_OLD], m0_sd[EXPAND_KEY])
    ok_zero = int(torch.count_nonzero(sd[EXPAND_KEY][:, LOCAL_OLD:])) == 0
    print(f"[*] copied {copied} tensors verbatim | expanded {expanded} ({EXPAND_KEY})")
    print(f"    first-130 cols == M0: {ok_copy} | new 27 cols all zero: {ok_zero}")
    if mismatched:
        print(f"    [!] UNEXPECTED mismatched keys (should be empty): {mismatched}")
    if not (ok_copy and ok_zero and expanded == 1 and not mismatched):
        print("[!] surgery sanity FAILED — do not use this model."); return

    new.save(out_path)
    print(f"\n[OK] expanded model saved: {out_path}")
    print("    Next (A1 sanity): eval_collab.py on this model @ lidar=12 must reproduce M0 (~92/95).")


if __name__ == "__main__":
    main()
