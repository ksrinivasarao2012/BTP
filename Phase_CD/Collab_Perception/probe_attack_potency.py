"""
Phase 4 GATE — false-obstacle attack potency probe (defense OFF).

Question: in THIS slot-fusion map=ON model under dropout, does a coherent Byzantine
false-obstacle broadcast actually hurt honest drones? (The earlier "deception INERT"
finding was on M0 in the original env — it must be re-verified here.)

Setup: ON model, slot_fusion=True, use_shared_map=True, dropout=0.10/sustain=5 (~33% blind).
Traitors = drones 0..k-1; each broadcasts a persistent phantom wall across the goal approach.
NO defense (no filtering). Success is counted over HONEST drones only (denominator = 10-k).

GATE: if the attack drops honest success by >= ~10 pp -> real threat -> build the defense.
      if it drops ~0-3 pp -> attack is inert here (deception-inert confirmed) -> reframe Phase 4.

Usage:
    python probe_attack_potency.py [model_path] [n_maps]
    python probe_attack_potency.py models/raster_slot_fusion_ON_stage2_final.zip 300
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

LOCAL = 130
GLOBAL = 520
K_SWEEP = [0, 1, 2, 3]              # number of traitors
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


def run_eval(model, n_traitors, n_maps, dropout=0.10, sustain=5):
    """Honest-drone success (traitors excluded from numerator AND denominator).

    Returns: (honest_success_rate %, per_map_honest_rate array).
    """
    traitor_idx = list(range(n_traitors))
    traitor_names = {f"drone_{i}" for i in traitor_idx}
    env = SwarmLidarEnv_Raster(
        render_mode=None,
        target_density=0.20,
        communication_range=10.0,
        congestion_mode="lidar",
        lidar_range=8.0,
        lidar_dropout=dropout,
        dropout_sustain=sustain,
        use_shared_map=True,
        slot_fusion=True,
        false_obstacle_attack=(n_traitors > 0),
        traitor_indices=traitor_idx,
    )
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    per_map = []

    print(f"    [k={n_traitors}, dropout={dropout}] {n_maps} maps ...", flush=True)
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
                    if a in traitor_names:                 # exclude traitors from the metric
                        continue
                    h_total += 1
                    if infos[a].get("cause") == "success":
                        h_reached += 1
            if not env.agents:
                break

        per_map.append(h_reached / h_total if h_total > 0 else 0.0)
        if (map_idx + 1) % 100 == 0:
            print(f"      ... {map_idx + 1}/{n_maps}", flush=True)

    env.close()
    rates = np.array(per_map, dtype=np.float32)
    return 100.0 * float(np.mean(rates)), rates


def bootstrap_drop_ci(base_rates, atk_rates, n_bootstrap=10000, seed=42):
    """Paired bootstrap CI on the DROP = baseline - attacked (pp)."""
    np.random.seed(seed)
    n = len(base_rates)
    drops = [
        100.0 * float(np.mean(base_rates[idx]) - np.mean(atk_rates[idx]))
        for idx in (np.random.choice(n, size=n, replace=True) for _ in range(n_bootstrap))
    ]
    drops = np.array(drops)
    return float(np.percentile(drops, 2.5)), float(np.percentile(drops, 97.5))


def resolve_path(path):
    if os.path.exists(path):
        return path
    for cand in (os.path.join("models", os.path.basename(path)), os.path.abspath(path)):
        if os.path.exists(cand):
            return cand
    return None


def sweep_k(model, n_maps, dropout=0.10, sustain=5):
    """Fixed dropout, sweep number of traitors. Each k compared to k=0 at the same dropout."""
    print(f"\n{'='*72}")
    print(f"MODE: traitor sweep | dropout={dropout}/sustain={sustain}")
    print(f"  metric: honest-drone success (traitors excluded, denom = 10-k), DEFENSE OFF")
    print(f"{'='*72}")
    rows = []
    base_rate = base_rates = None
    for k in K_SWEEP:
        rate, rates = run_eval(model, n_traitors=k, n_maps=n_maps, dropout=dropout, sustain=sustain)
        if k == 0:
            base_rate, base_rates = rate, rates
            rows.append((k, rate, 100.0 - rate, 0.0, 0.0, 0.0))
            print(f"  -> baseline (k=0): {rate:.2f}%  (fail {100.0-rate:.2f}%)")
        else:
            drop = base_rate - rate
            ci_lo, ci_hi = bootstrap_drop_ci(base_rates, rates)
            rows.append((k, rate, 100.0 - rate, drop, ci_lo, ci_hi))
            print(f"  -> k={k}: {rate:.2f}%  (fail {100.0-rate:.2f}%)  drop {drop:+.2f} pp  CI [{ci_lo:+.2f}, {ci_hi:+.2f}]")

    print(f"\n{'='*72}")
    print(f"RESULTS — honest success vs # traitors  (false-obstacle, no defense, dropout={dropout})")
    print(f"{'='*72}")
    print(f"  {'k':>2}  {'success':>8}  {'fail':>7}  {'drop':>8}  {'95% CI (drop)':>22}")
    for k, rate, fail, drop, lo, hi in rows:
        ci = "      —" if k == 0 else f"[{lo:+6.2f}, {hi:+6.2f}] pp"
        print(f"  {k:>2}  {rate:>7.2f}%  {fail:>6.2f}%  {drop:>+7.2f}pp  {ci:>22}")
    print(f"{'='*72}")
    _gate(max(r[3] for r in rows))


def sweep_dropout(model, n_maps, k_fixed=2, dropout_levels=(0.0, 0.10, 0.30), sustain=5):
    """Fixed k, sweep dropout. Each level compared to its OWN k=0 baseline at that dropout
    (higher dropout lowers baseline by itself, so the attack effect must be isolated per level)."""
    print(f"\n{'='*72}")
    print(f"MODE: dropout sweep | fixed k={k_fixed} traitors | sustain={sustain}")
    print(f"  isolating the attack: drop = (k=0 baseline) - (k={k_fixed}) AT EACH dropout level")
    print(f"  metric: honest-drone success, DEFENSE OFF")
    print(f"{'='*72}")
    rows = []
    for d in dropout_levels:
        blind = d * sustain / (1.0 + d * sustain) * 100.0
        base_rate, base_rates = run_eval(model, n_traitors=0, n_maps=n_maps, dropout=d, sustain=sustain)
        atk_rate, atk_rates = run_eval(model, n_traitors=k_fixed, n_maps=n_maps, dropout=d, sustain=sustain)
        drop = base_rate - atk_rate
        ci_lo, ci_hi = bootstrap_drop_ci(base_rates, atk_rates)
        rows.append((d, blind, base_rate, atk_rate, drop, ci_lo, ci_hi))
        print(f"  -> dropout={d} (~{blind:.0f}% blind): base {base_rate:.2f}%  atk {atk_rate:.2f}%  "
              f"drop {drop:+.2f} pp  CI [{ci_lo:+.2f}, {ci_hi:+.2f}]")

    print(f"\n{'='*72}")
    print(f"RESULTS — attack drop vs dropout severity  (k={k_fixed}, false-obstacle, no defense)")
    print(f"{'='*72}")
    print(f"  {'dropout':>7}  {'blind':>6}  {'base':>7}  {'k=%d' % k_fixed:>7}  {'drop':>8}  {'95% CI (drop)':>22}")
    for d, blind, base, atk, drop, lo, hi in rows:
        print(f"  {d:>7.2f}  {blind:>5.0f}%  {base:>6.2f}%  {atk:>6.2f}%  {drop:>+7.2f}pp  [{lo:+6.2f}, {hi:+6.2f}] pp")
    print(f"{'='*72}")
    drops = [r[4] for r in rows]
    print(f"\n[INTERPRETATION]")
    if drops[0] <= drops[-1] and drops[-1] - drops[0] >= 3.0:
        print(f"  ✓ Attack potency GROWS with dropout: {drops[0]:+.1f} -> {drops[-1]:+.1f} pp.")
        print(f"    Confirms mechanism: the lie bites inside the sensor-blind window.")
    else:
        print(f"  ~ Attack potency roughly flat across dropout: {[f'{x:+.1f}' for x in drops]}.")
        print(f"    Mechanism is not dropout-gated as hypothesized — re-examine placement.")


def _gate(max_drop):
    print(f"\n[GATE]")
    if max_drop >= 10.0:
        print(f"  ✓ Attack is potent (max drop {max_drop:.1f} pp >= 10 pp). Real threat.")
        print(f"    -> Proceed to build the consistency-trust defense.")
    elif max_drop >= 4.0:
        print(f"  ~ Attack is modest (max drop {max_drop:.1f} pp). Borderline.")
    else:
        print(f"  ✗ Attack is INERT here (max drop {max_drop:.1f} pp < 4 pp).")


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    mode = sys.argv[3].lower() if len(sys.argv) > 3 else "k"
    model_path = resolve_path(model_path)
    if model_path is None:
        print(f"[!] model not found"); return

    print(f"\n{'='*72}")
    print(f"ATTACK POTENCY PROBE | {os.path.basename(model_path)} | {n_maps} maps/cond | mode={mode}")
    print(f"{'='*72}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")

    if mode == "dropout":
        sweep_dropout(model, n_maps)
    else:
        sweep_k(model, n_maps)


if __name__ == "__main__":
    main()
