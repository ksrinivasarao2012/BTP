"""
Parallel evaluator (8-10 cores) — identical results to the serial evals, ~Nx faster.

Determinism: every map is reset with the SAME seed formula as the serial scripts and the policy
runs deterministic=True (no sampling), so a given map yields the same outcome regardless of which
worker computes it or how many workers there are. Verify with `mode=matrix` vs eval_trust_defense.py.

Modes:
  matrix     : k in {0,1,2,3} x {defense off,on}, wall attack  (== eval_trust_defense.py)
  attackcmp  : fixed k, wall vs camouflage x {off,on}          (== eval_attack_modes.py)
  gapsweep   : fixed k, camouflage, sweep camouflage_gap x {off,on}

Usage:
  python eval_parallel.py <model> <n_maps> <mode> [k] [n_workers]
  python eval_parallel.py models/raster_slot_fusion_ON_stage2_final.zip 500 matrix    8 10
  python eval_parallel.py models/raster_slot_fusion_ON_stage2_final.zip 300 attackcmp 2 10
  python eval_parallel.py models/raster_slot_fusion_ON_stage2_final.zip 300 gapsweep  2 10
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
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

LOCAL = 130
GLOBAL = 520
DEFAULT_MODEL = "models/raster_slot_fusion_ON_stage2_final.zip"
GAP_LEVELS = (0.1, 0.3, 0.6, 1.0)     # camouflage_gap sweep (m)

# ── policy classes (must exist at import time for PPO.load in each worker) ──────
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


# ── worker globals + setup ─────────────────────────────────────────────────────
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
    from env_byzantine_adaptive import AdaptiveByzantineEnv
    return AdaptiveByzantineEnv(
        render_mode=None, target_density=0.20, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=cfg["dropout"], dropout_sustain=cfg["sustain"], use_shared_map=True,
        false_obstacle_attack=(cfg["n_traitors"] > 0),
        traitor_indices=list(range(cfg["n_traitors"])),
        attack_mode=cfg["attack_mode"], trust_defense=cfg["defense"],
        camouflage_gap=cfg["camouflage_gap"],
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


# ── condition builders ─────────────────────────────────────────────────────────
def _cfg(label, n_traitors, attack_mode, defense, camouflage_gap=0.3, dropout=0.10, sustain=5):
    return dict(label=label, n_traitors=n_traitors, attack_mode=attack_mode, defense=defense,
                camouflage_gap=camouflage_gap, dropout=dropout, sustain=sustain)


def build_conditions(mode, k):
    if mode == "matrix":
        conds = [_cfg("k0_off", 0, "wall", False), _cfg("k0_on", 0, "wall", True)]
        for kk in (1, 2, 3):
            conds += [_cfg(f"k{kk}_off", kk, "wall", False), _cfg(f"k{kk}_on", kk, "wall", True)]
        return conds
    if mode == "attackcmp":
        return [_cfg("baseline", 0, "wall", False),
                _cfg("wall_off", k, "wall", False), _cfg("wall_on", k, "wall", True),
                _cfg("camo_off", k, "camouflage", False), _cfg("camo_on", k, "camouflage", True)]
    if mode == "gapsweep":
        conds = [_cfg("baseline", 0, "wall", False)]
        for g in GAP_LEVELS:
            conds += [_cfg(f"gap{g}_off", k, "camouflage", False, camouflage_gap=g),
                      _cfg(f"gap{g}_on", k, "camouflage", True, camouflage_gap=g)]
        return conds
    raise ValueError(f"unknown mode {mode}")


# ── stats helpers ──────────────────────────────────────────────────────────────
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


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    mode = sys.argv[3] if len(sys.argv) > 3 else "matrix"
    k = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    n_workers = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    conds = build_conditions(mode, k)
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]
    print(f"\n{'='*80}")
    print(f"PARALLEL EVAL | {os.path.basename(model_path)} | mode={mode} | {n_maps} maps/cond | "
          f"{len(conds)} conds | {n_workers} workers")
    print(f"{'='*80}", flush=True)

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

    succ = {ci: 100.0 * float(np.mean(rates[ci])) for ci in range(len(conds))}

    if mode == "matrix":
        _report_matrix(conds, succ, rates, det)
    elif mode == "attackcmp":
        _report_attackcmp(conds, succ, rates, det, k)
    else:
        _report_gapsweep(conds, succ, rates, det, k)


def _pr(det_ci):
    TP, FP, FN = det_ci
    p = TP / (TP + FP) if (TP + FP) else 0.0
    r = TP / (TP + FN) if (TP + FN) else 0.0
    return p, r


def _report_matrix(conds, succ, rates, det):
    idx = {c["label"]: i for i, c in enumerate(conds)}
    base = succ[idx["k0_off"]]
    print(f"\n{'='*80}\nRESULTS — defense matrix (wall attack)\n{'='*80}")
    print(f"  no-harm (k0, defense ON): {succ[idx['k0_on']]:.2f}% vs {base:.2f}% baseline "
          f"(delta {succ[idx['k0_on']]-base:+.2f} pp)")
    print(f"  {'k':>2}  {'no-def':>7}  {'defense':>7}  {'recovery':>9}  {'95% CI':>20}  {'P/R':>10}")
    for kk in (1, 2, 3):
        off, on = succ[idx[f"k{kk}_off"]], succ[idx[f"k{kk}_on"]]
        lo, hi = bootstrap_ci(rates[idx[f"k{kk}_on"]], rates[idx[f"k{kk}_off"]])
        p, r = _pr(det[idx[f"k{kk}_on"]])
        print(f"  {kk:>2}  {off:>6.2f}%  {on:>6.2f}%  {on-off:>+8.2f}pp  [{lo:+6.2f}, {hi:+6.2f}]  {p:>4.2f}/{r:<4.2f}")
    print(f"{'='*80}")


def _report_attackcmp(conds, succ, rates, det, k):
    idx = {c["label"]: i for i, c in enumerate(conds)}
    base = succ[idx["baseline"]]
    print(f"\n{'='*80}\nRESULTS — attack modes (k={k}) | clean baseline = {base:.2f}%\n{'='*80}")
    print(f"  {'attack':>11}  {'no-def':>7}  {'drop':>7}  {'defense':>7}  {'recovery':>9}  {'CI':>18}  {'P/R':>10}")
    for mode_lbl, off_l, on_l in [("wall", "wall_off", "wall_on"), ("camouflage", "camo_off", "camo_on")]:
        off, on = succ[idx[off_l]], succ[idx[on_l]]
        lo, hi = bootstrap_ci(rates[idx[on_l]], rates[idx[off_l]])
        p, r = _pr(det[idx[on_l]])
        print(f"  {mode_lbl:>11}  {off:>6.2f}%  {base-off:>+6.2f}  {on:>6.2f}%  {on-off:>+8.2f}pp  [{lo:+5.1f},{hi:+5.1f}]  {p:>4.2f}/{r:<4.2f}")
    print(f"{'='*80}")


def _report_gapsweep(conds, succ, rates, det, k):
    idx = {c["label"]: i for i, c in enumerate(conds)}
    base = succ[idx["baseline"]]
    print(f"\n{'='*80}\nRESULTS — camouflage_gap sweep (k={k}) | clean baseline = {base:.2f}%\n{'='*80}")
    print(f"  {'gap(m)':>7}  {'no-def':>7}  {'drop':>7}  {'defense':>7}  {'recovery':>9}  {'P/R':>10}")
    for g in GAP_LEVELS:
        off, on = succ[idx[f"gap{g}_off"]], succ[idx[f"gap{g}_on"]]
        p, r = _pr(det[idx[f"gap{g}_on"]])
        print(f"  {g:>7.2f}  {off:>6.2f}%  {base-off:>+6.2f}  {on:>6.2f}%  {on-off:>+8.2f}pp  {p:>4.2f}/{r:<4.2f}")
    print(f"{'='*80}")
    print("  Read: small gap -> stealthy (high P/R held? small drop=harmless);")
    print("        large gap -> harmful (big drop) but detected (high P/R). Attacker is boxed in.")


if __name__ == "__main__":
    main()
