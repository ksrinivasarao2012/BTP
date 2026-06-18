"""
Phase 4 — naive ("wall") vs proper ("camouflage") attack, each with defense OFF/ON.

Fixed k traitors (default 2). For each attack mode it reports honest-drone success
(traitors excluded, denom = 10-k), the attack drop vs the clean baseline, the trust-defense
recovery (+CI), and the filter's traitor-detection precision/recall.

The expected story: the camouflaged attack is harder to detect (lower precision/recall and/or
smaller recovery) than the wall attack -> exposes the real limit of consistency filtering.

Usage:
    python eval_attack_modes.py [model_path] [n_maps] [k]
    python eval_attack_modes.py models/raster_slot_fusion_ON_stage2_final.zip 300 2
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
from env_byzantine_adaptive import AdaptiveByzantineEnv

LOCAL = 130
GLOBAL = 520
DEFAULT_MODEL = "models/raster_slot_fusion_ON_stage2_final.zip"


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


def run_eval(model, n_traitors, attack_mode, defense, n_maps, dropout=0.10, sustain=5):
    """Returns (honest_success %, per_map_rates, (TP, FP, FN))."""
    traitor_idx = list(range(n_traitors))
    traitor_set = set(traitor_idx)
    traitor_names = {f"drone_{i}" for i in traitor_idx}
    env = AdaptiveByzantineEnv(
        render_mode=None, target_density=0.20, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=dropout, dropout_sustain=sustain, use_shared_map=True,
        false_obstacle_attack=(n_traitors > 0), traitor_indices=traitor_idx,
        attack_mode=attack_mode, trust_defense=defense,
    )
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    per_map = []
    TP = FP = FN = 0

    print(f"    [{attack_mode}/{'DEF' if defense else 'off'}] {n_maps} maps ...", flush=True)
    for map_idx in range(n_maps):
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

        per_map.append(h_reached / h_total if h_total > 0 else 0.0)
        if defense and n_traitors > 0:
            for i, pred in env.predicted_traitors().items():
                pred = set(pred)
                TP += len(pred & traitor_set)
                FP += len(pred - traitor_set)
                FN += len(traitor_set - pred)
        if (map_idx + 1) % 100 == 0:
            print(f"      ... {map_idx + 1}/{n_maps}", flush=True)

    env.close()
    rates = np.array(per_map, dtype=np.float32)
    return 100.0 * float(np.mean(rates)), rates, (TP, FP, FN)


def bootstrap_ci(a_rates, b_rates, n_bootstrap=10000, seed=42):
    np.random.seed(seed)
    n = len(a_rates)
    diffs = [100.0 * float(np.mean(a_rates[idx]) - np.mean(b_rates[idx]))
             for idx in (np.random.choice(n, size=n, replace=True) for _ in range(n_bootstrap))]
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
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    print(f"\n{'='*82}")
    print(f"ATTACK-MODE COMPARISON | {os.path.basename(model_path)} | {n_maps} maps/cond | k={k}")
    print(f"  regime: map=ON, 8m LiDAR, dropout=0.10/sustain=5 (~33% blind)")
    print(f"  metric: honest-drone success (traitors excluded, denom=10-k)")
    print(f"{'='*82}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")

    base_rate, _, _ = run_eval(model, 0, "wall", False, n_maps)   # clean baseline (no attack)
    print(f"  -> clean baseline (k=0): {base_rate:.2f}%")

    results = {}
    for mode in ("wall", "camouflage"):
        off_rate, off_rates, _ = run_eval(model, k, mode, False, n_maps)
        on_rate, on_rates, det = run_eval(model, k, mode, True, n_maps)
        recov_lo, recov_hi = bootstrap_ci(on_rates, off_rates)
        results[mode] = (off_rate, on_rate, on_rate - off_rate, recov_lo, recov_hi, det)
        print(f"  -> {mode}: off {off_rate:.2f}%  ON {on_rate:.2f}%  recovery {on_rate-off_rate:+.2f} pp")

    print(f"\n{'='*82}")
    print(f"RESULTS — k={k} | clean baseline = {base_rate:.2f}%")
    print(f"{'='*82}")
    print(f"  {'attack':>11}  {'no-def':>7}  {'drop':>7}  {'defense':>7}  {'recovery':>9}  {'CI(recov)':>18}  {'P/R':>10}")
    for mode in ("wall", "camouflage"):
        off, on, recov, lo, hi, (TP, FP, FN) = results[mode]
        drop = base_rate - off
        prec = TP / (TP + FP) if (TP + FP) else 0.0
        rec = TP / (TP + FN) if (TP + FN) else 0.0
        print(f"  {mode:>11}  {off:>6.2f}%  {drop:>+6.2f}  {on:>6.2f}%  {recov:>+8.2f}pp  [{lo:+5.1f},{hi:+5.1f}]  {prec:>4.2f}/{rec:<4.2f}")
    print(f"{'='*82}")

    print(f"\n[INTERPRETATION]")
    w_drop = base_rate - results["wall"][0]
    c_drop = base_rate - results["camouflage"][0]
    w_rec = results["wall"][2]
    c_rec = results["camouflage"][2]
    print(f"  wall:       drop {w_drop:+.1f} pp, defense recovers {w_rec:+.1f} pp")
    print(f"  camouflage: drop {c_drop:+.1f} pp, defense recovers {c_rec:+.1f} pp")
    if c_rec < w_rec - 2.0:
        print(f"  -> Camouflage is harder for the defense (less recovery). Honest limit demonstrated.")
    elif c_drop < w_drop - 2.0:
        print(f"  -> Camouflage is less harmful (stealth/harm tradeoff: hugging real obstacles")
        print(f"     blocks little new space). Attacker is boxed in by consistency filtering.")
    else:
        print(f"  -> Both modes behave similarly; report both and discuss the tradeoff.")


if __name__ == "__main__":
    main()
