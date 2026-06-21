"""
Dropout sweep: ON-trained vs OFF-trained models across 3 sensor-failure regimes.

  dropout=0%  → blind 0%   (no failure — sanity check)
  dropout=10% → blind ~33% (training regime)
  dropout=20% → blind ~50% (stress test)

ON  model: models/raster_slot_fusion_ON_stage2_final.zip  (use_shared_map=True)
OFF model: models/raster_slot_fusion_OFF_stage2_final.zip (use_shared_map=False)

Reports drone-level success rate + 95% bootstrapped CI on the ON-OFF gap.

Usage:
    python eval_dropout_sweep.py [n_maps]
    python eval_dropout_sweep.py 500
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

ON_MODEL  = "models/raster_slot_fusion_ON_stage2_final.zip"
OFF_MODEL = "models/raster_slot_fusion_OFF_stage2_final.zip"


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


def run_eval(model, use_shared_map, dropout, sustain, n_maps, tag, density=0.20):
    """Returns (drone_success_rate %, per_map_drone_rates array)."""
    env = SwarmLidarEnv_Raster(
        render_mode=None,
        target_density=density,
        communication_range=10.0,
        congestion_mode="lidar",
        lidar_range=8.0,
        lidar_dropout=dropout,
        dropout_sustain=sustain,
        use_shared_map=use_shared_map,
        probe_lidar_slot=False,
        slot_fusion=True,
        straight_line_goal=False
    )
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    per_map_drone_rates = []

    print(f"    [{tag}] {n_maps} maps ...", flush=True)
    for map_idx in range(n_maps):
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

        per_map_drone_rates.append(map_reached / map_total if map_total > 0 else 0.0)
        if (map_idx + 1) % 100 == 0:
            print(f"      ... {map_idx + 1}/{n_maps}", flush=True)

    env.close()
    rates = np.array(per_map_drone_rates, dtype=np.float32)
    return 100.0 * float(np.mean(rates)), rates


# ---- parallel worker machinery (identical results to serial: explicit seeds + deterministic predict) ----
from multiprocessing import Pool

_G = {}


def _init(on_path, off_path, density):
    _G["on"]  = PPO.load(on_path,  custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    _G["off"] = PPO.load(off_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
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
    model = _G["on"] if use_shared else _G["off"]
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
    """Paired bootstrap CI on (ON - OFF) drone-level gap."""
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
    n_maps = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    density = float(sys.argv[2]) if len(sys.argv) > 2 else 0.20
    n_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    on_path  = resolve_path(ON_MODEL)
    off_path = resolve_path(OFF_MODEL)
    for label, path, default in [("ON", on_path, ON_MODEL), ("OFF", off_path, OFF_MODEL)]:
        if path is None:
            print(f"[!] {label} model not found: {default}"); return

    print(f"\n{'='*72}")
    print(f"DROPOUT SWEEP  |  {n_maps} maps per condition  |  density={density}  |  {n_workers}w  |  drone-level success")
    print(f"  ON  model : {os.path.basename(on_path)}")
    print(f"  OFF model : {os.path.basename(off_path)}")
    print(f"{'='*72}\n", flush=True)

    # build all (level, mode, map) tasks and run them in one pool
    tasks = []
    for level_idx, (dropout, sustain, d_label, blind_label) in enumerate(SWEEP):
        for map_idx in range(n_maps):
            tasks.append((level_idx, dropout, sustain, True,  map_idx))   # ON  -> on_model
            tasks.append((level_idx, dropout, sustain, False, map_idx))   # OFF -> off_model

    on_rates  = {i: np.zeros(n_maps, dtype=np.float32) for i in range(len(SWEEP))}
    off_rates = {i: np.zeros(n_maps, dtype=np.float32) for i in range(len(SWEEP))}
    done, total = 0, len(tasks)
    chunk = max(1, total // (n_workers * 4))
    with Pool(n_workers, initializer=_init, initargs=(on_path, off_path, density)) as pool:
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

    # -- Final table --
    print(f"\n\n{'='*72}")
    print(f"RESULTS -- drone-level success rate")
    print(f"{'='*72}")
    print(f"  {'Dropout':>7}  {'Blind':>5}  {'ON':>7}  {'OFF':>7}  {'Gap':>8}  {'95% CI (gap)':>20}")
    print(f"  {'-------':>7}  {'-----':>5}  {'-------':>7}  {'-------':>7}  {'--------':>8}  {'--------------------':>20}")
    for d_label, blind_label, on_r, off_r, gap, ci_lo, ci_hi in rows:
        print(f"  {d_label:>7}  {blind_label:>5}  {on_r:>6.2f}%  {off_r:>6.2f}%  {gap:>+7.2f}pp  [{ci_lo:+6.2f}, {ci_hi:+6.2f}] pp")
    print(f"{'='*72}")

    # -- Interpretation --
    gaps = [r[4] for r in rows]
    cis  = [(r[5], r[6]) for r in rows]
    print(f"\n[INTERPRETATION]")
    all_sig = all(lo > 0 for lo, _ in cis)
    monotone = gaps[0] <= gaps[1] <= gaps[2]
    if all_sig and monotone:
        print(f"  [OK] Gap significant at all dropout levels (all CIs > 0).")
        print(f"  [OK] Gap grows with dropout severity: {gaps[0]:+.2f} -> {gaps[1]:+.2f} -> {gaps[2]:+.2f} pp")
        print(f"    Collaborative perception becomes MORE valuable as sensors degrade. Strong result.")
    elif all_sig:
        print(f"  [OK] Gap significant at all levels (all CIs > 0).")
        print(f"  [~] Gap not strictly monotone: {gaps[0]:+.2f} -> {gaps[1]:+.2f} -> {gaps[2]:+.2f} pp")
    else:
        non_sig = [rows[i][0] for i, (lo, _) in enumerate(cis) if lo <= 0]
        print(f"  [!] Not significant at dropout={non_sig}. Review those rows.")


if __name__ == "__main__":
    main()
