"""
STEP 4 - TEMPORAL-TRUST evaluation (wall + camouflage under noise).

Extends the §5.7/5.8 noise sweep with the temporal column. Per noise level, at k traitors:
  base        : k=0, no defense
  off         : k traitors, no defense
  robust      : k traitors, single-frame robust filter (k_sigma=4, alpha=0.25, tau=0.4)
  temporal    : k traitors, COMPOSED defense (robust OR temporal offset-bias)   <- the new column
  temporal_nh : k=0, composed defense ON                                        <- no-harm / FP check

The temporal column is strictly >= robust (it keeps the single-frame fast path for open-space
wall phantoms and adds the slow offset-bias path that catches camouflage). The decisive comparison
is the sigma=0.6 CAMOUFLAGE cell vs §5.8 (robust recall 0.21, recovery +1.4 pp).

Usage:
  python eval_temporal.py <model> <n_maps> [k] [n_workers] [attack_mode] [eps] [min_k]
  python eval_temporal.py models/noise_robust_ON_stage1_final.zip 150 2 10 wall
  python eval_temporal.py models/noise_robust_ON_stage1_final.zip 150 2 10 camouflage 0.6 20
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
DEFAULT_MODEL = "models/noise_robust_ON_stage1_final.zip"
NOISE_LEVELS = (0.0, 0.2, 0.4, 0.6)
ROBUST_K_SIGMA = 4.0
ROBUST_ALPHA = 0.25
ROBUST_TAU = 0.4
TEMPORAL_EPS = 0.6      # chosen from the STEP-3 self-test sweep (best P/R frontier point)
TEMPORAL_MIN_K = 20

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
        randomize_attack=cfg.get("randomize", False), n_phantom_range=(3, 6),
        attack_mode=cfg["attack_mode"], trust_defense=cfg["defense"],
        sensor_noise=cfg["sensor_noise"],
        verify_k_sigma=cfg["k_sigma"], trust_alpha=cfg["alpha"], tau_trust=cfg["tau"],
        temporal_defense=cfg["temporal"],
        temporal_bias_eps=cfg["eps"], temporal_min_k=cfg["min_k"],
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
    if (cfg["defense"] or cfg["temporal"]) and n_traitors > 0:
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


def _cfg(label, noise, n_traitors, defense, k_sigma, alpha, tau, attack_mode,
         temporal=False, eps=TEMPORAL_EPS, min_k=TEMPORAL_MIN_K, randomize=False):
    return dict(label=label, sensor_noise=noise, n_traitors=n_traitors, defense=defense,
                k_sigma=k_sigma, alpha=alpha, tau=tau, attack_mode=attack_mode,
                temporal=temporal, eps=eps, min_k=min_k, randomize=randomize)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    attack_mode = sys.argv[5] if len(sys.argv) > 5 else "wall"
    eps = float(sys.argv[6]) if len(sys.argv) > 6 else TEMPORAL_EPS
    min_k = int(sys.argv[7]) if len(sys.argv) > 7 else TEMPORAL_MIN_K
    # randomize_attack: per-map n_phantom~U{3..6} + per-phantom radius from the real mixture.
    # ON by default for headline realism; pass "0"/"fixed" as argv[8] to force the legacy fixed attack.
    rnd = (sys.argv[8].lower() not in ("0", "fixed", "false")) if len(sys.argv) > 8 else True
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    conds = []
    for nz in NOISE_LEVELS:
        conds += [
            _cfg(f"n{nz}_base", nz, 0, False, 0.0, 0.5, 0.5, attack_mode, randomize=rnd),
            _cfg(f"n{nz}_off", nz, k, False, 0.0, 0.5, 0.5, attack_mode, randomize=rnd),
            _cfg(f"n{nz}_robust", nz, k, True, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                 randomize=rnd),
            _cfg(f"n{nz}_temporal", nz, k, True, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                 temporal=True, eps=eps, min_k=min_k, randomize=rnd),
            _cfg(f"n{nz}_temporal_nh", nz, 0, True, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                 temporal=True, eps=eps, min_k=min_k, randomize=rnd),
        ]
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*100}")
    print(f"TEMPORAL EVAL | {os.path.basename(model_path)} | k={k} | {n_maps} maps/cond | "
          f"{len(conds)} conds | {n_workers}w")
    print(f"  robust: eps+={ROBUST_K_SIGMA}*sigma, alpha={ROBUST_ALPHA}, tau={ROBUST_TAU} | "
          f"temporal: bias_eps={eps}, min_k={min_k} | {attack_mode} attack | "
          f"randomize={'ON (n~U{3..6}, r~real-mix)' if rnd else 'OFF (fixed)'}")
    print(f"{'='*100}", flush=True)

    rates = {ci: np.zeros(n_maps, dtype=np.float32) for ci in range(len(conds))}
    detTP = {ci: np.zeros(n_maps, dtype=np.float32) for ci in range(len(conds))}
    detFP = {ci: np.zeros(n_maps, dtype=np.float32) for ci in range(len(conds))}
    detFN = {ci: np.zeros(n_maps, dtype=np.float32) for ci in range(len(conds))}
    done = 0
    total = len(tasks)
    chunk = max(1, n_maps // n_workers)
    with Pool(n_workers, initializer=_init, initargs=(model_path, conds)) as pool:
        for ci, mi, rate, TP, FP, FN in pool.imap(_run, tasks, chunksize=chunk):
            rates[ci][mi] = rate
            detTP[ci][mi] = TP; detFP[ci][mi] = FP; detFN[ci][mi] = FN
            done += 1
            if done % max(1, total // 20) == 0:
                print(f"  ... {done}/{total} ({100*done/total:.0f}%)", flush=True)

    idx = {c["label"]: i for i, c in enumerate(conds)}
    succ = {ci: 100.0 * float(np.mean(rates[ci])) for ci in range(len(conds))}

    def pr(lbl):
        ci = idx[lbl]
        TP, FP, FN = detTP[ci].sum(), detFP[ci].sum(), detFN[ci].sum()
        p = TP / (TP + FP) if (TP + FP) else 0.0
        r = TP / (TP + FN) if (TP + FN) else 0.0
        return p, r

    print(f"\n{'='*100}")
    print(f"RESULTS - temporal vs robust under noise (k={k}, {attack_mode} attack)")
    print(f"{'='*100}")
    print(f"  {'noise':>5} | {'base':>6} {'attack':>6} | {'robust':>6} {'P/R':>9} | "
          f"{'temporal':>8} {'P/R':>9} {'temp.nh':>7} | {'rob.rec':>8} {'tmp.rec':>8}")
    for nz in NOISE_LEVELS:
        base = succ[idx[f"n{nz}_base"]]
        off = succ[idx[f"n{nz}_off"]]
        robust = succ[idx[f"n{nz}_robust"]]
        temporal = succ[idx[f"n{nz}_temporal"]]
        nh = succ[idx[f"n{nz}_temporal_nh"]]
        pr_, rr = pr(f"n{nz}_robust")
        pt, rt = pr(f"n{nz}_temporal")
        print(f"  {nz:>5.2f} | {base:>5.1f}% {off:>5.1f}% | {robust:>5.1f}% {pr_:>4.2f}/{rr:<4.2f} | "
              f"{temporal:>7.1f}% {pt:>4.2f}/{rt:<4.2f} {nh:>6.1f}% | "
              f"{robust-off:>+7.1f} {temporal-off:>+7.1f}")
    print(f"{'='*100}")
    print("  temp.nh = temporal no-harm (k=0, defense ON): should stay ~= base if no false-gating harm")
    print("  rec columns = success recovery vs the undefended 'attack' (off) column, in pp")

    # ---- paired-bootstrap 95% CIs over maps (2000 resamples) ----
    import boot_ci
    print(f"\n{'='*100}")
    print(f"95% CONFIDENCE INTERVALS - paired bootstrap over {n_maps} maps (2000 resamples)")
    print(f"{'='*100}")
    for nz in NOISE_LEVELS:
        b = idx[f"n{nz}_base"]; o = idx[f"n{nz}_off"]
        rb = idx[f"n{nz}_robust"]; tp_ = idx[f"n{nz}_temporal"]; nh = idx[f"n{nz}_temporal_nh"]
        s_base = boot_ci.mean_ci(rates[b]); s_off = boot_ci.mean_ci(rates[o])
        s_rob = boot_ci.mean_ci(rates[rb]); s_tmp = boot_ci.mean_ci(rates[tp_]); s_nh = boot_ci.mean_ci(rates[nh])
        rec_rob = boot_ci.diff_ci(rates[rb], rates[o]); rec_tmp = boot_ci.diff_ci(rates[tp_], rates[o])
        noharm = boot_ci.diff_ci(rates[nh], rates[b])
        P, Plo, Phi, R, Rlo, Rhi = boot_ci.pr_ci(detTP[tp_], detFP[tp_], detFN[tp_])
        print(f"\n  sigma={nz:.2f}")
        print(f"    base     {s_base[0]:5.1f}% [{s_base[1]:5.1f},{s_base[2]:5.1f}]   "
              f"off {s_off[0]:5.1f}% [{s_off[1]:5.1f},{s_off[2]:5.1f}]")
        print(f"    robust   {s_rob[0]:5.1f}% [{s_rob[1]:5.1f},{s_rob[2]:5.1f}]   "
              f"recovery {rec_rob[0]:+5.1f} [{rec_rob[1]:+5.1f},{rec_rob[2]:+5.1f}] pp")
        print(f"    temporal {s_tmp[0]:5.1f}% [{s_tmp[1]:5.1f},{s_tmp[2]:5.1f}]   "
              f"recovery {rec_tmp[0]:+5.1f} [{rec_tmp[1]:+5.1f},{rec_tmp[2]:+5.1f}] pp")
        print(f"    temp.nh  {s_nh[0]:5.1f}% [{s_nh[1]:5.1f},{s_nh[2]:5.1f}]   "
              f"no-harm  {noharm[0]:+5.1f} [{noharm[1]:+5.1f},{noharm[2]:+5.1f}] pp")
        print(f"    temporal detection  precision {P:.2f} [{Plo:.2f},{Phi:.2f}]   "
              f"recall {R:.2f} [{Rlo:.2f},{Rhi:.2f}]")
    print(f"{'='*100}")

    print(f"\n[VERDICT - STEP 4 gate, focus on the {attack_mode} sigma=0.6 cell]")
    hi = NOISE_LEVELS[-1]
    pt, rt = pr(f"n{hi}_temporal")
    base_hi = succ[idx[f"n{hi}_base"]]
    nh_hi = succ[idx[f"n{hi}_temporal_nh"]] - base_hi
    rec_hi = succ[idx[f"n{hi}_temporal"]] - succ[idx[f"n{hi}_off"]]
    rec_rob = succ[idx[f"n{hi}_robust"]] - succ[idx[f"n{hi}_off"]]
    print(f"  sigma={hi}: temporal recall {rt:.2f} (robust {pr(f'n{hi}_robust')[1]:.2f}), "
          f"recovery {rec_hi:+.1f} pp (robust {rec_rob:+.1f} pp), no-harm {nh_hi:+.1f} pp, precision {pt:.2f}")
    if rt >= 0.5 and rec_hi >= 5.0 and nh_hi > -3.0 and pt >= 0.9:
        print("  -> WIN: temporal memory breaks the noise-band limit. (STEP 5 write-up.)")
    elif rec_hi >= 5.0 and rt >= 0.5:
        print("  -> WIN-ish on recovery/recall but check no-harm/precision (may be NO-HARM-FAILS -> tune).")
    else:
        print("  -> NOT a clean sigma=0.6 win; check sigma=0.4 cell for PARTIAL, else NO GAIN.")


if __name__ == "__main__":
    main()
