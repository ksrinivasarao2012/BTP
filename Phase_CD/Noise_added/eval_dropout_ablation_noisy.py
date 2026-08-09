"""
Anchor / dropout ablation on the ATTACKED model (noise_robust_ON) in its NATIVE env.

Motivation (finding: anchor-vs-contribution MODEL MISMATCH): the paper's anchor uses the
raster_slot_fusion_OFF model, but the whole attack/defense contribution runs on
noise_robust_ON. This script gives the ATTACKED model its OWN "sharing is load-bearing"
number, in the SAME env (NoisyByzantineEnv) + seeding as the attack/defense base column,
so the paper can be told on ONE model lineage.

Construction = single-policy information ablation (same weights both arms), attack OFF
(n_traitors=0), noise 0, use_shared_map toggled, dropout swept 0/10/20%.

SANITY TARGET: the 10% (~33% blind) ON row should reproduce the attack/defense base
(~86% at sigma=0), because that base IS this model, sharing ON, no attack, dropout 0.10.

Usage:
  python eval_dropout_ablation_noisy.py [model] [n_maps] [density] [n_workers]
  python eval_dropout_ablation_noisy.py models/noise_robust_ON_stage2_final.zip 500 0.27 10
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

from eval_temporal import MAPPO_Policy_M0      # EXACT policy class behind the base numbers
from env_noisy_byzantine import NoisyByzantineEnv

SWEEP = [(0.00, 5, "0%", " 0%"), (0.10, 5, "10%", "33%"), (0.20, 5, "20%", "50%")]
DEFAULT_MODEL = "models/noise_robust_ON_stage2_final.zip"

_G = {}


def _init(model_path, density):
    from stable_baselines3 import PPO
    import torch
    torch.set_num_threads(1)
    # n_envs/n_steps overrides shrink the (inference-unused) rollout buffer: noise_robust was
    # trained with 100 envs -> a 508 MiB buffer per worker OOMs the pool. Policy weights unaffected.
    _G["model"] = PPO.load(model_path, custom_objects={
        "policy_class": MAPPO_Policy_M0, "n_envs": 1, "n_steps": 4}, device="cpu")
    _G["density"] = density
    _G["envs"] = {}


def _get_env(dropout, sustain, use_shared):
    key = (dropout, sustain, use_shared)
    if key not in _G["envs"]:
        # kwargs mirror eval_temporal._build_env EXACTLY, except: attack OFF, noise 0,
        # use_shared_map toggled, lidar_dropout swept.
        _G["envs"][key] = NoisyByzantineEnv(
            render_mode=None, target_density=_G["density"], communication_range=10.0,
            congestion_mode="lidar", lidar_range=8.0,
            lidar_dropout=dropout, dropout_sustain=sustain, use_shared_map=use_shared,
            false_obstacle_attack=False, traitor_indices=[],
            randomize_attack=False, n_phantom_range=(3, 6),
            attack_mode="camouflage", trust_defense=False,
            sensor_noise=0.0, verify_k_sigma=4.0, trust_alpha=0.25, tau_trust=0.4,
            temporal_defense=False, temporal_bias_eps=0.6, temporal_min_k=20,
            comm_loss=0.0)
    return _G["envs"][key]


def _run(task):
    level_idx, dropout, sustain, use_shared, map_idx = task
    env, model = _get_env(dropout, sustain, use_shared), _G["model"]
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    attempts = 0
    while True:
        # SAME seed formula as eval_temporal (int(0.20*100), NOT density) -> same map set as the base column.
        seed = 800_000_000 + int(0.20 * 100) * 10_000 + map_idx + attempts * 5_000
        obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
        if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
            break
        attempts += 1
    reached = total = 0
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
                finished.add(a); total += 1
                if infos[a].get("cause") == "success":
                    reached += 1
        if not env.agents:
            break
    return level_idx, use_shared, map_idx, (reached / total if total > 0 else 0.0)


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
    print(f"ANCHOR/DROPOUT ABLATION on the ATTACKED model (NoisyByzantineEnv)")
    print(f"  {n_maps} maps  |  density={density}  |  {n_workers}w  |  attack OFF, noise 0")
    print(f"  model : {os.path.basename(model_path)}  (use_shared_map toggled)")
    print(f"  SANITY: 10% ON row should reproduce the attack/defense base (~86% @ sigma=0).")
    print(f"{'='*72}\n", flush=True)

    tasks = []
    for level_idx, (dropout, sustain, d_label, blind_label) in enumerate(SWEEP):
        for map_idx in range(n_maps):
            tasks.append((level_idx, dropout, sustain, True,  map_idx))
            tasks.append((level_idx, dropout, sustain, False, map_idx))

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
    print(f"RESULTS -- drone-level success (attacked model, single-policy ablation)")
    print(f"{'='*72}")
    print(f"  {'Dropout':>7}  {'Blind':>5}  {'ON':>7}  {'OFF':>7}  {'Gap':>8}  {'95% CI (gap)':>20}")
    for d_label, blind_label, on_r, off_r, gap, ci_lo, ci_hi in rows:
        print(f"  {d_label:>7}  {blind_label:>5}  {on_r:>6.2f}%  {off_r:>6.2f}%  {gap:>+7.2f}pp  [{ci_lo:+6.2f}, {ci_hi:+6.2f}] pp")
    print(f"{'='*72}")
    print(f"\n[INTERPRETATION]")
    print(f"  [i] 10% ON should be ~86 (matches base). If so, the attacked model has its own")
    print(f"      sharing-load-bearing number and the paper is one model lineage.")


if __name__ == "__main__":
    main()
