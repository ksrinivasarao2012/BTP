#!/usr/bin/env python3
"""
Evaluation Script for Trained Swarm Navigation Models

Evaluates a trained PPO model on fresh unseen maps.
Reports individual drone success rate with 95% Wilson CI.
This is the primary metric for the paper.

USAGE:
  python evaluate.py --model checkpoints/phase1/model_stage5.zip
  python evaluate.py --model checkpoints/phase2/model_stage5.zip --communication
  python evaluate.py --model checkpoints/phase1/model_stage5.zip --density 0.10
  python evaluate.py --model checkpoints/phase1/model_stage5.zip --episodes 200
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import warnings
warnings.filterwarnings("ignore")

import sys
import json
import argparse
import numpy as np
from datetime import datetime
from collections import deque
from stable_baselines3 import PPO

from gym_wrapper import SwarmVecEnv

N_DRONES = 10


# ====================================================================
# WILSON SCORE INTERVAL (95% CI for binary proportions)
# ====================================================================
def wilson_ci(successes, total):
    if total == 0:
        return 0.0, 0.0, 0.0
    p_hat = successes / total
    z = 1.96
    z_sq = z * z
    denom = 1 + z_sq / total
    center = (p_hat + z_sq / (2 * total)) / denom
    margin = z * np.sqrt(p_hat * (1 - p_hat) / total + z_sq / (4 * total * total)) / denom
    return max(0.0, center - margin), center, min(1.0, center + margin)


# ====================================================================
# TIMEOUT CLASSIFICATION
# ====================================================================
def classify_timeout(position_history):
    """
    Classify timeout drones as stuck or still moving.
    Two honest categories only — we cannot distinguish obstacle vs drone
    deadlock without neighbor state at the moment of timeout.

    Returns: "stuck_timeout" or "moving_timeout"
    """
    if len(position_history) < 50:
        return "moving_timeout"
    positions = list(position_history)
    displacement = np.linalg.norm(positions[-1][1] - positions[-50][1])
    return "stuck_timeout" if displacement < 0.5 else "moving_timeout"


# ====================================================================
# MAIN EVALUATION FUNCTION
# ====================================================================
def evaluate(model_path, n_episodes=1000, density=0.25,
             enable_communication=False, seed_start=999_000_000):
    """
    Evaluate a trained PPO model on fresh unseen maps.

    Args:
        model_path:            Path to .zip checkpoint
        n_episodes:            Number of episodes (default 1000)
        density:               Obstacle density (default 0.25)
        enable_communication:  Fill neighbor slots with real data (default False)
        seed_start:            First seed — each episode gets seed_start + ep_idx

    Returns:
        dict with summary metrics and per-episode data
    """

    # ----------------------------------------------------------------
    # LOAD MODEL
    # ----------------------------------------------------------------
    print(f"[*] Loading model: {model_path}")
    if not os.path.exists(model_path):
        print(f"[ERROR] Not found: {model_path}")
        sys.exit(1)

    model = PPO.load(model_path, device="cpu")
    print(f"[*] Model loaded")

    # ----------------------------------------------------------------
    # CREATE ENVIRONMENT
    # ----------------------------------------------------------------
    env = SwarmVecEnv(density=density, enable_communication=enable_communication)
    print(f"[*] Obs space: {env.observation_space.shape}  |  density={density}"
          f"  |  comm={enable_communication}")

    # ----------------------------------------------------------------
    # COUNTERS
    # ----------------------------------------------------------------
    counters = dict(
        successes=0,
        wall_collisions=0,
        obstacle_collisions=0,
        drone_collisions=0,
        timeouts=0,
        stuck_timeouts=0,
        moving_timeouts=0,
        all_10_success=0,
        total_drones=0,
        total_steps=0,
    )
    steps_to_success = []
    episodes_data = []

    print(f"\n[*] Starting: {n_episodes} episodes\n")

    # ----------------------------------------------------------------
    # EPISODE LOOP
    # ----------------------------------------------------------------
    for ep_idx in range(n_episodes):
        if (ep_idx + 1) % 100 == 0:
            sr = counters["successes"] / max(counters["total_drones"], 1)
            print(f"    Episode {ep_idx+1:4d}/{n_episodes}  "
                  f"success_rate={sr:.3f}  ({sr*100:.1f}%)")

        obs = env.reset(seed=seed_start + ep_idx)

        # Track position history per drone for timeout classification.
        # maxlen=1200 = MAX_STEPS in the environment
        pos_history = {i: deque(maxlen=1200) for i in range(N_DRONES)}

        ep = dict(success=0, wall=0, obstacle=0, drone=0, timeout=0)
        step_count = 0

        # ---- Main step loop ----
        # SwarmVecEnv steps all 10 drones in parallel each call.
        # obs shape: (10, 151)
        # We predict actions for all 10 drones at once.
        while True:
            step_count += 1

            # Predict actions for all 10 drones in parallel
            # obs shape: (10, 151), actions shape: (10, 2)
            actions, _ = model.predict(obs, deterministic=True)

            # Record positions before step
            for drone_id in range(N_DRONES):
                p = env.swarm_env.drone_positions[drone_id]
                pos_history[drone_id].append((step_count, p.copy()))

            # Step the environment
            obs, rewards, dones, infos = env.step(actions)

            # Process terminal events for each drone
            for drone_id in range(N_DRONES):
                info = infos[drone_id]
                cause = info.get("cause")

                if cause == "success":
                    ep["success"] += 1
                    steps_to_success.append(step_count)

                elif cause == "wall_collision":
                    ep["wall"] += 1

                elif cause == "obstacle_collision":
                    ep["obstacle"] += 1

                elif cause == "drone_collision":
                    ep["drone"] += 1

                elif cause == "timeout":
                    ep["timeout"] += 1
                    t_type = classify_timeout(pos_history[drone_id])
                    if t_type == "stuck_timeout":
                        counters["stuck_timeouts"] += 1
                    else:
                        counters["moving_timeouts"] += 1

            # Episode ends when all drones are done
            if np.all(dones):
                break

        # Any drones still active after the loop ended are also timeouts
        # (shouldn't happen with proper done flag handling)
        for drone_id in list(env.swarm_env.active_drones):
            ep["timeout"] += 1
            t_type = classify_timeout(pos_history[drone_id])
            if t_type == "stuck_timeout":
                counters["stuck_timeouts"] += 1
            else:
                counters["moving_timeouts"] += 1

        # ---- Update global counters ----
        counters["successes"]         += ep["success"]
        counters["wall_collisions"]   += ep["wall"]
        counters["obstacle_collisions"] += ep["obstacle"]
        counters["drone_collisions"]  += ep["drone"]
        counters["timeouts"]          += ep["timeout"]
        counters["total_drones"]      += N_DRONES
        counters["total_steps"]       += step_count
        if ep["success"] == N_DRONES:
            counters["all_10_success"] += 1

        episodes_data.append(dict(
            episode=ep_idx,
            seed=seed_start + ep_idx,
            successes=ep["success"],
            wall_collisions=ep["wall"],
            obstacle_collisions=ep["obstacle"],
            drone_collisions=ep["drone"],
            timeouts=ep["timeout"],
            steps=step_count,
            all_10_success=(ep["success"] == N_DRONES),
        ))

    env.close()

    # ----------------------------------------------------------------
    # FINAL METRICS
    # ----------------------------------------------------------------
    total = max(counters["total_drones"], 1)
    sr = counters["successes"]       / total
    wr = counters["wall_collisions"] / total
    or_ = counters["obstacle_collisions"] / total
    dr = counters["drone_collisions"] / total
    tr = counters["timeouts"]        / total
    st_r = counters["stuck_timeouts"]  / total
    mt_r = counters["moving_timeouts"] / total
    a10  = counters["all_10_success"]  / n_episodes
    mean_steps = float(np.mean(steps_to_success)) if steps_to_success else 0.0

    ci_lo, _, ci_hi = wilson_ci(counters["successes"], total)
    margin = (ci_hi - ci_lo) / 2

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"""
{'='*54}
EVALUATION RESULTS
{'='*54}
Model:          {model_path}
Episodes:       {n_episodes}
Density:        {density}
Communication:  {enable_communication}
Timestamp:      {timestamp}
{'-'*54}
Individual Drone Success Rate:   {sr:.3f} +/- {margin:.3f}  (95% CI)
Wall Collision Rate:             {wr:.3f}  ({wr*100:.1f}%)
Obstacle Collision Rate:         {or_:.3f}  ({or_*100:.1f}%)
Drone-Drone Collision Rate:      {dr:.3f}  ({dr*100:.1f}%)
Timeout Rate:                    {tr:.3f}  ({tr*100:.1f}%)
  Stuck (deadlock/obstacle):     {st_r:.3f}  ({st_r*100:.1f}%)
  Still moving:                  {mt_r:.3f}  ({mt_r*100:.1f}%)
Mean Steps to Success:           {mean_steps:.1f}
All-10 Episode Success Rate:     {a10:.3f}  ({a10*100:.1f}%)
Total Drone Attempts:            {total}
{'='*54}
""")

    # ----------------------------------------------------------------
    # SAVE JSON
    # ----------------------------------------------------------------
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    model_name = os.path.basename(model_path).replace(".zip", "")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(results_dir, f"eval_{model_name}_{ts}.json")

    output = {
        "metadata": {
            "model": model_path,
            "n_episodes": n_episodes,
            "density": density,
            "enable_communication": enable_communication,
            "timestamp": timestamp,
        },
        "summary": {
            "success_rate":            float(sr),
            "success_rate_ci_lower":   float(ci_lo),
            "success_rate_ci_upper":   float(ci_hi),
            "wall_collision_rate":     float(wr),
            "obstacle_collision_rate": float(or_),
            "drone_collision_rate":    float(dr),
            "timeout_rate":            float(tr),
            "stuck_timeout_rate":      float(st_r),
            "moving_timeout_rate":     float(mt_r),
            "mean_steps_to_success":   float(mean_steps),
            "all_10_success_rate":     float(a10),
            "total_drone_attempts":    total,
        },
        "episodes": episodes_data,
    }

    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[OK] Results saved: {json_path}\n")
    return output


# ====================================================================
# COMMAND LINE INTERFACE
# ====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate trained swarm navigation model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--model", required=True,
                        help="Path to .zip checkpoint")
    parser.add_argument("--episodes", type=int, default=1000,
                        help="Number of evaluation episodes (default: 1000)")
    parser.add_argument("--density", type=float, default=0.25,
                        help="Obstacle density (default: 0.25)")
    parser.add_argument("--communication", action="store_true",
                        help="Enable inter-drone communication")

    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"[ERROR] Model not found: {args.model}")
        sys.exit(1)

    evaluate(
        model_path=args.model,
        n_episodes=args.episodes,
        density=args.density,
        enable_communication=args.communication,
    )
