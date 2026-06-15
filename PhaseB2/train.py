"""
PPO Training Script with Density Curriculum

Trains a PPO agent through 5 curriculum stages with increasing obstacle density.
Uses SwarmVecEnv directly (10 parallel drones = 10 independent agents).

Total training: 20 million steps
Curriculum: 0.05 → 0.10 → 0.15 → 0.20 → 0.25 density
"""

import os
import multiprocessing
# Determine core count safely: use 10 if available, otherwise fall back to 8 (or the maximum available)
available_cores = multiprocessing.cpu_count()
if available_cores >= 10:
    num_cores = 10
elif available_cores >= 8:
    num_cores = 8
else:
    num_cores = max(1, available_cores)  # ensure at least 1 core
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = str(num_cores)
os.environ["MKL_NUM_THREADS"] = str(num_cores)

import csv
from datetime import datetime
from typing import Dict, Any
from collections import deque

import numpy as np
import torch
torch.set_num_threads(num_cores)
print(f"[*] PyTorch and OpenMP configured to use all {num_cores} CPU cores.")

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecMonitor
from stable_baselines3.common.callbacks import BaseCallback

from gym_wrapper import SwarmVecEnv
from networks import MAPPOPolicy


# ============================================================================
# CURRICULUM DEFINITION
# ============================================================================
'''
CURRICULUM = [
    {"density": 0.0, "steps": 3_000_000, "name": "stage0"},
    {"density": 0.05, "steps": 3_000_000, "name": "stage1"},
    {"density": 0.10, "steps": 3_000_000, "name": "stage2"},
    {"density": 0.15, "steps": 3_000_000, "name": "stage3"},
    {"density": 0.20, "steps": 3_000_000, "name": "stage4"},
    {"density": 0.25, "steps": 3_000_000, "name": "stage5"},
]
'''
CURRICULUM = [
    {"density": 0.0, "steps": 3_000_000, "name": "stage0"},
]
TOTAL_STEPS = sum(stage["steps"] for stage in CURRICULUM)
LOGGING_INTERVAL = 10_000


# ============================================================================
# CURRICULUM CALLBACK
# ============================================================================

class CurriculumCallback(BaseCallback):
    """Logs training metrics and saves best model."""

    def __init__(self, log_file: str = "logs/training_log.csv",
                 phase: int = 1, communication_enabled: bool = False):
        super().__init__()
        self.log_file = log_file
        self.phase = phase
        self.communication_enabled = communication_enabled
        self.last_logged_step = 0
        self.best_mean_reward = -np.inf
        self.current_density = 0.0
        self.prev_reward = None

        # Outcome history sliding window (tracks last 1000 drone outcomes)
        self.outcome_history = deque(maxlen=1000)

        # Initialize CSV file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        if not os.path.exists(log_file):
            with open(log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "step", "phase", "density", "mean_reward", "mean_ep_length",
                    "success_rate", "wall_collision_rate", "obstacle_collision_rate",
                    "drone_collision_rate", "timeout_rate", "communication_enabled", "timestamp"
                ])

    def _on_step(self) -> bool:
        """Called after each environment step."""
        current_step = self.model.num_timesteps

        # Read cause from infos for each drone (SwarmVecEnv returns list of 10 dicts)
        infos = self.locals.get("infos", [])
        for info in infos:
            cause = info.get("cause")
            if cause:
                self.outcome_history.append(cause)

        # Log every LOGGING_INTERVAL steps
        if current_step - self.last_logged_step >= LOGGING_INTERVAL:
            self._log_metrics(current_step)
            self.last_logged_step = current_step

        return True

    def set_density(self, density: float):
        """Update the current density for logging."""
        self.current_density = density

    def _status(self, value, thresholds):
        """Return status label given (good, ok, warning) thresholds (higher=better)."""
        if value >= thresholds[0]:
            return "GOOD  "
        elif value >= thresholds[1]:
            return "OK    "
        elif value >= thresholds[2]:
            return "WARN  "
        return "CRITICAL"

    def _status_low(self, value, thresholds):
        """Return status label given (good, ok, warning) thresholds (lower=better)."""
        if value <= thresholds[0]:
            return "GOOD  "
        elif value <= thresholds[1]:
            return "OK    "
        elif value <= thresholds[2]:
            return "WARN  "
        return "CRITICAL"

    def _trend(self, current, previous):
        """Arrow indicator for metric trend."""
        if previous is None:
            return " "
        diff = current - previous
        if diff > 0.005:
            return "↑"
        elif diff < -0.005:
            return "↓"
        return "→"

    def _log_metrics(self, step: int):
        """Extract and log training metrics with clear health status output."""
        ep_info_buffer = self.model.ep_info_buffer

        if len(ep_info_buffer) > 0:
            ep_rewards = np.array([ep["r"] for ep in ep_info_buffer])
            ep_lengths = np.array([ep["l"] for ep in ep_info_buffer])
            mean_reward = float(np.mean(ep_rewards))
            mean_ep_length = float(np.mean(ep_lengths))
        else:
            mean_reward = 0.0
            mean_ep_length = 0.0

        total = len(self.outcome_history)
        if total > 0:
            success_rate   = self.outcome_history.count("success") / total
            wall_rate      = self.outcome_history.count("wall_collision") / total
            obstacle_rate  = self.outcome_history.count("obstacle_collision") / total
            drone_rate     = self.outcome_history.count("drone_collision") / total
            timeout_rate   = self.outcome_history.count("timeout") / total
        else:
            success_rate = wall_rate = obstacle_rate = drone_rate = timeout_rate = 0.0

        # Save best model
        if mean_reward > self.best_mean_reward:
            self.best_mean_reward = mean_reward
            self.model.save(f"checkpoints/phase{self.phase}/model_best")

        # Determine overall health
        if success_rate >= 0.25 and obstacle_rate < 0.55 and drone_rate < 0.65:
            health = "GOOD  — Continue training"
        elif success_rate >= 0.12 and obstacle_rate < 0.70:
            health = "OK    — Continue training"
        elif success_rate >= 0.05:
            health = "WARN  — Watch closely next 500K steps"
        else:
            health = "CRITICAL — Consider stopping if this persists 200K more steps"

        # Reward trend
        reward_trend = self._trend(mean_reward, self.prev_reward)
        self.prev_reward = mean_reward

        # Stage index (1-based)
        stage_idx = next(
            (i + 1 for i, s in enumerate(CURRICULUM) if s["density"] == self.current_density),
            "?"
        )

        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n{'='*62}")
        print(f"  PHASE {self.phase} | STAGE {stage_idx}/5 | "
              f"density={self.current_density:.2f} | "
              f"Step {step:,} | {timestamp}")
        print(f"{'='*62}")
        print(f"  Reward        : {mean_reward:8.2f}  {reward_trend}")
        print(f"  Success Rate  : {success_rate:8.3f}  ({success_rate*100:5.1f}%)  "
              f"{self._status(success_rate, (0.25, 0.12, 0.05))}")
        print(f"  Obstacle Coll : {obstacle_rate:8.3f}  ({obstacle_rate*100:5.1f}%)  "
              f"{self._status_low(obstacle_rate, (0.25, 0.45, 0.60))}")
        print(f"  Drone Coll    : {drone_rate:8.3f}  ({drone_rate*100:5.1f}%)  "
              f"{self._status_low(drone_rate, (0.35, 0.55, 0.70))}")
        print(f"  Wall Coll     : {wall_rate:8.3f}  ({wall_rate*100:5.1f}%)  "
              f"{self._status_low(wall_rate, (0.02, 0.05, 0.10))}")
        print(f"  Timeout Rate  : {timeout_rate:8.3f}  ({timeout_rate*100:5.1f}%)  "
              f"{self._status_low(timeout_rate, (0.30, 0.50, 0.70))}")
        print(f"  Episode Length: {mean_ep_length:8.1f}")
        print(f"  Best Reward   : {self.best_mean_reward:8.2f}")
        print(f"{'─'*62}")
        print(f"  HEALTH: {health}")
        print(f"{'='*62}")

        # Log to CSV
        timestamp_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                step, self.phase, f"{self.current_density:.2f}",
                f"{mean_reward:.4f}", f"{mean_ep_length:.2f}",
                f"{success_rate:.4f}", f"{wall_rate:.4f}",
                f"{obstacle_rate:.4f}", f"{drone_rate:.4f}",
                f"{timeout_rate:.4f}", self.communication_enabled,
                timestamp_full
            ])

        # Counters are automatically managed by the sliding window deque.
        pass


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

def create_env(density: float, enable_communication: bool, seed: int = None) -> VecMonitor:
    """Create and wrap a single SwarmVecEnv with monitoring.

    SwarmVecEnv is already vectorized (10 drones = 10 independent agents in parallel).
    We wrap it with VecMonitor to track episode info.
    """
    env = SwarmVecEnv(
        density=density,
        enable_communication=enable_communication,
        seed=seed
    )
    env = VecMonitor(env)
    return env


# ============================================================================
# TRAINING LOOP
# ============================================================================

def train(phase: int = 1):
    """Main training loop with curriculum learning.

    Args:
        phase: 1 for no communication, 2 for communication enabled
    """
    enable_communication = (phase == 2)
    os.makedirs("checkpoints", exist_ok=True)
    os.makedirs(f"checkpoints/phase{phase}", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Create initial environment at stage1 density
    env = create_env(density=CURRICULUM[0]["density"],
                     enable_communication=enable_communication)

    # PPO with MAPPOPolicy (centralized critic during training)
    # Each drone is an independent agent with local actor and centralized critic
    model = PPO(
        policy=MAPPOPolicy,
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=0,
        tensorboard_log="./logs/",
        device="cpu"
    )

    # Create callback
    callback = CurriculumCallback(
        log_file=f"logs/phase{phase}_training_log.csv",
        phase=phase,
        communication_enabled=enable_communication
    )

    # ========================================================================
    # CURRICULUM TRAINING
    # ========================================================================

    for stage_idx, stage in enumerate(CURRICULUM):
        density = stage["density"]
        steps = stage["steps"]
        name = stage["name"]

        print(f"\n{'='*70}")
        print(f"Starting {name.upper()} at density {density}")
        print(f"Training for {steps:,} steps")
        print(f"{'='*70}\n")

        # Update density in the environment
        env.env_method("set_density", density)

        # Update callback's current density
        callback.set_density(density)
        # Reset best-reward tracking per stage so model_best reflects the
        # best checkpoint at the CURRENT density, not an easier earlier stage
        callback.best_mean_reward = -np.inf

        # Train for this stage
        model.learn(
            total_timesteps=steps,
            reset_num_timesteps=False,  # Continue from previous stage
            tb_log_name=name,
            callback=callback
        )

        # Save checkpoint after each stage
        checkpoint_path = f"checkpoints/phase{phase}/model_{name}"
        model.save(checkpoint_path)
        print(f"\n✓ Saved checkpoint: {checkpoint_path}.zip")

    # ========================================================================
    # TRAINING COMPLETE
    # ========================================================================

    print(f"\n{'='*70}")
    print("✓ Training complete!")
    print(f"✓ Final model saved to checkpoints/phase{phase}/model_stage{len(CURRICULUM)}.zip")
    print(f"✓ Best model saved to checkpoints/phase{phase}/model_best.zip")
    print(f"✓ Training log saved to logs/phase{phase}_training_log.csv")
    print(f"✓ TensorBoard logs in ./logs/")
    print(f"{'='*70}\n")

    env.close()


# ============================================================================
# RESUME TRAINING
# ============================================================================

def resume_training(resume_from_stage: int = 1, phase: int = 1):
    """Resume training from a saved checkpoint.

    Args:
        resume_from_stage: Stage number that is COMPLETED (1-indexed).
                          E.g., resume_from_stage=2 means stage 2 (d=0.10) is done,
                          training continues from stage 3 (d=0.15).
                          Valid values: 1-4 (stage 5 = all done, nothing to resume).
        phase: 1 for no communication, 2 for communication enabled
    """
    enable_communication = (phase == 2)
    os.makedirs("checkpoints", exist_ok=True)
    os.makedirs(f"checkpoints/phase{phase}", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Load the saved model
    checkpoint_name = f"model_stage{resume_from_stage}"
    model_path = f"checkpoints/phase{phase}/{checkpoint_name}"

    if not os.path.exists(f"{model_path}.zip"):
        raise FileNotFoundError(f"Checkpoint {model_path}.zip not found")

    print(f"Loading checkpoint: {model_path}.zip")
    model = PPO.load(model_path)

    # Create callback
    callback = CurriculumCallback(
        log_file=f"logs/phase{phase}_training_log.csv",
        phase=phase,
        communication_enabled=enable_communication
    )

    start_stage = resume_from_stage
    remaining = CURRICULUM[start_stage:]

    if not remaining:
        print(f"\n[INFO] All {len(CURRICULUM)} stages are complete through stage {resume_from_stage}.")
        print(f"[INFO] Nothing to resume. Use model_stage{len(CURRICULUM)}.zip for evaluation.")
        return

    for stage in remaining:
        density = stage["density"]
        steps = stage["steps"]
        name = stage["name"]

        print(f"\n{'='*70}")
        print(f"Resuming {name.upper()} at density {density}")
        print(f"Training for {steps:,} steps")
        print(f"{'='*70}\n")

        # Create new environment at this stage's density
        env = create_env(density=density, enable_communication=enable_communication)
        model.set_env(env)

        # Update callback's current density
        callback.set_density(density)

        # Train for this stage
        model.learn(
            total_timesteps=steps,
            reset_num_timesteps=False,
            tb_log_name=name,
            callback=callback
        )

        # Save checkpoint
        checkpoint_path = f"checkpoints/phase{phase}/model_{name}"
        model.save(checkpoint_path)
        print(f"\n✓ Saved checkpoint: {checkpoint_path}.zip")

        env.close()

    print(f"\n{'='*70}")
    print("✓ Resume training complete!")
    print(f"✓ Final model saved to checkpoints/phase{phase}/model_stage{len(CURRICULUM)}.zip")
    print(f"{'='*70}\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train PPO with density curriculum")
    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        choices=[1, 2],
        help="1=no-communication (Phase 1), 2=communication enabled (Phase 2)"
    )
    parser.add_argument(
        "--resume",
        type=int,
        default=None,
        help="Resume from stage N (1-5). Stage N must be complete. If not specified, train from scratch."
    )

    args = parser.parse_args()

    if args.resume is not None:
        resume_training(resume_from_stage=args.resume, phase=args.phase)
    else:
        train(phase=args.phase)
