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
    def __init__(self, *args, sensor_noise=0.0, verify_k_sigma=0.0,
                 temporal_defense=False, temporal_bias_eps=0.5, temporal_min_k=10,
                 phantom_jitter=0.0, phantom_duty=1.0, comm_loss=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensor_noise = sensor_noise        # Gaussian std (m) on sensed obstacle positions
        # COMM-LOSS (R3 realism study): each neighbour's broadcast is independently DROPPED with
        # probability comm_loss per (receiver, sender, step) — a lost packet delivers nothing, so it
        # contributes neither to fusion NOR to the trust verification that frame. Models lossy radio.
        # Temporal defense should degrade gracefully: at loss p it needs ~min_k/(1-p) frames to reach a
        # verdict (still << the 1200-step episode for moderate p), while honest fusion also loses some help.
        self.comm_loss = comm_loss
        # FILTER-AWARE ADAPTIVE ATTACKER (§5.11 rebuttal) — an attacker that KNOWS the temporal filter:
        #  * phantom_jitter (m): per-frame zero-mean Gaussian added to the broadcast phantom centre.
        #    Intent: try to fake "honest noise". PREDICTION: fails — jitter raises the offset VARIANCE
        #    but not its MEAN, so the running-mean test is unaffected (mean still = the gap vector).
        #  * phantom_duty in (0,1]: broadcast the phantom only this fraction of frames (intermittent
        #    lying), interleaving the traitor's honest view on the off-frames to DILUTE the bucket mean.
        #    This trades detection for harm: at low duty the mean shrinks (toward eps) but so does the
        #    blocked-time -> a softer form of the stealth/harm bind. (The hard bind is camouflage_gap:
        #    small gap -> small offset -> evades but blocks no new space -> harmless.)
        self.phantom_jitter = phantom_jitter
        self.phantom_duty = phantom_duty
        self._bc_phantom_step = -1
        self._bc_phantom = None                 # cached per-step broadcast phantoms (or None if suppressed)
        # ROBUST FILTER knob: effective contradiction tolerance = verify_eps + verify_k_sigma * sensor_noise.
        # verify_k_sigma=0 -> the naive fixed-threshold rule (noise-fragile, the strawman baseline).
        # verify_k_sigma>0 -> noise-aware: honest noisy matches (~sqrt(2)*sigma off) pass; only WILDLY
        # off broadcasts (open-space phantoms, meters from any real obstacle) still flag. Pair with a
        # slower trust_alpha so a single noisy mismatch can't condemn an honest neighbor.
        self.verify_k_sigma = verify_k_sigma
        # TEMPORAL-TRUST (P4) — the camouflage slow path. Single-frame robust check can't separate a
        # phantom hugging a real obstacle inside the widened eps band; but the per-frame OFFSET VECTOR
        # d = (j's reported pos) - (ego's own sensed pos of the matched obstacle) is ZERO-MEAN for an
        # honest neighbor (cancels over frames) and a PERSISTENT bias for a camouflage liar. We keep a
        # per-(ego,neighbor,ego-track) running vector mean; once a bucket has >= temporal_min_k samples,
        # ||mean|| > temporal_bias_eps marks the neighbor as fabricating. Composes (logical OR) with the
        # single-frame robust check, which stays the fast path for open-space (wall) phantoms.
        self.temporal_defense = temporal_defense
        self.temporal_bias_eps = temporal_bias_eps      # tight threshold (m); ~ honest mean-bias p95
        self.temporal_min_k = temporal_min_k            # min frames in a bucket before a verdict
        self._tbias = {}                                # {(idx,j): {mstar: [sum_x, sum_y, count]}}
        self._sense_step = -1
        self._sensed = np.empty((self.n_drones, 0, 2), dtype=np.float32)   # per-drone noisy views
        self._sradii = np.empty((0,), dtype=np.float32)
        self._in_range = np.zeros((self.n_drones, 0), dtype=bool)

    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)     # resets trust + regenerates phantoms
        self._tbias = {}                         # temporal memory is per-episode
        self._sense_step = -1
        self._bc_phantom_step = -1
        self._bc_phantom = None
        return out

    # ---- per-step phantom broadcast (shared across observers): intermittent duty + jitter ----
    def _broadcast_phantoms(self):
        """Returns (centers(P,2), radii(P,)) the traitors broadcast THIS frame, or None if suppressed.
        One draw per step (cached) so every observer/traitor sees the same fabricated value, as a real
        coordinated attacker would emit. With jitter=0 and duty=1 this is exactly self._phantoms."""
        if self._bc_phantom_step == self.steps:
            return self._bc_phantom
        self._bc_phantom_step = self.steps
        if not len(self._phantoms):
            self._bc_phantom = None
            return None
        if self.phantom_duty < 1.0:              # intermittent lying: evenly-spaced on-window of length duty
            period = 10
            on = (self.steps % period) < int(round(self.phantom_duty * period))
            if not on:
                self._bc_phantom = None
                return None
        centers = self._phantoms[:, :2].astype(np.float32).copy()
        if self.phantom_jitter > 0.0:            # zero-mean jitter: fakes noise but leaves the mean intact
            centers = centers + np.random.normal(0.0, self.phantom_jitter, centers.shape).astype(np.float32)
        self._bc_phantom = (centers, self._phantoms[:, 2])
        return self._bc_phantom

    # ---- temporal-trust slow path: accumulate offset-vector running mean per (ego,neighbor,track) ----
    def _temporal_update(self, idx, j, bc_c):
        """Associate each broadcast obstacle to ego's nearest sighted obstacle (track id m*),
        update the per-pair running offset-vector mean, then judge: a bucket with >= temporal_min_k
        samples whose ||mean|| exceeds temporal_bias_eps contradicts neighbor j.
        Returns (judged, contradicted)."""
        if self.lidar_blind[idx] or not len(bc_c) or self._sensed.shape[1] == 0:
            return False, False
        in_i = self._in_range[idx]
        if not in_i.any():
            return False, False
        ego_idx = np.where(in_i)[0]              # ego's own sighted obstacle track-ids
        ego_pts = self._sensed[idx][in_i]        # ego's noisy views of them
        pos = self.positions[idx]
        buckets = self._tbias.setdefault((idx, j), {})
        for o in bc_c:
            if np.linalg.norm(pos - o) > self.lidar_range:
                continue                         # ego can't verify what it can't reach
            a = int(np.argmin(np.linalg.norm(ego_pts - o, axis=1)))
            mstar = int(ego_idx[a])
            d = np.asarray(o, dtype=np.float32) - ego_pts[a]
            b = buckets.get(mstar)
            if b is None:
                b = buckets[mstar] = [0.0, 0.0, 0]
            b[0] += float(d[0]); b[1] += float(d[1]); b[2] += 1
        judged = contradicted = False
        for sx, sy, c in buckets.values():
            if c >= self.temporal_min_k:
                judged = True
                if float(np.hypot(sx / c, sy / c)) > self.temporal_bias_eps:
                    contradicted = True
                    break
        return judged, contradicted

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
            if self.comm_loss > 0.0 and np.random.random() < self.comm_loss:
                continue                                  # dropped packet: no fusion, no verification this frame
            bc_c, bc_r = [], []
            if not self.lidar_blind[j] and M:
                m = self._in_range[j]
                if m.any():
                    bc_c.append(self._sensed[j][m]); bc_r.append(self._sradii[m])
            if self.false_obstacle_attack and (j in self.traitor_indices) and len(self._phantoms):
                bcp = self._broadcast_phantoms()          # adaptive: jitter + intermittent duty
                if bcp is not None:
                    bc_c.append(bcp[0]); bc_r.append(bcp[1])
            if not bc_c:
                continue
            bc_c = np.concatenate(bc_c); bc_r = np.concatenate(bc_r)

            if self.trust_defense or self.temporal_defense:
                judged = contradicted = False
                if self.trust_defense:                       # single-frame robust (fast path)
                    js, cs = self._ego_judgement(idx, bc_c)
                    judged |= js; contradicted |= cs
                if self.temporal_defense:                    # temporal offset-bias (slow path)
                    jt, ct = self._temporal_update(idx, j, bc_c)
                    judged |= jt; contradicted |= ct
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
