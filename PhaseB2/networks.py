"""
Custom Actor-Critic Network for SB3 PPO — Swarm Navigation

SwarmFeaturesExtractor: processes split 151D observation space
  - 72D LiDAR (range rays)
  - 7D own state (position, velocity, goal direction)
  - 72D neighbor slots (9 neighbors × 8D each)

Each component gets its own encoder, then fused before the actor/critic heads.
Mean pooling over neighbors is permutation-invariant (order doesn't matter).
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import numpy as np
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor, NatureCNN
from stable_baselines3.common.policies import ActorCriticPolicy


class SwarmFeaturesExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor for swarm observations.

    Input: 151D observation
      [0:72]    LiDAR (48 rays, some duplicated for alignment)
      [72:79]   Own state (x, y, vx, vy, goal_x, goal_y, goal_dist)
      [79:151]  Neighbor slots (9 × 8D: vx, vy, x_rel, y_rel, dist, collision_risk, active_flag, unused)

    Output: 128D features for actor/critic heads
    """

    def __init__(self, observation_space: spaces.Box, features_dim: int = 128):
        super().__init__(observation_space, features_dim)

        # Component dimensions
        self.lidar_dim = 72
        self.own_state_dim = 7
        self.neighbor_dim = 72  # 9 neighbors × 8D
        self.num_neighbors = 9
        self.neighbor_state_dim = 8

        assert self.lidar_dim + self.own_state_dim + self.neighbor_dim == 151, \
            f"Observation size mismatch: {self.lidar_dim + self.own_state_dim + self.neighbor_dim} != 151"

        # ============ LiDAR Encoder ============
        # 72D → 128D → 64D
        self.lidar_encoder = nn.Sequential(
            nn.Linear(self.lidar_dim, 128),
            nn.LayerNorm(128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.LayerNorm(64),
            nn.Tanh()
        )
        self.lidar_out_dim = 64

        # ============ Own State Encoder ============
        # 7D → 32D
        self.own_state_encoder = nn.Sequential(
            nn.Linear(self.own_state_dim, 32),
            nn.LayerNorm(32),
            nn.Tanh()
        )
        self.own_state_out_dim = 32

        # ============ Neighbor Encoder ============
        # Process each neighbor slot independently, then mean pool
        # Each slot: 8D → 32D
        self.neighbor_slot_encoder = nn.Sequential(
            nn.Linear(self.neighbor_state_dim, 32),
            nn.Tanh()
        )

        # Post-pooling fusion of neighbor features
        self.neighbor_fusion = nn.Sequential(
            nn.Linear(32, 32),
            nn.LayerNorm(32),
            nn.Tanh()
        )
        self.neighbor_out_dim = 32

        # ============ Fusion Layer ============
        # Concatenate all encoded features: [64, 32, 32] → 128D
        fusion_input_dim = self.lidar_out_dim + self.own_state_out_dim + self.neighbor_out_dim
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, 256),
            nn.LayerNorm(256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.Tanh()
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """
        Process observation batch.

        Args:
            observations: shape (batch_size, 151)

        Returns:
            features: shape (batch_size, 128)
        """
        batch_size = observations.shape[0]

        # ---- Split observation into components ----
        lidar = observations[:, :self.lidar_dim]                          # (batch, 72)
        own_state = observations[:, self.lidar_dim:self.lidar_dim + self.own_state_dim]  # (batch, 7)
        neighbors_flat = observations[:, self.lidar_dim + self.own_state_dim:]  # (batch, 72)

        # ---- Encode each component ----
        lidar_features = self.lidar_encoder(lidar)                        # (batch, 64)
        own_state_features = self.own_state_encoder(own_state)            # (batch, 32)

        # Reshape neighbors to (batch, 9, 8) for per-slot processing
        neighbors = neighbors_flat.reshape(batch_size, self.num_neighbors, self.neighbor_state_dim)  # (batch, 9, 8)

        # Encode each neighbor slot
        # Shape: (batch, 9, 8) → (batch, 9, 32)
        neighbor_slot_features = self.neighbor_slot_encoder(neighbors)    # (batch, 9, 32)

        # Zero out inactive neighbor slots using active flag (index 7)
        # active_flags shape: (batch, 9, 1)
        active_flags = neighbors[:, :, 7:8]
        neighbor_slot_features = neighbor_slot_features * active_flags

        # Mean pool over active neighbors only
        # Avoid division by zero if all neighbors inactive
        n_active = active_flags.sum(dim=1).clamp(min=1.0)  # (batch, 1)
        neighbor_pooled = neighbor_slot_features.sum(dim=1) / n_active  # (batch, 32)

        # Fuse pooled neighbor features
        neighbor_features = self.neighbor_fusion(neighbor_pooled)         # (batch, 32)

        # ---- Fuse all components ----
        fused = torch.cat([lidar_features, own_state_features, neighbor_features], dim=1)  # (batch, 128)
        features = self.fusion(fused)                                     # (batch, 128)

        return features


class SwarmActorExtractor(BaseFeaturesExtractor):
    """
    Actor feature extractor for MAPPO.
    Input: 1661D combined obs (151D local + 1510D global).
    Uses ONLY the first 151D (local obs). Ignores global state.
    Identical processing to SwarmFeaturesExtractor.
    """

    def __init__(self, observation_space: spaces.Box, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        local_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(151,), dtype=np.float32
        )
        self._inner = SwarmFeaturesExtractor(local_space, features_dim=features_dim)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        local_obs = observations[:, :151]
        return self._inner(local_obs)


class SwarmCriticExtractor(BaseFeaturesExtractor):
    """
    Centralized critic feature extractor for MAPPO.
    Input: 1661D combined obs (151D local + 1510D global).
    Uses the FULL 1661D (local + global) so the critic knows which drone it's evaluating.
    """

    def __init__(self, observation_space: spaces.Box, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        self.net = nn.Sequential(
            nn.Linear(1661, 512), nn.LayerNorm(512), nn.Tanh(),
            nn.Linear(512,  256), nn.LayerNorm(256), nn.Tanh(),
            nn.Linear(256,  128), nn.LayerNorm(128), nn.Tanh(),
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        return self.net(observations)           # (batch, 128)


class _DummyMlpExtractor(nn.Module):
    """Satisfies SB3 internals that reference mlp_extractor. Never called."""
    latent_dim_pi = 64
    latent_dim_vf = 64

    def forward(self, x):
        return x, x


class MAPPOPolicy(ActorCriticPolicy):
    """
    MAPPO Actor-Critic Policy.

    Actor  : uses local 151D obs   → SwarmActorExtractor  → action
    Critic : uses global 1661D obs → SwarmCriticExtractor → value
    """

    def _build(self, lr_schedule) -> None:
        self.features_extractor = SwarmActorExtractor(
            self.observation_space, features_dim=128
        )
        self.critic_features_extractor = SwarmCriticExtractor(
            self.observation_space, features_dim=128
        )

        self.actor_mlp = nn.Sequential(nn.Linear(128, 64), nn.Tanh())
        self.critic_mlp = nn.Sequential(nn.Linear(128, 64), nn.Tanh())

        self.mlp_extractor = _DummyMlpExtractor()

        self.action_net, self.log_std = self.action_dist.proba_distribution_net(
            latent_dim=64, log_std_init=0.0
        )

        self.value_net = nn.Linear(64, 1)

        self.optimizer = self.optimizer_class(
            self.parameters(),
            lr=lr_schedule(1),
            **self.optimizer_kwargs
        )

    def forward(self, obs: torch.Tensor, deterministic: bool = False):
        actor_latent  = self.actor_mlp(self.features_extractor(obs))
        critic_latent = self.critic_mlp(self.critic_features_extractor(obs))

        values       = self.value_net(critic_latent)
        distribution = self._get_action_dist_from_latent(actor_latent)
        actions      = distribution.get_actions(deterministic=deterministic)
        log_prob     = distribution.log_prob(actions)
        actions      = actions.reshape((-1, *self.action_space.shape))
        return actions, values, log_prob

    def evaluate_actions(self, obs: torch.Tensor, actions: torch.Tensor):
        actor_latent  = self.actor_mlp(self.features_extractor(obs))
        critic_latent = self.critic_mlp(self.critic_features_extractor(obs))

        distribution = self._get_action_dist_from_latent(actor_latent)
        log_prob     = distribution.log_prob(actions)
        entropy      = distribution.entropy()
        values       = self.value_net(critic_latent)
        return values, log_prob, entropy

    def predict_values(self, obs: torch.Tensor) -> torch.Tensor:
        critic_latent = self.critic_mlp(self.critic_features_extractor(obs))
        return self.value_net(critic_latent)

    def get_distribution(self, obs: torch.Tensor):
        actor_latent = self.actor_mlp(self.features_extractor(obs))
        return self._get_action_dist_from_latent(actor_latent)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Testing SwarmFeaturesExtractor...")

    # Create dummy observation space
    obs_space = spaces.Box(low=-np.inf, high=np.inf, shape=(151,), dtype=np.float32)

    # Instantiate extractor
    extractor = SwarmFeaturesExtractor(obs_space, features_dim=128)

    # Test forward pass with batch of 32
    test_obs = torch.randn(32, 151, dtype=torch.float32)
    features = extractor(test_obs)

    assert features.shape == (32, 128), f"Expected shape (32, 128), got {features.shape}"
    print(f"✓ Feature extractor output shape: {features.shape}")

    # Count parameters
    total_params = sum(p.numel() for p in extractor.parameters())
    print(f"✓ Feature extractor parameters: {total_params:,}")

    # Verify parameter count is in expected range
    assert 50000 < total_params < 150000, \
        f"Parameter count {total_params} outside expected range (50K-150K)"
    print(f"✓ Parameter count in expected range")

    # Test with different batch sizes
    for batch_sz in [1, 16, 64]:
        test_batch = torch.randn(batch_sz, 151, dtype=torch.float32)
        out = extractor(test_batch)
        assert out.shape == (batch_sz, 128), f"Batch size {batch_sz} failed"
    print(f"✓ Tested with batch sizes [1, 16, 64]")

    # Verify gradients flow through
    test_obs_grad = torch.randn(4, 151, dtype=torch.float32, requires_grad=True)
    out_grad = extractor(test_obs_grad)
    loss = out_grad.sum()
    loss.backward()
    assert test_obs_grad.grad is not None
    print(f"✓ Gradients flow through extractor")

    print("\n" + "="*60)
    print("All tests passed! Network is ready for training.")
    print("="*60)
