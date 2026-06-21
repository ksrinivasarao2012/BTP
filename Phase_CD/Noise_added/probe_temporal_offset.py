"""
TEMPORAL-TRUST PROBE A (STEP 1) — does the offset-vector signal exist with ORACLE association?

See Phase_CD/Noise_added/TEMPORAL_TRUST_RUNBOOK.md (STEP 1) for the full rationale. In short:

  For neighbor j's report of an obstacle, the per-frame OFFSET VECTOR is
      d_t = (j's reported position) - (ego's own sensed position of the matched obstacle).
  Honest j:  d_t = noise_j(t) - noise_ego(t) ~ N(0, sqrt2*sigma)  -> ZERO-MEAN, averages away.
  Liar j  :  d_t = phantom - ego_sensed(real it hugs)             -> persistent NON-ZERO bias.

  The discriminator is ||mean of d_t|| over K frames. This probe measures, on sigma=0.6
  CAMOUFLAGE episodes, the distribution of ||mean offset|| for HONEST vs PHANTOM reports using
  GROUND TRUTH to associate (so association can never be blamed). It tests the STATISTICS only.

This probe does NOT edit the env. It reads env internals from outside, after each env.step:
  env._sensed (n,M,2 noisy views), env._in_range (n,M bool), env._phantoms (P,3),
  env.obstacles (true), env.positions, env.lidar_blind, env.lidar_range, env.communication_range.

Usage:
  python probe_temporal_offset.py <model> <n_maps> [k] [n_workers] [attack_mode] [sigma]
  python probe_temporal_offset.py models/noise_robust_ON_stage1_final.zip 150 2 10 camouflage 0.6

Output: per Kmin in {1,5,10,20}, honest/phantom ||mean|| percentiles, usable-K distribution,
        AUC (rank phantom>honest by ||mean||), and the clean-gap (phantom_p10 - honest_p90).
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
KMINS = (1, 5, 10, 20)

import torch.nn as nn
from stable_baselines3.common.policies import ActorCriticPolicy


# ---- M0 actor/critic extractor (copied verbatim from eval_noise_robust.py) ----
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


def _init(model_path, cfg):
    import torch
    torch.set_num_threads(1)
    os.environ["OMP_NUM_THREADS"] = "1"
    from stable_baselines3 import PPO
    _G["model"] = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    _G["cfg"] = cfg
    _G["env"] = None


def _build_env(cfg):
    from env_noisy_byzantine import NoisyByzantineEnv
    return NoisyByzantineEnv(
        render_mode=None, target_density=0.27, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=0.10, dropout_sustain=5, use_shared_map=True,
        false_obstacle_attack=(cfg["n_traitors"] > 0),
        traitor_indices=list(range(cfg["n_traitors"])),
        attack_mode=cfg["attack_mode"], trust_defense=False,   # defense OFF: we only observe
        sensor_noise=cfg["sensor_noise"],
        verify_k_sigma=0.0, trust_alpha=0.5, tau_trust=0.5,
    )


def _accumulate(env, acc, traitor_set, lidar_range, comm_range):
    """After one env.step, add per-frame offset vectors into oracle-associated buckets.

    acc[(idx, j, key)] = [sum_x, sum_y, count, label]  (label: 0=honest, 1=phantom)
    """
    sensed = env._sensed                         # (n, M, 2) noisy views
    in_range = env._in_range                     # (n, M) bool
    M = sensed.shape[1]
    if M == 0:
        return
    obs_c = np.array([o[:2] for o in env.obstacles], dtype=np.float32)   # (M,2) true centers
    phantoms = env._phantoms                     # (P,3)
    pos = env.positions
    n = env.n_drones
    alive = [k for k in range(n) if env.possible_agents[k] in env.agents]
    blind = env.lidar_blind

    for idx in alive:
        if idx in traitor_set or blind[idx]:
            continue                              # honest, sighted verifier only
        in_i = in_range[idx]
        for j in alive:
            if j == idx:
                continue
            if np.linalg.norm(pos[idx] - pos[j]) > comm_range:
                continue
            # ---- HONEST reports of j: true obstacle m seen by BOTH (oracle: same index) ----
            if not blind[j]:
                both = in_range[j] & in_i
                for m in np.where(both)[0]:
                    if np.linalg.norm(pos[idx] - obs_c[m]) > lidar_range:
                        continue
                    d = sensed[j][m] - sensed[idx][m]
                    b = acc.setdefault((idx, j, ("real", int(m))), [0.0, 0.0, 0, 0])
                    b[0] += float(d[0]); b[1] += float(d[1]); b[2] += 1
            # ---- PHANTOM reports of j: only traitors fabricate ----
            if j in traitor_set and len(phantoms):
                for k in range(len(phantoms)):
                    p = phantoms[k, :2]
                    if np.linalg.norm(pos[idx] - p) > lidar_range:
                        continue
                    mstar = int(np.argmin(np.linalg.norm(obs_c - p[None, :], axis=1)))
                    if not in_i[mstar]:
                        continue                  # ego must sight the real obstacle the phantom hugs
                    d = p - sensed[idx][mstar]
                    b = acc.setdefault((idx, j, ("phantom", int(k))), [0.0, 0.0, 0, 1])
                    b[0] += float(d[0]); b[1] += float(d[1]); b[2] += 1


def _accumulate_realistic(env, acc, traitor_set, lidar_range, comm_range):
    """STEP 2: REALISTIC association — no ground-truth indices, no is-phantom flag in the logic.

    Neighbor j broadcasts ONE mixed list B_j = (its sighted noisy reals) ++ (phantoms if traitor),
    exactly what _fused_lidar sees at bc_c. Ego associates each broadcast obstacle to ITS OWN
    nearest sighted obstacle (track id m*), offset d = o - ego_sensed[m*]. The bucket is keyed by
    (idx, j, m*). Ground-truth (is_phantom) is recorded ONLY for post-hoc scoring labels.

    acc[(idx,j,mstar)] = {"sx","sy","n","ph"(bool, scoring only),"D"(list of [dx,dy])}
    """
    sensed = env._sensed
    in_range = env._in_range
    M = sensed.shape[1]
    if M == 0:
        return
    phantoms = env._phantoms
    pos = env.positions
    n = env.n_drones
    alive = [k for k in range(n) if env.possible_agents[k] in env.agents]
    blind = env.lidar_blind

    for idx in alive:
        if idx in traitor_set or blind[idx]:
            continue
        in_i = in_range[idx]
        ego_idx = np.where(in_i)[0]                 # ego's own sighted obstacle track-ids
        if len(ego_idx) == 0:
            continue
        ego_pts = sensed[idx][in_i]                 # ego's noisy views of its sighted obstacles
        for j in alive:
            if j == idx:
                continue
            if np.linalg.norm(pos[idx] - pos[j]) > comm_range:
                continue
            # ---- build j's mixed broadcast B_j (centers + scoring-only is_phantom flag) ----
            bc = []                                  # list of (center(2,), is_phantom)
            if not blind[j]:
                for m in np.where(in_range[j])[0]:
                    bc.append((sensed[j][m], False))
            if j in traitor_set and len(phantoms):
                for k in range(len(phantoms)):
                    bc.append((phantoms[k, :2], True))
            if not bc:
                continue
            for o, is_ph in bc:
                if np.linalg.norm(pos[idx] - o) > lidar_range:
                    continue                         # ego can only verify what's in its own range
                a = int(np.argmin(np.linalg.norm(ego_pts - o[None, :], axis=1)))
                mstar = int(ego_idx[a])
                d = np.asarray(o, dtype=np.float32) - ego_pts[a]
                b = acc.setdefault((idx, j, mstar),
                                   {"sx": 0.0, "sy": 0.0, "n": 0, "ph": False, "D": []})
                b["sx"] += float(d[0]); b["sy"] += float(d[1]); b["n"] += 1
                b["D"].append((float(d[0]), float(d[1])))
                if is_ph:
                    b["ph"] = True                   # bucket contains >=1 phantom (label only)


def _two_means(D, iters=12):
    """Tiny 2-means on 2D points. Returns [(centroid(2,), size), (centroid(2,), size)]."""
    N = len(D)
    mean = D.mean(0)
    c0 = D[int(np.argmax(np.linalg.norm(D - mean, axis=1)))].copy()
    c1 = D[int(np.argmax(np.linalg.norm(D - c0, axis=1)))].copy()
    cents = np.stack([c0, c1])
    lab = np.zeros(N, dtype=int)
    for _ in range(iters):
        dist = np.linalg.norm(D[:, None, :] - cents[None, :, :], axis=2)
        lab = dist.argmin(1)
        new = cents.copy()
        for c in (0, 1):
            if (lab == c).any():
                new[c] = D[lab == c].mean(0)
        if np.allclose(new, cents):
            break
        cents = new
    return [(cents[c], int((lab == c).sum())) for c in (0, 1)]


def _cluster_stat(D):
    """Robust-to-mixing statistic: largest persistent (non-trivial-size) cluster centroid norm.

    A bucket that mixes a fixed phantom bias with honest zero-mean reports of the same obstacle
    still has ONE cluster whose centroid is the phantom bias; honest-only buckets have both
    clusters near zero. This catches phantoms even when the plain mean is diluted by mixing.
    """
    D = np.asarray(D, dtype=float)
    N = len(D)
    if N == 0:
        return 0.0
    if N < 4:
        return float(np.linalg.norm(D.mean(0)))
    best = 0.0
    for cent, sz in _two_means(D):
        if sz >= max(2, int(0.2 * N)):
            best = max(best, float(np.linalg.norm(cent)))
    return best


def _run(map_idx):
    cfg = _G["cfg"]
    if _G["env"] is None:
        _G["env"] = _build_env(cfg)
    env, model = _G["env"], _G["model"]

    n_traitors = cfg["n_traitors"]
    assoc = cfg["assoc"]
    traitor_set = set(range(n_traitors))
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    lidar_range = env.lidar_range
    comm_range = env.communication_range

    attempts = 0
    while True:
        seed = 800_000_000 + int(0.20 * 100) * 10_000 + map_idx + attempts * 5_000
        obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
        if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
            break
        attempts += 1

    acc = {}
    finished = set()
    while True:
        active = [a for a in obs_dict.keys() if a not in finished]
        if not active:
            break
        obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
        act, _ = model.predict(obs_batch, deterministic=True)
        action = {a: act[k] for k, a in enumerate(active)}
        obs_dict, _, terms, truncs, infos = env.step(action)
        if assoc == "realistic":
            _accumulate_realistic(env, acc, traitor_set, lidar_range, comm_range)
        else:
            _accumulate(env, acc, traitor_set, lidar_range, comm_range)
        for a in active:
            if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                finished.add(a)
        if not env.agents:
            break

    out = []
    if assoc == "realistic":
        # emit (label, mean_bias_mag, cluster_stat, count) per bucket
        for key, b in acc.items():
            c = b["n"]
            if c <= 0:
                continue
            mean_mag = float(np.hypot(b["sx"] / c, b["sy"] / c))
            cstat = _cluster_stat(b["D"])
            out.append((1 if b["ph"] else 0, mean_mag, cstat, c))
    else:
        # emit (label, mag, count) per bucket
        for (idx, j, key), (sx, sy, c, label) in acc.items():
            if c <= 0:
                continue
            mag = float(np.hypot(sx / c, sy / c))
            out.append((label, mag, c))
    return out


def resolve_path(path):
    if os.path.exists(path):
        return path
    for c in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(c):
            return c
    return None


def _rankdata_avg(a):
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    sa = a[order]
    i = 0
    n = len(a)
    while i < n:
        j = i
        while j + 1 < n and sa[j + 1] == sa[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _auc(honest, phantom):
    """P(mag_phantom > mag_honest), tie=0.5, via Mann-Whitney U."""
    nh, np_ = len(honest), len(phantom)
    if nh == 0 or np_ == 0:
        return float("nan")
    ranks = _rankdata_avg(np.concatenate([honest, phantom]))
    U = ranks[nh:].sum() - np_ * (np_ + 1) / 2.0
    return float(U / (nh * np_))


def _pcts(a, ps):
    if len(a) == 0:
        return [float("nan")] * len(ps)
    return [float(np.percentile(a, p)) for p in ps]


def _report_table(name, labels, stat, counts, p_label):
    """Print a per-Kmin separation table for one statistic (oracle mag, or realistic mean/cluster)."""
    hdr = (f"  {'Kmin':>4} | {'#hon':>5} {'#pha':>5} | "
           f"{'hon p50/p75/p90/p95':>26} | {'pha p5/p10/p25/p50':>24} | "
           f"{'AUC':>5} | {'clean-gap':>9}")
    print(f"\n[{name}]  (separability of {p_label})")
    print(hdr)
    print(f"  {'-'*(len(hdr)-2)}")
    for kmin in KMINS:
        sel = counts >= kmin
        hon = stat[sel & (labels == 0)]
        pha = stat[sel & (labels == 1)]
        hp = _pcts(hon, (50, 75, 90, 95))
        pp = _pcts(pha, (5, 10, 25, 50))
        auc = _auc(hon, pha)
        gap = (pp[1] - hp[2]) if (len(hon) and len(pha)) else float("nan")
        print(f"  {kmin:>4} | {len(hon):>5} {len(pha):>5} | "
              f"{hp[0]:>5.2f}/{hp[1]:.2f}/{hp[2]:.2f}/{hp[3]:.2f}      | "
              f"{pp[0]:>4.2f}/{pp[1]:.2f}/{pp[2]:.2f}/{pp[3]:.2f}    | "
              f"{auc:>5.2f} | {gap:>+8.2f}")


def main():
    argv = [a for a in sys.argv[1:]]
    assoc = "oracle"
    if "--assoc" in argv:
        i = argv.index("--assoc")
        assoc = argv[i + 1] if i + 1 < len(argv) else "realistic"
        del argv[i:i + 2]
    model_path = argv[0] if len(argv) > 0 else DEFAULT_MODEL
    n_maps = int(argv[1]) if len(argv) > 1 else 150
    k = int(argv[2]) if len(argv) > 2 else 2
    n_workers = int(argv[3]) if len(argv) > 3 else 10
    attack_mode = argv[4] if len(argv) > 4 else "camouflage"
    sigma = float(argv[5]) if len(argv) > 5 else 0.6
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    cfg = dict(n_traitors=k, attack_mode=attack_mode, sensor_noise=sigma, assoc=assoc)
    tasks = list(range(n_maps))

    title = "PROBE A (oracle assoc)" if assoc != "realistic" else "PROBE B (REALISTIC assoc)"
    print(f"\n{'='*92}")
    print(f"TEMPORAL-TRUST {title} | {os.path.basename(model_path)} | "
          f"sigma={sigma} | k={k} | {attack_mode} | {n_maps} maps | {n_workers}w")
    print(f"  measuring ||mean offset vector|| : honest (zero-mean) vs phantom (biased)")
    print(f"{'='*92}", flush=True)

    buckets = []
    done = 0
    chunk = max(1, n_maps // max(1, n_workers))
    with Pool(n_workers, initializer=_init, initargs=(model_path, cfg)) as pool:
        for out in pool.imap(_run, tasks, chunksize=chunk):
            buckets.extend(out)
            done += 1
            if done % max(1, n_maps // 10) == 0:
                print(f"  ... {done}/{n_maps} maps ({100*done/n_maps:.0f}%) | {len(buckets)} buckets", flush=True)

    if not buckets:
        print("[!] no buckets collected (no in-range honest/phantom co-sightings?)"); return

    labels = np.array([b[0] for b in buckets])

    if assoc == "realistic":
        mean_mag = np.array([b[1] for b in buckets])
        cluster = np.array([b[2] for b in buckets])
        counts = np.array([b[3] for b in buckets])
        print(f"\n{'='*92}")
        print(f"RESULTS — REALISTIC association, sigma={sigma} {attack_mode}")
        print(f"  total buckets: {len(buckets)}  (honest-only {int((labels==0).sum())}, "
              f"phantom-containing {int((labels==1).sum())})")
        print(f"  NOTE: realistic buckets MIX honest+phantom reports of the same obstacle, so a")
        print(f"        phantom-containing bucket's plain mean is DILUTED -> cluster stat is the rescue.")
        print(f"{'='*92}")
        _report_table("mean-bias  ||mean(d)||", labels, mean_mag, counts, "plain vector mean")
        _report_table("cluster    max||centroid||", labels, cluster, counts, "2-mode cluster centroid")
    else:
        mags = np.array([b[1] for b in buckets])
        counts = np.array([b[2] for b in buckets])
        print(f"\n{'='*92}")
        print(f"RESULTS — ||mean offset|| separation by usable-K (Kmin), sigma={sigma} {attack_mode}")
        print(f"  total buckets: {len(buckets)}  (honest {int((labels==0).sum())}, phantom {int((labels==1).sum())})")
        print(f"{'='*92}")
        _report_table("oracle  ||mean(d)||", labels, mags, counts, "vector mean")

    print(f"{'='*92}")

    # usable-K (count) distribution per class
    hc = counts[labels == 0]
    pc = counts[labels == 1]
    print(f"\nUsable-K (frames per bucket) distribution:")
    print(f"  honest : median {np.median(hc):.0f}  p10 {np.percentile(hc,10):.0f}  "
          f"p90 {np.percentile(hc,90):.0f}  max {hc.max():.0f}")
    if len(pc):
        print(f"  phantom: median {np.median(pc):.0f}  p10 {np.percentile(pc,10):.0f}  "
              f"p90 {np.percentile(pc,90):.0f}  max {pc.max():.0f}")

    if assoc == "realistic":
        print(f"\n[DECISION GATE — STEP 2]")
        print(f"  GREEN if: realistic AUC>=0.80 (mean-bias OR cluster) -> build the filter (STEP 3)")
        print(f"  AMBER if: only the cluster statistic separates       -> build with cluster stat")
        print(f"  RED   if: AUC<0.75 with realistic assoc (STEP1 was GREEN) -> association is the wall")
    else:
        print(f"\n[DECISION GATE — STEP 1]")
        print(f"  GREEN if: AUC>=0.85 AND honest_p90<phantom_p10 at some Kmin<=10 AND median usable-K>=that Kmin")
        print(f"  AMBER if: AUC>=0.85 only at Kmin=20 but median usable-K<10")
        print(f"  RED   if: AUC<0.75 even with oracle assoc at Kmin=20  -> STOP, fundamental limit stands")


if __name__ == "__main__":
    main()
