"""
FILTER-AWARE ADAPTIVE ATTACKER - does an attacker that KNOWS the temporal filter defeat it?

Pre-empts the #1 reviewer objection ("your adversary is static/weak"). At the hard cell
(sigma=0.6, camouflage, k=2), sweep ONE adaptive dimension and compare, per value:
  base     : k=0, no defense        (success ceiling)
  off      : k traitors, no defense (the HARM the attack actually does)
  temporal : k traitors, composed temporal defense (robust OR temporal)  + P/R

Sweeps (CLI `sweep`):
  gap    : camouflage_gap in {0.0,0.3,0.6,1.0,1.5}  -- the STEALTH/HARM BIND. Small gap => phantom hugs the
           real obstacle => small offset => evades temporal, but blocks ~no new space => low harm. Large gap
           => big offset => caught. Expectation: harm and recall RISE TOGETHER; the attacker cannot get one
           without the other.
  jitter : phantom_jitter in {0.0,0.3,0.6,1.0}      -- attacker adds zero-mean noise to fake honest spread.
           Expectation: recall ~FLAT. Jitter raises the offset VARIANCE, not its MEAN; the running-mean test
           is unaffected.
  duty   : phantom_duty in {1.0,0.7,0.5,0.3}        -- intermittent lying (broadcast phantom only a fraction
           of frames, look honest the rest). Expectation: recall falls as duty falls, BUT so does harm
           (the obstacle blocks the path less of the time) -- a softer stealth/harm bind.

Usage:
  python eval_adaptive_attack.py <model> <n_maps> [k] [n_workers] [sweep] [eps] [min_k]
  python eval_adaptive_attack.py models/noise_robust_ON_stage1_final.zip 150 2 10 gap
  python eval_adaptive_attack.py models/noise_robust_ON_stage1_final.zip 150 2 10 jitter
  python eval_adaptive_attack.py models/noise_robust_ON_stage1_final.zip 150 2 10 duty
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
SIGMA = float(sys.argv[6]) if len(sys.argv) > 6 else 0.6  # optional 6th CLI arg = noise sigma (default 0.6)
ROBUST_K_SIGMA = 4.0
ROBUST_ALPHA = 0.25
ROBUST_TAU = 0.4
TEMPORAL_EPS = 0.6
TEMPORAL_MIN_K = 20

SWEEPS = {
    "offset": ("phantom_center_offset", [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]),  # THE stealth/harm bind axis
    "gap":    ("camouflage_gap", [0.0, 0.3, 0.6, 1.0, 1.5]),
    "jitter": ("phantom_jitter", [0.0, 0.3, 0.6, 1.0]),
    "duty":   ("phantom_duty",   [1.0, 0.7, 0.5, 0.3]),
}

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
        attack_mode="camouflage", camouflage_gap=cfg["camouflage_gap"],
        phantom_center_offset=cfg["phantom_center_offset"],
        trust_defense=cfg["defense"], sensor_noise=SIGMA,
        verify_k_sigma=ROBUST_K_SIGMA, trust_alpha=ROBUST_ALPHA, tau_trust=ROBUST_TAU,
        temporal_defense=cfg["temporal"], temporal_bias_eps=cfg["eps"], temporal_min_k=cfg["min_k"],
        phantom_jitter=cfg["phantom_jitter"], phantom_duty=cfg["phantom_duty"],
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
            TP += len(pred & traitor_set); FP += len(pred - traitor_set); FN += len(traitor_set - pred)
    return cond_idx, map_idx, rate, TP, FP, FN


def resolve_path(path):
    if os.path.exists(path):
        return path
    for c in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(c):
            return c
    return None


def _cfg(label, n_traitors, defense, temporal, camouflage_gap=0.3, phantom_jitter=0.0, phantom_duty=1.0,
         phantom_center_offset=None):
    return dict(label=label, n_traitors=n_traitors, defense=defense, temporal=temporal,
                camouflage_gap=camouflage_gap, phantom_jitter=phantom_jitter, phantom_duty=phantom_duty,
                phantom_center_offset=phantom_center_offset, eps=TEMPORAL_EPS, min_k=TEMPORAL_MIN_K)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    sweep = sys.argv[5] if len(sys.argv) > 5 else "gap"
    if sweep not in SWEEPS:
        print(f"[!] sweep must be one of {list(SWEEPS)}"); return
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return
    param, values = SWEEPS[sweep]

    def kw(v):
        return {param: v}

    conds = []
    for v in values:
        conds += [
            _cfg(f"{v}_base", 0, False, False, **kw(v)),
            _cfg(f"{v}_off", k, False, False, **kw(v)),
            _cfg(f"{v}_temporal", k, True, True, **kw(v)),
        ]
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*100}")
    print(f"ADAPTIVE ATTACKER - sweep '{sweep}' ({param}) | {os.path.basename(model_path)} | "
          f"sigma={SIGMA} camouflage k={k} | {n_maps} maps/cond | {n_workers}w")
    print(f"  temporal: eps={TEMPORAL_EPS}, min_k={TEMPORAL_MIN_K} | composed (robust OR temporal)")
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
    print(f"RESULTS - adaptive '{sweep}' sweep (sigma={SIGMA}, camouflage, k={k})")
    print(f"{'='*100}")
    print(f"  {param:>14} | {'base':>6} {'off':>6} {'harm':>6} | {'temporal':>8} {'P/R':>9} | "
          f"{'recovery':>8}")
    for v in values:
        base = succ[idx[f"{v}_base"]]
        off = succ[idx[f"{v}_off"]]
        temporal = succ[idx[f"{v}_temporal"]]
        pt, rt = pr(f"{v}_temporal")
        harm = base - off
        print(f"  {v:>14} | {base:>5.1f}% {off:>5.1f}% {harm:>+5.1f} | {temporal:>7.1f}% "
              f"{pt:>4.2f}/{rt:<4.2f} | {temporal-off:>+7.1f}")
    print(f"{'='*100}")
    print("  harm = base-off (success the attack costs when undefended); recovery = temporal-off")

    # ---- paired-bootstrap 95% CIs over maps (2000 resamples) ----
    import boot_ci
    print(f"\n{'='*100}")
    print(f"95% CONFIDENCE INTERVALS - paired bootstrap over {n_maps} maps (2000 resamples)")
    print(f"{'='*100}")
    for v in values:
        b = idx[f"{v}_base"]; o = idx[f"{v}_off"]; tp_ = idx[f"{v}_temporal"]
        s_base = boot_ci.mean_ci(rates[b]); s_off = boot_ci.mean_ci(rates[o]); s_tmp = boot_ci.mean_ci(rates[tp_])
        harm = boot_ci.diff_ci(rates[b], rates[o]); rec = boot_ci.diff_ci(rates[tp_], rates[o])
        P, Plo, Phi, R, Rlo, Rhi = boot_ci.pr_ci(detTP[tp_], detFP[tp_], detFN[tp_])
        print(f"\n  {param}={v}")
        print(f"    base     {s_base[0]:5.1f}% [{s_base[1]:5.1f},{s_base[2]:5.1f}]   "
              f"off {s_off[0]:5.1f}% [{s_off[1]:5.1f},{s_off[2]:5.1f}]")
        print(f"    harm     {harm[0]:+5.1f} [{harm[1]:+5.1f},{harm[2]:+5.1f}] pp   "
              f"temporal {s_tmp[0]:5.1f}% [{s_tmp[1]:5.1f},{s_tmp[2]:5.1f}]")
        print(f"    recovery {rec[0]:+5.1f} [{rec[1]:+5.1f},{rec[2]:+5.1f}] pp   "
              f"detection P {P:.2f} [{Plo:.2f},{Phi:.2f}]  R {R:.2f} [{Rlo:.2f},{Rhi:.2f}]")
    print(f"{'='*100}")

    print(f"\n[INTERPRETATION - {sweep}]")
    if sweep == "offset":
        print("  THE STEALTH/HARM BIND (the clean demonstration). phantom_center_offset = metres from the")
        print("  hugged real obstacle's CENTRE. offset~0 => phantom ON the real obstacle: blocks ~no new")
        print("  space (harm~0) AND zero offset => temporal can't/needn't catch it (harmless). As offset")
        print("  grows => harm rises (protrudes into the corridor) AND recall rises (caught). BIND holds")
        print("  if harm and recall climb TOGETHER and temporal>=off at every offset -> no free lunch.")
    elif sweep == "gap":
        print("  STEALTH/HARM BIND holds if: as gap->0 BOTH harm AND recall fall (attacker can't be")
        print("  stealthy AND harmful); as gap grows, harm rises but recall catches it. Attacker has no")
        print("  free lunch -> temporal recovery is not gameable by hugging tighter.")
    elif sweep == "jitter":
        print("  Filter survives jitter if: recall stays ~FLAT across jitter (mean test unaffected by")
        print("  zero-mean noise). Falling recovery here would mean jitter helps -> would need disclosure.")
    elif sweep == "duty":
        print("  Soft bind holds if: recall falls with duty BUT harm falls too (less blocked time).")
        print("  A duty that keeps harm high while recall collapses would be a genuine crack -> disclose.")


if __name__ == "__main__":
    main()
