"""
LIDAR-8m ADVERSARIAL IMPACT PROBE.

Tests M0 zero-shot at lidar_range=8m (instead of its trained 12m) under:
  - no adversary  -> new baseline at lidar=8m
  - f=2 rammers   -> adversarial drop at lidar=8m

Compares against known lidar=12m results to decide whether 8m LiDAR preserves
enough adversarial impact to justify the Collab_Perception paper's threat model.

Known lidar=12m results (M0):
  no adversary:  95.55 / 91.10
  f=2 rammers:   77.38 / 73.50   drop = -18.17 / -17.60 pp

Decision rule:
  8m drop >= ~12 pp at both densities  ->  8m LiDAR is fine; proceed with plan
  8m drop <  ~8  pp                   ->  adversarial impact too small; investigate

Usage:
    python probe_lidar8_ram.py            # no adversary + f=2 rammers, 30 maps (quick)
    python probe_lidar8_ram.py 200        # full 200-map run
Args: [n_maps]
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

_ROOT = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.join(_ROOT, "Phase_CD")
if _PHASE_CD not in sys.path:
    sys.path.insert(0, _PHASE_CD)
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m  # lidar_range param (pristine env lacks it)

DENSITIES   = [0.20, 0.30]
MODEL_PATH  = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM        = 8.0
LIDAR_TEST  = 8.0          # the range we are probing
F_RAMMERS   = 2
CONGESTION_MODE = "lidar"

# Known M0 @ lidar=12m reference (for printed comparison only)
REF_BASELINE = {0.20: 95.55, 0.30: 91.10}
REF_RAM_F2   = {0.20: 77.38, 0.30: 73.50}


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

    def forward(self, f):        return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f):  return self.policy_net(f[:, :130])
    def forward_critic(self, f): return self.value_net(f[:, 130:])


class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)


def run_condition(model, n_maps, density, f_rammers, lidar_range):
    """Run one condition. Returns dict of metrics."""
    traitors = set(range(f_rammers))
    env = SwarmLidarEnv_StepB10_8_0m(
        render_mode=None, target_density=density,
        communication_range=COMM, congestion_mode=CONGESTION_MODE,
        lidar_range=lidar_range
    )
    if f_rammers > 0:
        env.traitor_indices = traitors
        env.traitor_behavior = "ram"
        env.deception_mode   = "none"

    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    h_reached = h_timeout = h_coll = h_drone = h_total = 0

    for map_idx in range(n_maps):
        attempts = 0
        while True:
            seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
            obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
            if all(env._is_map_solvable(start_pos=env.positions[amap[a]])
                   for a in env.possible_agents):
                break
            attempts += 1

        finished = set(); done = False
        while not done:
            active = [a for a in obs_dict.keys() if a not in finished]
            if not active:
                break
            obs_batch = np.array([obs_dict[a] for a in active])
            act, _   = model.predict(obs_batch, deterministic=True)
            action   = {a: act[k] for k, a in enumerate(active)}
            obs_dict, _, terms, truncs, infos = env.step(action)
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a)
                    idx = amap[a]
                    if f_rammers > 0 and idx in traitors:
                        continue          # traitors excluded from honest_success
                    h_total += 1
                    cause = infos[a].get("cause")
                    if   cause == "success":   h_reached += 1
                    elif cause == "timeout":   h_timeout += 1
                    elif cause == "collision":
                        h_coll += 1
                        if infos[a].get("collision_type") == "drone":
                            h_drone += 1
            if not env.agents:
                done = True
    env.close()

    denom = max(h_total, 1)
    return {
        "density":       density,
        "f":             f_rammers,
        "lidar":         lidar_range,
        "honest_success":       round(100.0 * h_reached / denom, 2),
        "honest_timeout":       round(100.0 * h_timeout / denom, 2),
        "honest_collision":     round(100.0 * h_coll    / denom, 2),
        "honest_drone_coll":    round(100.0 * h_drone   / denom, 2),
    }


def main():
    n_maps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    if not os.path.exists(MODEL_PATH):
        print(f"[!] model not found: {MODEL_PATH}"); return

    print(f"[*] LIDAR-8m RAM PROBE  |  model=M0  |  lidar={LIDAR_TEST}m  |  maps={n_maps}")
    print(f"[*] Note: M0 was trained at lidar=12m - this is a zero-shot distribution-shift test.")
    print(f"[*] Compares no-adversary vs f={F_RAMMERS} rammers at lidar={LIDAR_TEST}m.\n")
    model = PPO.load(MODEL_PATH, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    rows = []
    for density in DENSITIES:
        print(f"-- density={density:.2f} -------------------------------------")

        # Condition A: no adversary at lidar=8m
        r_base = run_condition(model, n_maps, density, f_rammers=0, lidar_range=LIDAR_TEST)
        rows.append(r_base)
        print(f"  no adversary  (lidar=8m):  success {r_base['honest_success']:6.2f}%  "
              f"coll {r_base['honest_collision']:5.2f}%  drone-coll {r_base['honest_drone_coll']:5.2f}%")
        print(f"  [ref lidar=12m no-adv]:            {REF_BASELINE[density]:.2f}%")
        print(f"  distribution-shift drop:           {r_base['honest_success'] - REF_BASELINE[density]:+.2f} pp\n")

        # Condition B: f=2 rammers at lidar=8m
        r_ram = run_condition(model, n_maps, density, f_rammers=F_RAMMERS, lidar_range=LIDAR_TEST)
        rows.append(r_ram)
        drop_8m  = r_ram['honest_success'] - r_base['honest_success']
        drop_12m = REF_RAM_F2[density] - REF_BASELINE[density]
        print(f"  f=2 rammers   (lidar=8m):  success {r_ram['honest_success']:6.2f}%  "
              f"coll {r_ram['honest_collision']:5.2f}%  drone-coll {r_ram['honest_drone_coll']:5.2f}%")
        print(f"  adversarial drop @ lidar=8m:       {drop_8m:+.2f} pp")
        print(f"  adversarial drop @ lidar=12m (ref):{drop_12m:+.2f} pp")
        print()

    # Save
    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "probe_lidar8_ram.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[OK] saved: {out}")

    # Decision
    print("\n" + "=" * 68)
    print("DECISION RULE")
    print("  8m adversarial drop >= ~12 pp (both densities)")
    print("  -> ramming is still a serious threat at 8m LiDAR")
    print("  -> 8m plan is scientifically valid; proceed with training")
    print()
    print("  8m adversarial drop < ~8 pp")
    print("  -> drones are already damaged by distribution shift;")
    print("     ramming barely adds more -> adversarial story weakens")
    print("  -> consider retraining M0 at 8m first before this decision")
    print("=" * 68)


if __name__ == "__main__":
    main()
