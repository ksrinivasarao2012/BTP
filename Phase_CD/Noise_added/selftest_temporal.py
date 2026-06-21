"""
STEP 3 SELF-TEST — sanity-check the temporal-trust filter before the full eval.

Runs a few sigma=0.6 CAMOUFLAGE episodes with the COMPOSED defense (single-frame robust OR
temporal) ON, then reads env._tbias and prints, per episode:
  (a) honest (ego,honest-neighbor) buckets: ||mean(d)|| should stay SMALL (< temporal_bias_eps mostly),
  (b) traitor (ego,traitor) buckets:        ||mean(d)|| should CROSS temporal_bias_eps,
  (c) predicted_traitors() P/R: temporal should now flag camouflage that single-frame missed.

Usage:
  python selftest_temporal.py [model] [n_maps] [eps] [min_k]
  python selftest_temporal.py models/noise_robust_ON_stage1_final.zip 5 0.5 10
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
_COLLAB = os.path.join(_PHASE_CD, "Collab_Perception")
for _p in (_ROOT, _PHASE_CD, _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

from probe_temporal_offset import MAPPO_Policy_M0, resolve_path   # reuse policy + path helper


def build_env(eps, min_k):
    from env_noisy_byzantine import NoisyByzantineEnv
    return NoisyByzantineEnv(
        render_mode=None, target_density=0.27, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=0.10, dropout_sustain=5, use_shared_map=True,
        false_obstacle_attack=True, traitor_indices=[0, 1],
        attack_mode="camouflage", trust_defense=True,
        sensor_noise=0.6, verify_k_sigma=4.0, trust_alpha=0.25, tau_trust=0.4,
        temporal_defense=True, temporal_bias_eps=eps, temporal_min_k=min_k,
    )


def main():
    model_path = resolve_path(sys.argv[1] if len(sys.argv) > 1 else "models/noise_robust_ON_stage1_final.zip")
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    eps = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    min_k = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    if model_path is None:
        print("[!] model not found"); return

    from stable_baselines3 import PPO
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    env = build_env(eps, min_k)
    traitor_set = {0, 1}
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

    print(f"\nSELF-TEST temporal filter | {os.path.basename(model_path)} | eps={eps} min_k={min_k} "
          f"| sigma=0.6 camouflage k=2 | {n_maps} maps")
    print("=" * 88)

    tot_TP = tot_FP = tot_FN = 0
    for mp in range(n_maps):
        attempts = 0
        while True:
            seed = 800_000_000 + 2_000_000 + mp + attempts * 5_000
            obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
            if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                break
            attempts += 1
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
            if not env.agents:
                break

        # read temporal memory: collect bucket ||mean|| split by neighbor type, only mature buckets
        hon_mags, tr_mags = [], []
        for (idx, j), buckets in env._tbias.items():
            if idx in traitor_set:
                continue                                  # verifier must be honest
            for sx, sy, c in buckets.values():
                if c < min_k:
                    continue
                mag = float(np.hypot(sx / c, sy / c))
                (tr_mags if j in traitor_set else hon_mags).append(mag)

        def stat(v):
            if not v:
                return "  (none)"
            v = np.array(v)
            return (f"n={len(v):>4}  median={np.median(v):.2f}  p90={np.percentile(v,90):.2f}  "
                    f">eps={100*np.mean(v > eps):.0f}%")

        # detection P/R for this map
        TP = FP = FN = 0
        for i, pred in env.predicted_traitors().items():
            pred = set(pred)
            TP += len(pred & traitor_set); FP += len(pred - traitor_set); FN += len(traitor_set - pred)
        tot_TP += TP; tot_FP += FP; tot_FN += FN
        p = TP / (TP + FP) if (TP + FP) else 0.0
        r = TP / (TP + FN) if (TP + FN) else 0.0

        print(f"map {mp}: honest-pair  {stat(hon_mags)}")
        print(f"       traitor-pair {stat(tr_mags)}")
        print(f"       predicted_traitors P={p:.2f} R={r:.2f}  (TP={TP} FP={FP} FN={FN})")

    P = tot_TP / (tot_TP + tot_FP) if (tot_TP + tot_FP) else 0.0
    R = tot_TP / (tot_TP + tot_FN) if (tot_TP + tot_FN) else 0.0
    print("=" * 88)
    print(f"OVERALL P={P:.2f} R={R:.2f}  (TP={tot_TP} FP={tot_FP} FN={tot_FN})")
    print("EXPECT: honest-pair median small & low >eps%%; traitor-pair median > eps & high >eps%%; R>0.")


if __name__ == "__main__":
    main()
