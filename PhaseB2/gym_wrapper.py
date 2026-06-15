"""
SwarmVecEnv: Vectorized environment wrapper for 10-drone swarm.

Instead of cycling through drones sequentially (which breaks the Markov property),
this wrapper steps all 10 drones in parallel, treating each as its own environment
within a shared SwarmEnv. Dead drones continue in a "ghost" state until all drones
are inactive, at which point the swarm resets.

This preserves proper Markov transitions for SB3 PPO:
  - Action from drone i directly affects the observation/reward of drone i
  - All 10 drones step simultaneously
  - Reward is returned every step for every drone (not just on macro-step 10)
  - Credit assignment is clear: drone i's action → drone i's outcome
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3.common.vec_env import VecEnv
from swarm_env import SwarmEnv


class SwarmVecEnv(VecEnv):
    """
    Vectorized environment for 10-drone swarm.

    Wraps SwarmEnv as a true parallel environment where each drone is treated
    as an independent agent stepping simultaneously.

    - num_envs = 10 (one per drone)
    - observation_space = (151,) for each drone's local observation
    - action_space = (2,) continuous velocity
    """

    def __init__(self, density=0.25, enable_communication=False, seed=None):
        """
        Args:
            density: Obstacle density (0.0 to 1.0)
            enable_communication: Whether drones share state via neighbor channels
            seed: Random seed
        """
        self.swarm_env = SwarmEnv(
            target_density=density,
            enable_communication=enable_communication,
            seed=seed
        )

        self.num_envs = self.swarm_env.N_DRONES  # 10
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(1661,),  # 151D local + 1510D global
            dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(2,),
            dtype=np.float32
        )

        # Track state across steps
        self._obs = np.zeros((self.num_envs, 1661), dtype=np.float32)
        self._rewards = np.zeros(self.num_envs, dtype=np.float32)
        self._dones = np.zeros(self.num_envs, dtype=bool)
        self._infos = [{} for _ in range(self.num_envs)]

        # State tracking setup is complete.

    def reset(self, seed=None, options=None):
        """Reset the swarm environment."""
        obs_dict, _ = self.swarm_env.reset(seed=seed)

        # Initialize all drones with their local observations first
        local_obs = np.zeros((self.num_envs, 151), dtype=np.float32)
        for drone_id in range(self.num_envs):
            local_obs[drone_id] = obs_dict[drone_id]
            self._rewards[drone_id] = 0.0
            self._dones[drone_id] = False
            self._infos[drone_id] = {}

        # Build 1661D combined observations (local + global)
        global_obs = local_obs.flatten()
        for drone_id in range(self.num_envs):
            self._obs[drone_id] = np.concatenate([local_obs[drone_id], global_obs])

        return self._obs.copy()

    def step_async(self, actions: np.ndarray):
        """
        Prepare actions for the next step.

        Args:
            actions: (num_envs, 2) array of velocity commands
        """
        self._pending_actions = actions

    def step_wait(self):
        """
        Execute one step of all drones simultaneously.

        Properly handles per-drone termination: when a drone succeeds or collides,
        done[drone_id] is set to True immediately (not waiting for entire swarm to finish).
        Terminal observation is extracted from info dict when available.

        Returns:
            obs: (10, 1661) observations
            rewards: (10,) rewards for this step
            dones: (10,) terminal flags (True if this drone finished, False if still active)
            infos: list of 10 info dicts (includes "terminal_observation" for terminated drones)
        """
        # Build action dict for SwarmEnv (only active drones receive actions)
        actions_dict = {}
        for drone_id in range(self.num_envs):
            if drone_id in self.swarm_env.active_drones:
                actions_dict[drone_id] = np.clip(self._pending_actions[drone_id], -1.0, 1.0)

        # Step the swarm environment
        obs_dict, rew_dict, done_dict, trunc_dict, info_dict = \
            self.swarm_env.step(actions_dict)

        # Build local observations array first
        local_obs = np.zeros((self.num_envs, 151), dtype=np.float32)
        for drone_id in range(self.num_envs):
            if drone_id in obs_dict:
                local_obs[drone_id] = obs_dict[drone_id]
            else:
                # Dead drone: zero observation (will be overwritten with terminal_observation below)
                local_obs[drone_id] = np.zeros(151, dtype=np.float32)

            # Reward: use real reward from swarm_env, or 0 if drone is dead
            if drone_id in rew_dict:
                self._rewards[drone_id] = rew_dict[drone_id]
            else:
                self._rewards[drone_id] = 0.0

            # Done flag: respect what swarm_env reports (per-drone termination)
            if drone_id in done_dict:
                self._dones[drone_id] = done_dict[drone_id]
            else:
                self._dones[drone_id] = False

            # Info: pass through, and use terminal_observation if available
            if drone_id in info_dict:
                self._infos[drone_id] = info_dict[drone_id]
                # If this drone terminated, use its terminal observation for SB3
                if self._dones[drone_id] and "terminal_observation" in info_dict[drone_id]:
                    local_obs[drone_id] = info_dict[drone_id]["terminal_observation"]
            else:
                self._infos[drone_id] = {}

        # Build combined 1661D observations (local + global)
        global_obs = local_obs.flatten()
        for drone_id in range(self.num_envs):
            self._obs[drone_id] = np.concatenate([local_obs[drone_id], global_obs])

        # If all drones are inactive or max steps reached, mark episode as done
        # and reset the environment for the next episode
        if len(self.swarm_env.active_drones) == 0 or \
           self.swarm_env.step_count >= self.swarm_env.MAX_STEPS:
            # Mark any remaining active drones as done (timeout)
            for drone_id in range(self.num_envs):
                if not self._dones[drone_id]:
                    self._dones[drone_id] = True
                    self._infos[drone_id]["cause"] = "timeout"

            # Copy the final states BEFORE resetting
            terminal_rewards = self._rewards.copy()
            terminal_dones = self._dones.copy()
            terminal_infos = [info.copy() for info in self._infos]

            # Reset the environment for the next episode
            reset_obs = self.reset()
            return (
                reset_obs,
                terminal_rewards,
                terminal_dones,
                terminal_infos
            )

        return (
            self._obs.copy(),
            self._rewards.copy(),
            self._dones.copy(),
            self._infos
        )

    def step(self, actions: np.ndarray):
        """Single-step interface (step_async + step_wait)."""
        self.step_async(actions)
        return self.step_wait()

    def render(self):
        """Render the environment (if supported)."""
        self.swarm_env.render()

    def close(self):
        """Close the environment."""
        pass

    def set_density(self, density):
        """Update obstacle density (for curriculum learning)."""
        self.swarm_env.target_density = density

    def set_communication(self, enable):
        """Enable/disable inter-drone communication."""
        self.swarm_env.enable_communication = enable

    def get_attr(self, attr_name, indices=None):
        return [getattr(self, attr_name)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        setattr(self, attr_name, value)

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        method = getattr(self, method_name)
        return [method(*method_args, **method_kwargs)] * self.num_envs

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs


# DEPRECATED: SwarmFlatEnv
# Legacy single-agent wrapper that tiled actions to all drones (broken for multi-agent learning).
# Use SwarmVecEnv directly instead. See train.py and evaluate.py for the correct pattern.
