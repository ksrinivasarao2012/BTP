"""
probe_comm_oracle.py — COMMUNICATION VALUE ORACLE (UPPER BOUND)

PURPOSE
-------
Answers: "Does perfect exploitation of communication give measurable benefit over
LiDAR-only at short LiDAR ranges?" — BEFORE committing to a 20M-step from-scratch train.

SCIENTIFIC RATIONALE
--------------------
From Phase B (ABLATION_RESULTS.md Finding 3):
  - At LiDAR=12m, ALL drone-drone avoidance is done by LiDAR (0% drone-drone collisions
    even at comm=0 retrained). Communication's value was purely indirect (smoother
    coordination -> fewer obstacle hits).
  - At LiDAR=4m, max_velocity=2.0m/s: head-on closing speed = 4m/s, braking time ~2s.
    LiDAR react window = 4m/4m/s = 1.0s  < 2.0s braking = CANNOT STOP IN TIME.
    Comm react window = 10m/4m/s = 2.5s  > 2.0s braking = CAN ADJUST IN TIME.
  - So at LiDAR=4m there is a PHYSICAL WINDOW (4-10m) where comm provides advance warning
    that LiDAR cannot. This probe tests whether a PERFECT oracle acting on that info helps.

ORACLE LOGIC (perfect-information upper bound)
----------------------------------------------
For each drone, at each timestep:
  1. Using TRUE env positions (oracle has ground truth), find all active neighbors in the
     "comm-only annulus": LIDAR_RANGE < dist <= COMM_RANGE  (4m < dist <= 10m).
     These are drones the drone CAN hear via comm but CANNOT see via LiDAR.
  2. Compute TTC (time-to-collision) = dist / closing_speed for each such neighbor.
  3. If any annulus neighbor has TTC < TTC_THRESH (i.e. on a collision course):
     -> Override action with a PROACTIVE DODGE: steer perpendicular to the threat,
        biased toward the goal direction (like a gentle lane-change).
  4. LiDAR-visible neighbors (dist <= LIDAR_RANGE) are handled by the policy as normal.

If this oracle improves success rate over the baseline policy:
  -> Communication carries non-redundant, exploitable value at LiDAR=4m.
  -> From-scratch training at LiDAR=4m, comm=10m is scientifically justified.

If this oracle shows no improvement:
  -> Even perfect communication exploitation doesn't help -> the task is fundamentally
     LiDAR-limited at this range -> training from scratch will not learn to use comm.

Usage:
  python Phase_CD/probe_comm_oracle.py [model_path] [n_maps]
  python Phase_CD/probe_comm_oracle.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30

Defaults: M0, 30 maps. Output: Phase_CD/results/comm_oracle_lidar4_comm10.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"

from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

# --- run from anywhere; repo root + script dir on path ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
# ----------------------------------------------------------
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

# ======== Configuration ========
LIDAR_RANGE  = 4.0    # short-LiDAR regime under test
COMM_RANGE   = 10.0   # communication range (annulus outer boundary)
DENSITIES    = [0.20, 0.30]
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
DEFAULT_MAPS  = 30

# Oracle tuning
TTC_THRESH   = 2.2    # seconds: if time-to-collision < this, trigger proactive dodge
                      # justified: at 4m/s closing and 4m LiDAR, 2s braking needed;
                      # 2.2s gives the oracle a small lead on the 2.0s braking time
MIN_CLOSING  = 0.3    # m/s: ignore near-stationary neighbors (no real threat)
CLEAR_THRESH = 2.0    # m: LiDAR sector must return > this to be considered open

# 16 sector centre directions (matching env's ray layout)
_SECTOR_DIRS = np.array(
    [[np.cos(k * 2 * np.pi / 16), np.sin(k * 2 * np.pi / 16)] for k in range(16)],
    dtype=np.float32
)
# ================================


class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], 130
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]
            last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], 520
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]
            last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi  = last
        self.latent_dim_vf  = last_vf

    def forward(self, f):
        return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f):
        return self.policy_net(f[:, :130])
    def forward_critic(self, f):
        return self.value_net(f[:, 130:])


class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(
            self.features_dim, self.net_arch, self.activation_fn)


def proactive_dodge(pos, vel, threat_pos, threat_vel, obs_vec, to_goal_dir):
    """
    Oracle override: steer perpendicular to the approaching threat,
    biased toward the goal direction.  LiDAR-aware: prefer the perpendicular
    that points into a clear sector.

    obs_vec[6:22] = LiDAR min distances for 16 sectors (normalised by lidar_range).
    We read them back in metres here.
    """
    lid_min = obs_vec[6:22] * LIDAR_RANGE          # metres, shape (16,)

    # Vector from us to threat
    rel = threat_pos - pos
    dist = np.linalg.norm(rel)
    if dist < 1e-6:
        return to_goal_dir.astype(np.float32)

    # Two perpendicular options
    perp1 = np.array([-rel[1],  rel[0]], dtype=np.float32) / dist
    perp2 = np.array([ rel[1], -rel[0]], dtype=np.float32) / dist

    # Score each by (a) agreement with goal direction and (b) LiDAR clearance
    def score(perp):
        goal_align = float(np.dot(perp, to_goal_dir))
        # Find best matching sector for this perpendicular
        dots = _SECTOR_DIRS @ perp
        best_k = int(np.argmax(dots))
        clearance = float(lid_min[best_k]) / LIDAR_RANGE  # 0-1
        return 0.4 * goal_align + 0.6 * clearance

    chosen = perp1 if score(perp1) >= score(perp2) else perp2
    return chosen.astype(np.float32)


def run_condition(model, n_maps, densities, oracle_active, label):
    """
    Run n_maps episodes per density.
    oracle_active=True  -> override action when comm-only annulus neighbor is on collision course
    oracle_active=False -> pure policy (baseline)
    Returns list of result dicts.
    """
    results = []
    for density in densities:
        env = SwarmLidarEnv_StepB10_8_0m(
            render_mode=None,
            target_density=density,
            communication_range=COMM_RANGE,
            congestion_mode="lidar",
            lidar_range=LIDAR_RANGE
        )
        amap = env.agent_name_mapping  # name -> idx

        reached = timeout = coll = total = 0
        coll_drone = coll_obstacle = coll_wall = 0
        oracle_triggers = 0   # how many times the oracle actually fired

        for map_idx in range(n_maps):
            # ---- solvable-map gate (same seeds as eval_shortlidar) ----
            attempts = 0
            while True:
                seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[amap[a]])
                       for a in env.possible_agents):
                    break
                attempts += 1

            finished = set()
            while True:
                active = [a for a in obs_dict if a not in finished]
                if not active:
                    break

                obs_batch = np.array([obs_dict[a] for a in active])
                act_batch, _ = model.predict(obs_batch, deterministic=True)

                action = {}
                for k, agent in enumerate(active):
                    idx   = amap[agent]
                    pos   = env.positions[idx].copy()
                    vel   = env.velocities[idx].copy()
                    a_pol = act_batch[k]

                    override = False
                    if oracle_active:
                        # --- find the to_goal direction for scoring ---
                        to_goal = env.get_shortest_path_direction(pos)

                        # --- scan comm-only annulus ---
                        for j in range(env.n_drones):
                            if j == idx:
                                continue
                            if env.possible_agents[j] not in env.agents:
                                continue
                            t_pos  = env.positions[j]
                            t_vel  = env.velocities[j]
                            rel    = t_pos - pos
                            dist   = float(np.linalg.norm(rel))

                            # Must be in comm-only annulus: beyond LiDAR, within comm
                            if not (LIDAR_RANGE < dist <= COMM_RANGE):
                                continue

                            # Compute closing speed (positive = approaching)
                            if dist < 1e-6:
                                continue
                            rel_vel = vel - t_vel          # our vel minus their vel
                            closing = float(np.dot(rel_vel, rel / dist))  # >0 = closing

                            if closing < MIN_CLOSING:
                                continue  # not approaching fast enough to matter

                            ttc = dist / closing
                            if ttc < TTC_THRESH:
                                # Oracle fires: proactive dodge
                                a_pol = proactive_dodge(
                                    pos, vel, t_pos, t_vel, obs_dict[agent], to_goal)
                                oracle_triggers += 1
                                override = True
                                break  # handle one threat at a time

                    action[agent] = a_pol

                obs_dict, _, terms, truncs, infos = env.step(action)

                for agent in active:
                    if (terms.get(agent, False) or truncs.get(agent, False)) \
                            and agent not in finished:
                        finished.add(agent)
                        total += 1
                        cause = infos[agent].get("cause")
                        if cause == "success":
                            reached += 1
                        elif cause == "timeout":
                            timeout += 1
                        elif cause == "collision":
                            coll += 1
                            ct = infos[agent].get("collision_type", "unknown")
                            if ct == "drone":     coll_drone += 1
                            elif ct == "obstacle": coll_obstacle += 1
                            elif ct == "wall":     coll_wall += 1

                if not env.agents:
                    break

        env.close()
        denom = max(total, 1)
        row = {
            "condition":         label,
            "oracle_active":     oracle_active,
            "lidar_range":       LIDAR_RANGE,
            "comm_range":        COMM_RANGE,
            "density":           density,
            "n_maps":            n_maps,
            "success":           100.0 * reached    / denom,
            "timeout":           100.0 * timeout    / denom,
            "collision":         100.0 * coll       / denom,
            "collision_drone":   100.0 * coll_drone    / denom,
            "collision_obstacle":100.0 * coll_obstacle / denom,
            "collision_wall":    100.0 * coll_wall     / denom,
            "oracle_triggers":   oracle_triggers,
        }
        results.append(row)
        print(
            f"  [{label}] d={density:.2f}: success={row['success']:.2f}%  "
            f"coll={row['collision']:.2f}% (drone {row['collision_drone']:.2f}% "
            f"obst {row['collision_obstacle']:.2f}%)  "
            f"oracle_fires={oracle_triggers}"
        )
    return results


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps     = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAPS

    print("=" * 70)
    print("COMM VALUE ORACLE PROBE")
    print(f"  model      : {model_path}")
    print(f"  LiDAR      : {LIDAR_RANGE} m   |   comm : {COMM_RANGE} m")
    print(f"  annulus    : {LIDAR_RANGE}–{COMM_RANGE} m  (comm-only zone under test)")
    print(f"  TTC thresh : {TTC_THRESH} s   |   maps : {n_maps}")
    print()
    print("SCIENCE: at LiDAR=4m, react window = 4m/4m/s = 1.0s < 2.0s braking.")
    print("         Comm at 10m gives 2.5s warning. Oracle tests if that window helps.")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}")
        sys.exit(1)

    model = PPO.load(model_path,
                     custom_objects={"policy_class": MAPPO_Policy_B5},
                     device="cpu")

    all_rows = []

    print("\n--- BASELINE (policy only, no oracle, LiDAR=4m, comm=10m) ---")
    all_rows += run_condition(model, n_maps, DENSITIES,
                              oracle_active=False, label="baseline_lidar4")

    print("\n--- ORACLE  (perfect comm-only annulus awareness + proactive dodge) ---")
    all_rows += run_condition(model, n_maps, DENSITIES,
                              oracle_active=True,  label="oracle_comm_annulus")

    # ---- summary ----
    print("\n" + "=" * 70)
    print("SUMMARY -- comm_value = oracle_success - baseline_success")
    print("=" * 70)
    df = pd.DataFrame(all_rows)
    for density in DENSITIES:
        base = df[(df["condition"] == "baseline_lidar4") & (df["density"] == density)]
        orac = df[(df["condition"] == "oracle_comm_annulus") & (df["density"] == density)]
        if len(base) and len(orac):
            b_s  = float(base["success"].iloc[0])
            o_s  = float(orac["success"].iloc[0])
            b_dc = float(base["collision_drone"].iloc[0])
            o_dc = float(orac["collision_drone"].iloc[0])
            b_oc = float(base["collision_obstacle"].iloc[0])
            o_oc = float(orac["collision_obstacle"].iloc[0])
            cv   = o_s - b_s
            print(f"\n  density={density:.2f}:")
            print(f"    baseline  : success={b_s:.2f}%  drone_coll={b_dc:.2f}%  obst_coll={b_oc:.2f}%")
            print(f"    oracle    : success={o_s:.2f}%  drone_coll={o_dc:.2f}%  obst_coll={o_oc:.2f}%")
            print(f"    comm_value = {cv:+.2f} pp")
            print()

    print("DECISION RULE:")
    print("  comm_value >= +3 pp  -> comm CAN add value at LiDAR=4m")
    print("                          -> from-scratch training (20M steps) IS justified")
    print("  comm_value ~  0 pp   -> even perfect exploitation doesn't help")
    print("                          -> LiDAR-4m is fundamentally comm-insensitive")
    print("                          -> do NOT spend 20M steps; reconsider regime")
    print("  oracle_triggers=0    -> no drone ever entered the comm-only annulus during")
    print("                          a threat -> physical collision geometry doesn't use it")
    print("=" * 70)

    out_dir = os.path.join("Phase_CD", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "comm_oracle_lidar4_comm10.csv")
    df.to_csv(out_path, index=False)
    print(f"\n[OK] results saved: {out_path}")


if __name__ == "__main__":
    main()
