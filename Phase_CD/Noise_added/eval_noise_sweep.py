"""
NOISE SWEEP (parallel) - does the hardcoded consistency filter survive blurry sensing?

For each sensor-noise level, runs 4 conditions at fixed k traitors (wall attack):
  baseline  : k=0, defense off            (nav-only degradation from noise)
  no-harm   : k=0, defense ON             (false positives -> honest neighbors distrusted)
  attack    : k traitors, defense off
  defense   : k traitors, defense ON      (recovery + detection P/R)

What to read:
  * no-harm dropping below baseline  -> the filter is wrongly distrusting honest drones (FP rising)
  * detection precision falling below 1.00 -> honest broadcasts misflagged as lies
  * recovery (defense - attack) shrinking with noise -> the simple rule is cracking
  -> if it cracks, that is the justification to build LEARNED trust.

Determinism: same seed formula + deterministic policy -> identical to a serial run.

Usage:
  python eval_noise_sweep.py <model> <n_maps> [k] [n_workers]
  python eval_noise_sweep.py models/raster_slot_fusion_ON_stage2_final.zip 300 2 10
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
_COLLAB = os.path.join(_PHASE_CD, "Collab_Perception")
for _p in (_ROOT, _PHASE_CD, _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

LOCAL = 130
GLOBAL = 520
DEFAULT_MODEL = "models/raster_slot_fusion_ON_stage2_final.zip"
NOISE_LEVELS = (0.0, 0.2, 0.4, 0.6)        # Gaussian std (m) on sensed obstacle positions

import torch.nn as nn
from stable_baselines3.common.policies import ActorCriticPolicy


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


_G = {}


def _init(model_path, conds):
    import torch
    torch.set_num_threads(1)
    os.environ["OMP_NUM_THREADS"] = "1"
    from stable_baselines3 import PPO
    _G["model"] = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    _G["conds"] = conds
    _G["env"] = None
    _G["env_key"] = None


def _build_env(cfg):
    from env_noisy_byzantine import NoisyByzantineEnv
    return NoisyByzantineEnv(
        render_mode=None, target_density=0.27, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=0.10, dropout_sustain=5, use_shared_map=True,
        false_obstacle_attack=(cfg["n_traitors"] > 0),
        traitor_indices=list(range(cfg["n_traitors"])),
        attack_mode="wall", trust_defense=cfg["defense"],
        sensor_noise=cfg["sensor_noise"],
    )


def _run(task):
    cond_idx, map_idx = task
    cfg = _G["conds"][cond_idx]
    if _G["env_key"] != cond_idx:
        if _G["env"] is not None:
            _G["env"].close()
        _G["env"] = _build_env(cfg)
        _G["env_key"] = cond_idx
    env, model = _G["env"], _G["model"]

    n_traitors = cfg["n_traitors"]
    traitor_set = set(range(n_traitors))
    traitor_names = {f"drone_{i}" for i in range(n_traitors)}
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

    attempts = 0
    while True:
        seed = 800_000_000 + int(0.20 * 100) * 10_000 + map_idx + attempts * 5_000
        obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
        if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
            break
        attempts += 1

    h_reached = h_total = 0
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
                if a in traitor_names:
                    continue
                h_total += 1
                if infos[a].get("cause") == "success":
                    h_reached += 1
        if not env.agents:
            break

    rate = h_reached / h_total if h_total > 0 else 0.0
    TP = FP = FN = 0
    if cfg["defense"] and n_traitors > 0:
        for i, pred in env.predicted_traitors().items():
            pred = set(pred)
            TP += len(pred & traitor_set)
            FP += len(pred - traitor_set)
            FN += len(traitor_set - pred)
    return cond_idx, map_idx, rate, TP, FP, FN


def bootstrap_ci(a, b, n_bootstrap=10000, seed=42):
    np.random.seed(seed)
    n = len(a)
    diffs = [100.0 * float(np.mean(a[idx]) - np.mean(b[idx]))
             for idx in (np.random.choice(n, size=n, replace=True) for _ in range(n_bootstrap))]
    diffs = np.array(diffs)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def resolve_path(path):
    if os.path.exists(path):
        return path
    for c in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(c):
            return c
    return None


def _cfg(label, noise, n_traitors, defense):
    return dict(label=label, sensor_noise=noise, n_traitors=n_traitors, defense=defense)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    conds = []
    for nz in NOISE_LEVELS:
        conds += [_cfg(f"n{nz}_base", nz, 0, False),
                  _cfg(f"n{nz}_noharm", nz, 0, True),
                  _cfg(f"n{nz}_off", nz, k, False),
                  _cfg(f"n{nz}_on", nz, k, True)]
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*86}")
    print(f"NOISE SWEEP | {os.path.basename(model_path)} | k={k} | {n_maps} maps/cond | "
          f"{len(conds)} conds | {n_workers} workers")
    print(f"  noise levels (m): {NOISE_LEVELS}   (wall attack, dropout=0.10/sustain=5)")
    print(f"{'='*86}", flush=True)

    rates = {ci: np.zeros(n_maps, dtype=np.float32) for ci in range(len(conds))}
    det = {ci: [0, 0, 0] for ci in range(len(conds))}
    done = 0
    total = len(tasks)
    chunk = max(1, n_maps // n_workers)
    with Pool(n_workers, initializer=_init, initargs=(model_path, conds)) as pool:
        for ci, mi, rate, TP, FP, FN in pool.imap(_run, tasks, chunksize=chunk):
            rates[ci][mi] = rate
            det[ci][0] += TP; det[ci][1] += FP; det[ci][2] += FN
            done += 1
            if done % max(1, total // 20) == 0:
                print(f"  ... {done}/{total} ({100*done/total:.0f}%)", flush=True)

    idx = {c["label"]: i for i, c in enumerate(conds)}
    succ = {ci: 100.0 * float(np.mean(rates[ci])) for ci in range(len(conds))}

    print(f"\n{'='*86}")
    print(f"RESULTS - filter robustness vs sensor noise (k={k}, wall attack)")
    print(f"{'='*86}")
    print(f"  {'noise':>6}  {'base':>7}  {'noharm':>7}  {'FP-harm':>8}  {'attack':>7}  {'defense':>7}  {'recovery':>9}  {'P/R':>10}")
    for nz in NOISE_LEVELS:
        base = succ[idx[f"n{nz}_base"]]
        noharm = succ[idx[f"n{nz}_noharm"]]
        off = succ[idx[f"n{nz}_off"]]
        on = succ[idx[f"n{nz}_on"]]
        TP, FP, FN = det[idx[f"n{nz}_on"]]
        p = TP / (TP + FP) if (TP + FP) else 0.0
        r = TP / (TP + FN) if (TP + FN) else 0.0
        print(f"  {nz:>6.2f}  {base:>6.2f}%  {noharm:>6.2f}%  {noharm-base:>+7.2f}  "
              f"{off:>6.2f}%  {on:>6.2f}%  {on-off:>+8.2f}pp  {p:>4.2f}/{r:<4.2f}")
    print(f"{'='*86}")

    print(f"\n[INTERPRETATION]")
    p0 = det[idx[f'n{NOISE_LEVELS[0]}_on']]
    pN = det[idx[f'n{NOISE_LEVELS[-1]}_on']]
    prec0 = p0[0] / (p0[0] + p0[1]) if (p0[0] + p0[1]) else 0.0
    precN = pN[0] / (pN[0] + pN[1]) if (pN[0] + pN[1]) else 0.0
    harm0 = succ[idx[f"n{NOISE_LEVELS[0]}_noharm"]] - succ[idx[f"n{NOISE_LEVELS[0]}_base"]]
    harmN = succ[idx[f"n{NOISE_LEVELS[-1]}_noharm"]] - succ[idx[f"n{NOISE_LEVELS[-1]}_base"]]
    print(f"  precision {prec0:.2f} (noise 0) -> {precN:.2f} (noise {NOISE_LEVELS[-1]})")
    print(f"  no-harm delta {harm0:+.2f} pp -> {harmN:+.2f} pp")
    if precN < 0.9 or harmN < -3.0:
        print(f"  -> Filter CRACKS under noise (false positives / honest harm). "
              f"This JUSTIFIES building learned trust.")
    else:
        print(f"  -> Filter survives this noise range. Hardcoded defense is genuinely robust; "
              f"learned trust is not yet justified - report this honestly.")


if __name__ == "__main__":
    main()
