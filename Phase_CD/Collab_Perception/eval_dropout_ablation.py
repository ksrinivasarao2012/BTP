"""
Dropout sweep — SINGLE-POLICY INFORMATION ABLATION (matches tab:anchor construction).

Unlike eval_dropout_sweep.py (which compares an ON-trained vs an OFF-trained model),
this runs ONE model with use_shared_map toggled on/off, exactly like the anchor
(eval_slot_fusion_zero_shot.py). Same weights on both arms -> the ON-OFF gap is
attributable to the shared information alone, and the 10% (~33% blind) row reproduces
the anchor's ON/OFF cell by construction (same model, density, seeds, env config).

Purpose: makes tab:dropout use the SAME construction as tab:anchor so the two tables
reconcile cell-for-cell (finding #2, BASELINE_NUMBERS_RECONCILIATION.md).

  dropout=0%  -> blind 0%   (no failure)
  dropout=10% -> blind ~33% (== anchor operating point)
  dropout=20% -> blind ~50% (stress)

Usage:
    python eval_dropout_ablation.py [model_path] [n_maps] [density] [n_workers]
    python eval_dropout_ablation.py models/raster_slot_fusion_OFF_stage2_final.zip 500 0.27 10
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
import torch.nn as nn

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_raster import SwarmLidarEnv_Raster

LOCAL  = 130
GLOBAL = 520

# (dropout, sustain, dropout_label, blind_label)
SWEEP = [
    (0.00, 5, "0%",  " 0%"),
    (0.10, 5, "10%", "33%"),
    (0.20, 5, "20%", "50%"),
]

DEFAULT_MODEL = "models/raster_slot_fusion_OFF_stage2_final.zip"


class MAPPO_Extractor_M0(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], LOCAL
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f):
        return self.policy_net(f[:, :LOCAL]), self.value_net(f[:, LOCAL:])

    def forward_actor(self, f):
        return self.policy_net(f[:, :LOCAL])

    def forward_critic(self, f):
        return self.value_net(f[:, LOCAL:])


class MAPPO_Policy_M0(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_M0(self.features_dim, self.net_arch, self.activation_fn)


from multiprocessing import Pool

_G = {}


def _init(model_path, density):
    # SINGLE model, used on BOTH arms (the ablation). use_shared_map is the only thing toggled.
    _G["model"] = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    _G["density"] = density
    _G["envs"] = {}


def _get_env(dropout, sustain, use_shared):
    key = (dropout, sustain, use_shared)
    if key not in _G["envs"]:
        _G["envs"][key] = SwarmLidarEnv_Raster(
            render_mode=None, target_density=_G["density"], communication_range=10.0,
            congestion_mode="lidar", lidar_range=8.0,
            lidar_dropout=dropout, dropout_sustain=sustain,
            use_shared_map=use_shared, probe_lidar_slot=False,
            slot_fusion=True, straight_line_goal=False)
    return _G["envs"][key]


def _run(task):
    """(level_idx, dropout, sustain, use_shared, map_idx) -> (level_idx, use_shared, map_idx, drone_rate)."""
    level_idx, dropout, sustain, use_shared, map_idx = task
    model = _G["model"]                                  # SAME model regardless of arm
    env, density = _get_env(dropout, sustain, use_shared), _G["density"]
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    attempts = 0
    while True:
        seed = 800_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
        obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
        if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
            break
        attempts += 1
    map_reached = map_total = 0
    finished = set()
    while True:
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
                map_total += 1
                if infos[a].get("cause") == "success":
                    map_reached += 1
        if not env.agents:
            break
    return level_idx, use_shared, map_idx, (map_reached / map_total if map_total > 0 else 0.0)


def bootstrap_ci(on_rates, off_rates, n_bootstrap=10000, seed=42):
    np.random.seed(seed)
    n = len(on_rates)
    diffs = [
        100.0 * float(np.mean(on_rates[idx]) - np.mean(off_rates[idx]))
        for idx in (np.random.choice(n, size=n, replace=True) for _ in range(n_bootstrap))
    ]
    diffs = np.array(diffs)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def resolve_path(path):
    if os.path.exists(path):
        return path
    for cand in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(cand):
            return cand
    return None


def main():
    model_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps    = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    density   = float(sys.argv[3]) if len(sys.argv) > 3 else 0.27
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    model_path = resolve_path(model_arg)
    if model_path is None:
        print(f"[!] model not found: {model_arg}"); return

    print(f"\n{'='*72}")
    print(f"DROPOUT SWEEP (SINGLE-POLICY ABLATION)  |  {n_maps} maps  |  density={density}  |  {n_workers}w")
    print(f"  model : {os.path.basename(model_path)}  (use_shared_map toggled; same weights both arms)")
    print(f"  10% row should reproduce the anchor (tab:anchor) cell by construction.")
    print(f"{'='*72}\n", flush=True)

    tasks = []
    for level_idx, (dropout, sustain, d_label, blind_label) in enumerate(SWEEP):
        for map_idx in range(n_maps):
            tasks.append((level_idx, dropout, sustain, True,  map_idx))   # ON  = shared map
            tasks.append((level_idx, dropout, sustain, False, map_idx))   # OFF = own LiDAR only

    on_rates  = {i: np.zeros(n_maps, dtype=np.float32) for i in range(len(SWEEP))}
    off_rates = {i: np.zeros(n_maps, dtype=np.float32) for i in range(len(SWEEP))}
    done, total = 0, len(tasks)
    chunk = max(1, total // (n_workers * 4))
    with Pool(n_workers, initializer=_init, initargs=(model_path, density)) as pool:
        for level_idx, use_shared, map_idx, rate in pool.imap_unordered(_run, tasks, chunksize=chunk):
            (on_rates if use_shared else off_rates)[level_idx][map_idx] = rate
            done += 1
            if done % 500 == 0:
                print(f"  ... {done}/{total}", flush=True)

    rows = []
    for level_idx, (dropout, sustain, d_label, blind_label) in enumerate(SWEEP):
        blind_pct = dropout * sustain / (1.0 + dropout * sustain) * 100.0
        on_rate  = 100.0 * float(np.mean(on_rates[level_idx]))
        off_rate = 100.0 * float(np.mean(off_rates[level_idx]))
        gap = on_rate - off_rate
        ci_lo, ci_hi = bootstrap_ci(on_rates[level_idx], off_rates[level_idx])
        rows.append((d_label, f"{blind_pct:.0f}%", on_rate, off_rate, gap, ci_lo, ci_hi))
        print(f"  dropout={d_label:>4} blind~{blind_pct:.0f}%  ON {on_rate:.2f}%  OFF {off_rate:.2f}%  "
              f"gap {gap:+.2f} pp  CI [{ci_lo:+.2f}, {ci_hi:+.2f}]", flush=True)

    print(f"\n\n{'='*72}")
    print(f"RESULTS -- drone-level success (single-policy ablation)")
    print(f"{'='*72}")
    print(f"  {'Dropout':>7}  {'Blind':>5}  {'ON':>7}  {'OFF':>7}  {'Gap':>8}  {'95% CI (gap)':>20}")
    print(f"  {'-------':>7}  {'-----':>5}  {'-------':>7}  {'-------':>7}  {'--------':>8}  {'--------------------':>20}")
    for d_label, blind_label, on_r, off_r, gap, ci_lo, ci_hi in rows:
        print(f"  {d_label:>7}  {blind_label:>5}  {on_r:>6.2f}%  {off_r:>6.2f}%  {gap:>+7.2f}pp  [{ci_lo:+6.2f}, {ci_hi:+6.2f}] pp")
    print(f"{'='*72}")

    gaps = [r[4] for r in rows]
    cis  = [(r[5], r[6]) for r in rows]
    print(f"\n[INTERPRETATION]")
    all_sig  = all(lo > 0 for lo, _ in cis[1:])   # 0% row is expected non-significant
    print(f"  [i] 10% row ON/OFF should match tab:anchor (89.3/45.9); if so, tables now reconcile.")
    if all_sig:
        print(f"  [OK] Gap significant at 10% and 20% (CIs > 0): {gaps[1]:+.2f} -> {gaps[2]:+.2f} pp")
    else:
        print(f"  [!] Review: a degraded-dropout CI is not clear of zero.")


if __name__ == "__main__":
    main()
