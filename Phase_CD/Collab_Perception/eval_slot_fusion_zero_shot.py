"""
Zero-shot slot-fusion ON/OFF eval on M0 (no retraining).

Runs M0 on the raster env with slot_fusion=True, comparing:
  - ON: use_shared_map=True (slot fusion active)
  - OFF: use_shared_map=False (own LiDAR only; blind -> empty)

At the real gate regime: lidar=8m, dropout=0.20, density=0.20/0.30.
Returns 650-d obs (no expansion, M0 compatible).

Usage:
    python eval_slot_fusion_zero_shot.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 200
Args: [model_path] [n_maps]
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_raster import SwarmLidarEnv_Raster
import torch.nn as nn


class MAPPO_Extractor_M0(nn.Module):
    """Custom CTDE extractor for M0 (650-d): actor reads [:130], critic reads [130:520]."""
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        LOCAL = 130
        GLOBAL = 520
        # Actor: 130-d local
        pi_layers, last = [], LOCAL
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        # Critic: 520-d global
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f):
        return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])

    def forward_actor(self, f):
        return self.policy_net(f[:, :130])

    def forward_critic(self, f):
        return self.value_net(f[:, 130:])


class MAPPO_Policy_M0(ActorCriticPolicy):
    """Policy class for loading M0 with custom CTDE extractor."""
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_M0(self.features_dim, self.net_arch, self.activation_fn)


def run_eval(model, use_shared_map, n_maps=200):
    """Run eval with slot-fusion at realistic dropout regime (8m lidar, dropout=0.10, sustain=5 ≈ 33% blind).

    Returns: (success_rate, per_map_successes)
    """
    env = SwarmLidarEnv_Raster(
        render_mode=None,
        target_density=0.20,
        communication_range=10.0,
        congestion_mode="lidar",
        lidar_range=8.0,
        lidar_dropout=0.10,           # Realistic: 10% per-step chance
        dropout_sustain=5,             # Realistic: 5-step sustained (33% blind overall)
        use_shared_map=use_shared_map,
        probe_lidar_slot=False,
        slot_fusion=True,  # Unified _cast48 over union at 8m scale
        straight_line_goal=False
    )
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    reached = total = 0
    per_map_results = []  # Track per-map success (1 if all drones reached, 0 else)

    print(f"[*] Evaluating slot_fusion={'ON' if use_shared_map else 'OFF'}: {n_maps} maps...")
    for map_idx in range(n_maps):
        attempts = 0
        while True:
            seed = 800_000_000 + int(0.20 * 100) * 10_000 + map_idx + attempts * 5_000
            obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
            if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                break
            attempts += 1

        map_reached = 0
        map_total = 0
        finished = set()
        done = False
        while not done:
            active = [a for a in obs_dict.keys() if a not in finished]
            if not active:
                break
            obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
            act, _ = model.predict(obs_batch, deterministic=True)
            action = {a: act[k] for k, a in enumerate(active)}
            obs_dict, _, terms, truncs, infos = env.step(action)

            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a)
                    total += 1
                    map_total += 1
                    if infos[a].get("cause") == "success":
                        reached += 1
                        map_reached += 1

            if not env.agents:
                done = True

        # Per-map success: 1 if all drones on this map succeeded, 0 else
        map_success = 1.0 if (map_total > 0 and map_reached == map_total) else 0.0
        per_map_results.append(map_success)

        if (map_idx + 1) % 50 == 0:
            print(f"  ... {map_idx + 1}/{n_maps}")

    env.close()
    success_rate = 100.0 * reached / max(total, 1)
    return success_rate, np.array(per_map_results)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand
                break

    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}")
        return

    print(f"[*] Slot-fusion ON/OFF eval | M0: {os.path.basename(model_path)} | regime: 8m LiDAR, dropout=0.10/sustain=5 (≈33% blind)")
    print(f"    Loading model...")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")

    # ON: slot fusion with shared map
    success_on, results_on = run_eval(model, use_shared_map=True, n_maps=n_maps)

    # OFF: own LiDAR only
    success_off, results_off = run_eval(model, use_shared_map=False, n_maps=n_maps)

    # Per-map success rates
    n_maps_actual = len(results_on)
    permap_on  = 100.0 * np.mean(results_on)
    permap_off = 100.0 * np.mean(results_off)
    diff_drone  = success_on - success_off
    diff_permap = permap_on - permap_off

    # Bootstrap 95% CI — two paired series, resampled over maps
    np.random.seed(42)
    n_bootstrap = 10000
    drone_diffs_boot   = []
    permap_diffs_boot  = []

    # Need per-map drone counts to bootstrap drone-level metric
    # Approximate: drone-level rate bootstrapped as mean of per-map rates scaled by total drones
    # Exact approach: store (reached, total) per map
    # Simple & valid: bootstrap on per-map binary for permap CI;
    # for drone CI, treat each map's contribution as (map_reached/map_total)*100 averaged
    # We already have per-map binary in results_on/off. For drone-level CI we need per-map rates.
    # Re-derive per-map drone success rates from run_eval output (binary 0/1 per map is not enough).
    # Instead run bootstrap only on the per-map binary (the statistically cleaner metric).
    # Drone-level CI: reported without CI (it aggregates across maps, harder to bootstrap without per-map counts).

    for _ in range(n_bootstrap):
        idx_boot = np.random.choice(n_maps_actual, size=n_maps_actual, replace=True)
        permap_diffs_boot.append(
            100.0 * np.mean(results_on[idx_boot]) - 100.0 * np.mean(results_off[idx_boot])
        )

    permap_diffs_boot = np.array(permap_diffs_boot)
    pm_ci_lo = np.percentile(permap_diffs_boot, 2.5)
    pm_ci_hi = np.percentile(permap_diffs_boot, 97.5)

    print(f"\n[RESULTS]")
    print(f"  ── 1. Drone-level success (per individual drone) ──────────────")
    print(f"     ON  (slot fusion + shared):  {success_on:6.2f}%")
    print(f"     OFF (own LiDAR only):        {success_off:6.2f}%")
    print(f"     Difference (ON - OFF):       {diff_drone:+6.2f} pp")
    print(f"  ── 2. Map-level success (all 10 drones reached goal) ──────────")
    print(f"     ON  per-map:                 {permap_on:6.2f}%")
    print(f"     OFF per-map:                 {permap_off:6.2f}%")
    print(f"     Difference (ON - OFF):       {diff_permap:+6.2f} pp")
    print(f"     95% CI on difference:        [{pm_ci_lo:+6.2f}, {pm_ci_hi:+6.2f}] pp")
    print(f"\n[INTERPRETATION]  (based on map-level CI)")
    if pm_ci_lo > 0 and diff_permap > 10.0:
        print(f"  ✓ LARGE EFFECT & statistically significant (CI > 0).")
        print(f"    Slot-fusion validates. Ready to train ON/OFF curricula.")
    elif pm_ci_lo > 0:
        print(f"  ✓ Statistically significant (CI > 0) but effect modest.")
        print(f"    Training may amplify the signal.")
    else:
        print(f"  ✗ Not statistically significant (CI includes 0) or negative.")
        print(f"    Consider architecture changes or pivot to OPTION_1.")


if __name__ == "__main__":
    main()
