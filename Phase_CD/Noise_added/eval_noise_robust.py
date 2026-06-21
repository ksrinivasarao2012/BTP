"""
NOISE SWEEP — naive vs ROBUST consistency filter (fair-baseline test).

The earlier sweep showed the NAIVE filter (fixed threshold, fast decay) collapses under noise
(precision 1.00 -> 0.32). Before concluding "learned trust is needed," we must check a properly
designed hardcoded rule. The ROBUST filter applies two fixes that target the real failure
(false positives from noise):
  * noise-aware tolerance: eps = verify_eps + k_sigma * sensor_noise  -> honest noisy matches pass
  * slower trust decay (small trust_alpha)                            -> one noisy mismatch can't condemn

Per noise level, at k traitors (wall attack), we run:
  base        : k=0, no defense
  off         : k traitors, no defense
  naive_on    : k traitors, NAIVE filter   (k_sigma=0, alpha=0.5)   <- the strawman
  robust_on   : k traitors, ROBUST filter  (k_sigma=4, alpha=0.25)  <- fair baseline
  robust_noharm: k=0, ROBUST filter        (false-positive check)

Decision:
  * if ROBUST recovers precision + recovery under noise -> hardcoded is genuinely fine; NO learned
    trust needed (simpler, honest paper).
  * if ROBUST still fails (esp. later vs camouflage) -> THEN learned trust is justified.

Usage:
  python eval_noise_robust.py <model> <n_maps> [k] [n_workers]
  python eval_noise_robust.py models/raster_slot_fusion_ON_stage2_final.zip 150 2 10
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
NOISE_LEVELS = (0.0, 0.2, 0.4, 0.6)
ROBUST_K_SIGMA = 4.0
ROBUST_ALPHA = 0.25
ROBUST_TAU = 0.4

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
        attack_mode=cfg["attack_mode"], trust_defense=cfg["defense"],
        sensor_noise=cfg["sensor_noise"],
        verify_k_sigma=cfg["k_sigma"], trust_alpha=cfg["alpha"], tau_trust=cfg["tau"],
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


def resolve_path(path):
    if os.path.exists(path):
        return path
    for c in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(c):
            return c
    return None


def _cfg(label, noise, n_traitors, defense, k_sigma, alpha, tau, attack_mode):
    return dict(label=label, sensor_noise=noise, n_traitors=n_traitors, defense=defense,
                k_sigma=k_sigma, alpha=alpha, tau=tau, attack_mode=attack_mode)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    attack_mode = sys.argv[5] if len(sys.argv) > 5 else "wall"   # "wall" | "camouflage"
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    conds = []
    for nz in NOISE_LEVELS:
        conds += [
            _cfg(f"n{nz}_base", nz, 0, False, 0.0, 0.5, 0.5, attack_mode),
            _cfg(f"n{nz}_off", nz, k, False, 0.0, 0.5, 0.5, attack_mode),
            _cfg(f"n{nz}_naive", nz, k, True, 0.0, 0.5, 0.5, attack_mode),
            _cfg(f"n{nz}_robust", nz, k, True, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode),
            _cfg(f"n{nz}_robust_nh", nz, 0, True, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode),
        ]
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*94}")
    print(f"NOISE SWEEP - naive vs ROBUST filter | {os.path.basename(model_path)} | k={k} | "
          f"{n_maps} maps/cond | {len(conds)} conds | {n_workers}w")
    print(f"  robust: eps += {ROBUST_K_SIGMA}*sigma, alpha={ROBUST_ALPHA}, tau={ROBUST_TAU} | {attack_mode} attack")
    print(f"{'='*94}", flush=True)

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

    def pr(lbl):
        TP, FP, FN = det[idx[lbl]]
        p = TP / (TP + FP) if (TP + FP) else 0.0
        r = TP / (TP + FN) if (TP + FN) else 0.0
        return p, r

    print(f"\n{'='*94}")
    print(f"RESULTS - naive vs robust filter under noise (k={k}, {attack_mode} attack)")
    print(f"{'='*94}")
    print(f"  {'noise':>5} | {'base':>6} {'attack':>6} | {'naive':>6} {'P/R':>9} | "
          f"{'robust':>6} {'P/R':>9} {'nh':>6} | {'rob.recov':>9}")
    for nz in NOISE_LEVELS:
        base = succ[idx[f"n{nz}_base"]]
        off = succ[idx[f"n{nz}_off"]]
        naive = succ[idx[f"n{nz}_naive"]]
        robust = succ[idx[f"n{nz}_robust"]]
        nh = succ[idx[f"n{nz}_robust_nh"]]
        pn, rn = pr(f"n{nz}_naive")
        pr_, rr = pr(f"n{nz}_robust")
        print(f"  {nz:>5.2f} | {base:>5.1f}% {off:>5.1f}% | {naive:>5.1f}% {pn:>4.2f}/{rn:<4.2f} | "
              f"{robust:>5.1f}% {pr_:>4.2f}/{rr:<4.2f} {nh:>5.1f}% | {robust-off:>+8.1f}pp")
    print(f"{'='*94}")
    print("  nh = robust no-harm (k=0, defense ON): should stay ~= base if no false positives")

    print(f"\n[VERDICT]")
    pr_hi, rr_hi = pr(f"n{NOISE_LEVELS[-1]}_robust")
    nh_hi = succ[idx[f"n{NOISE_LEVELS[-1]}_robust_nh"]] - succ[idx[f"n{NOISE_LEVELS[-1]}_base"]]
    rec_hi = succ[idx[f"n{NOISE_LEVELS[-1]}_robust"]] - succ[idx[f"n{NOISE_LEVELS[-1]}_off"]]
    print(f"  at noise {NOISE_LEVELS[-1]}: robust precision {pr_hi:.2f}, no-harm {nh_hi:+.1f} pp, recovery {rec_hi:+.1f} pp")
    if pr_hi >= 0.7 and nh_hi > -3.0 and rec_hi > 2.0:
        print("  -> ROBUST filter SURVIVES noise. Hardcoded defense is genuinely good.")
        print("     Learned trust is NOT justified on the wall attack. Next: test camouflage+noise.")
    else:
        print("  -> ROBUST filter STILL fails under noise (even with fair tuning).")
        print("     This is the real justification for learned trust (or a fundamental-limit result).")


if __name__ == "__main__":
    main()
