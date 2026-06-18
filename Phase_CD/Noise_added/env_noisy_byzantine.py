"""
NOISY-SENSING env — stresses the consistency-trust filter under realistic (blurry) perception.

Extends AdaptiveByzantineEnv (Collab_Perception/). Adds Gaussian position noise to every drone's
obstacle sensing, applied CONSISTENTLY: a drone both NAVIGATES on and BROADCASTS its own noisy
view, and a verifier checks broadcasts against ITS OWN (independently noisy) view.

Why this is the decisive test:
  The hardcoded filter rejects a broadcast obstacle if the verifier "sees nothing there"
  (no sensed obstacle within verify_eps). With perfect sensing this is flawless. With noise of
  std sigma, two drones' views of the SAME real obstacle differ by ~sqrt(2)*sigma. Once that
  exceeds verify_eps, the verifier wrongly contradicts an HONEST broadcast -> false positives ->
  honest neighbors get distrusted -> the filter starts hurting the swarm. This is exactly where a
  simple rule cracks and a *learned* trust module would have to earn its keep.

Noise model:
  * Per drone, per step: each real obstacle's POSITION is perturbed by N(0, sigma) (radii kept true).
  * Physical sensing RANGE uses true distance (you sense it if it is within lidar_range), but your
    MEASURED position of it is noisy. Blind drones sense nothing (sender-gating preserved).
  * Phantoms are exact (the attacker fabricates precisely; it has no sensor noise).
"""
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
_COLLAB = os.path.join(_PHASE_CD, "Collab_Perception")
for _p in (_ROOT, _PHASE_CD, _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from env_byzantine_adaptive import AdaptiveByzantineEnv


class NoisyByzantineEnv(AdaptiveByzantineEnv):
    def __init__(self, *args, sensor_noise=0.0, verify_k_sigma=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensor_noise = sensor_noise        # Gaussian std (m) on sensed obstacle positions
        # ROBUST FILTER knob: effective contradiction tolerance = verify_eps + verify_k_sigma * sensor_noise.
        # verify_k_sigma=0 -> the naive fixed-threshold rule (noise-fragile, the strawman baseline).
        # verify_k_sigma>0 -> noise-aware: honest noisy matches (~sqrt(2)*sigma off) pass; only WILDLY
        # off broadcasts (open-space phantoms, meters from any real obstacle) still flag. Pair with a
        # slower trust_alpha so a single noisy mismatch can't condemn an honest neighbor.
        self.verify_k_sigma = verify_k_sigma
        self._sense_step = -1
        self._sensed = np.empty((self.n_drones, 0, 2), dtype=np.float32)   # per-drone noisy views
        self._sradii = np.empty((0,), dtype=np.float32)
        self._in_range = np.zeros((self.n_drones, 0), dtype=bool)

    # ---- per-step noisy sensing (one draw per step, shared across observers) ----
    def _sample_sensing(self):
        if self._sense_step == self.steps:
            return
        self._sample_dropout()                  # ensure blindness is current first
        self._sense_step = self.steps
        M = len(self.obstacles)
        if M == 0:
            self._sensed = np.empty((self.n_drones, 0, 2), dtype=np.float32)
            self._sradii = np.empty((0,), dtype=np.float32)
            self._in_range = np.zeros((self.n_drones, 0), dtype=bool)
            return
        real = np.array(self.obstacles, dtype=np.float32)
        tc, self._sradii = real[:, :2], real[:, 2]
        if self.sensor_noise > 0.0:
            noise = np.random.normal(0.0, self.sensor_noise, (self.n_drones, M, 2)).astype(np.float32)
        else:
            noise = np.zeros((self.n_drones, M, 2), dtype=np.float32)
        self._sensed = (tc[None, :, :] + noise).astype(np.float32)
        self._in_range = np.zeros((self.n_drones, M), dtype=bool)
        for j in range(self.n_drones):
            if self.lidar_blind[j]:
                continue
            d = np.linalg.norm(tc - self.positions[j], axis=1)
            self._in_range[j] = d <= self.lidar_range

    # ---- verification against ego's OWN noisy view ----
    def _ego_judgement(self, idx, cand_centers):
        if self.lidar_blind[idx] or not len(cand_centers):
            return False, False
        ego_seen = self._sensed[idx][self._in_range[idx]] if self._sensed.shape[1] else np.empty((0, 2), np.float32)
        eps = self.verify_eps + self.verify_k_sigma * self.sensor_noise   # noise-aware tolerance
        pos = self.positions[idx]
        judged = False
        for o in cand_centers:
            if np.linalg.norm(pos - o) > self.lidar_range:
                continue
            judged = True
            if len(ego_seen) == 0 or float(np.min(np.linalg.norm(ego_seen - o, axis=1))) > eps:
                return True, True
        return judged, False

    # ---- fused slot using noisy sensing + attack + (optional) trust defense ----
    def _fused_lidar(self, idx):
        self._sample_sensing()
        pos = self.positions[idx]
        M = self._sensed.shape[1]
        c_list, r_list = [], []

        # 1. Ego's own (noisy) obstacles, if sighted
        if not self.lidar_blind[idx] and M:
            m = self._in_range[idx]
            if m.any():
                c_list.append(self._sensed[idx][m]); r_list.append(self._sradii[m])

        # 2. Per-neighbor broadcasts (noisy real + exact phantoms), with trust gating
        for j in range(self.n_drones):
            if j == idx or self.possible_agents[j] not in self.agents:
                continue
            if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                continue
            bc_c, bc_r = [], []
            if not self.lidar_blind[j] and M:
                m = self._in_range[j]
                if m.any():
                    bc_c.append(self._sensed[j][m]); bc_r.append(self._sradii[m])
            if self.false_obstacle_attack and (j in self.traitor_indices) and len(self._phantoms):
                bc_c.append(self._phantoms[:, :2]); bc_r.append(self._phantoms[:, 2])
            if not bc_c:
                continue
            bc_c = np.concatenate(bc_c); bc_r = np.concatenate(bc_r)

            if self.trust_defense:
                judged, contradicted = self._ego_judgement(idx, bc_c)
                if judged:
                    self.trust[idx, j] = ((1.0 - self.trust_alpha) * self.trust[idx, j]
                                          + self.trust_alpha * (0.0 if contradicted else 1.0))
                if self.trust[idx, j] < self.tau_trust:
                    continue
            c_list.append(bc_c); r_list.append(bc_r)

        # 3. Other drones (always visible)
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))

        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range

    # OFF path (own LiDAR only) under noise — used for the comm-disabled ablation
    def _own_lidar_only(self, idx):
        self._sample_sensing()
        pos = self.positions[idx]
        M = self._sensed.shape[1]
        c_list, r_list = [], []
        if not self.lidar_blind[idx] and M:
            m = self._in_range[idx]
            if m.any():
                c_list.append(self._sensed[idx][m]); r_list.append(self._sradii[m])
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))
        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range
