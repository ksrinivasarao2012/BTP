"""
PAPER ENV 1/2 — Collaborative Perception under Sensor Dropout (clean, Phase-3).

Self-contained, documented re-statement of the slot-fusion environment used for the
dropout-robustness result. It reproduces EXACTLY the obs math the trained models
(`raster_slot_fusion_{ON,OFF}_stage2_final.zip`) were trained on, so eval numbers are
identical to the sandbox `swarm_env_raster.py` — but with all probe/legacy cruft removed.

Observation: 650-d = [ local(130) || global(520) ].  The actor reads obs[:130], critic obs[130:].
The own-LiDAR slot obs[6:54] is REPLACED by a fused 48-d channel:

    fused[6:54] = normalize( cast48( UNION{ ego own obstacles (if sighted),
                                            sender-gated neighbor obstacles,
                                            other drones } ) )

Mechanisms:
  * lidar_dropout / dropout_sustain : per-step, per-drone, SUSTAINED sensor failure. A "blind"
        drone contributes nothing to its own sensing AND (sender-gating) shares nothing with others.
  * use_shared_map=True  -> ON  (neighbors fill the fused slot; survives the drone's own blindness)
  * use_shared_map=False -> OFF (own LiDAR only; the comm-disabled ablation baseline)

The min-distance fusion (inside cast48) is what buys dropout-robustness — and, as shown in the
companion env (`env_byzantine_trust.py`), is also the attack surface a liar exploits.
"""
import numpy as np
from gymnasium import spaces
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

LOCAL_BASE = 130
GLOBAL = 520
OBS_DIM = LOCAL_BASE + GLOBAL    # 650


class CollabPerceptionEnv(SwarmLidarEnv_StepB10_8_0m):
    def __init__(self, *args, lidar_dropout=0.0, dropout_sustain=20, use_shared_map=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.lidar_dropout = lidar_dropout        # prob a non-blind drone goes blind this step
        self.dropout_sustain = dropout_sustain    # how many steps it stays blind once it goes blind
        self.use_shared_map = use_shared_map      # ON (fused neighbors) vs OFF (own LiDAR only)
        self.obs_size = OBS_DIM
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,),
                                                 dtype=np.float32) for a in self.possible_agents}
        self.observation_space = self.observation_spaces["drone_0"]
        self.lidar_blind = np.zeros(self.n_drones, dtype=bool)
        self._blind_timer = np.zeros(self.n_drones, dtype=int)
        self._dropout_step = -1

    # ---- dropout state (sampled once per env-step, sustained per drone) ----
    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)
        self.lidar_blind[:] = False
        self._blind_timer[:] = 0
        self._dropout_step = -1
        return out

    def _sample_dropout(self):
        if self._dropout_step == self.steps:
            return
        self._dropout_step = self.steps
        if self.lidar_dropout <= 0.0:
            self.lidar_blind[:] = False
            return
        for j in range(self.n_drones):
            if self._blind_timer[j] > 0:
                self._blind_timer[j] -= 1
                self.lidar_blind[j] = True
            elif np.random.random() < self.lidar_dropout:
                self._blind_timer[j] = self.dropout_sustain - 1
                self.lidar_blind[j] = True
            else:
                self.lidar_blind[j] = False

    # ---- ray-cast: 48-d {min,mean,std} over 16 sectors vs given obstacle circles + walls ----
    def _cast48(self, pos, centers, radii, max_range):
        ray_dirs = self.ray_dirs
        nr = ray_dirs.shape[0]
        md = np.full(nr, max_range, dtype=np.float32)
        for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            mask = ray_dirs[:, axis] * direction > 1e-6
            if np.any(mask):
                d = (boundary - pos[axis]) / ray_dirs[mask, axis]
                md[mask] = np.minimum(md[mask], np.where(d > 0, d, max_range).astype(np.float32))
        if len(centers):
            rel = centers - pos
            proj = rel @ ray_dirs.T
            rp2 = np.sum(rel**2, axis=1, keepdims=True)
            d2 = rp2 - proj**2
            rad = (radii + self.drone_radius)[:, None]
            hit = (proj > 0) & (d2 < rad**2)
            dists = proj - np.sqrt(np.maximum(rad**2 - d2, 0))
            dists[~hit] = max_range
            md = np.minimum(md, np.min(dists, axis=0))      # <-- the min-fusion
        sec = md.reshape(16, 12)
        return np.concatenate([np.min(sec, axis=1), np.mean(sec, axis=1), np.std(sec, axis=1)]).astype(np.float32)

    # ---- fused 48-d slot: union of {ego (if sighted), sender-gated neighbors, drones} at 8m ----
    def _fused_lidar(self, idx):
        pos = self.positions[idx]
        c_list, r_list = [], []

        # 1. Ego's own obstacles (only if sighted; if blind, ego senses nothing)
        if not self.lidar_blind[idx] and self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            c_list.append(arr[:, :2]); r_list.append(arr[:, 2])

        # 2. Sender-gated neighbor obstacles (only from non-blind, in-comm-range neighbors)
        if self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            centers, radii = arr[:, :2], arr[:, 2]
            keep = np.zeros(len(centers), dtype=bool)
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents:
                    continue
                if self.lidar_blind[j]:                                   # sender-gating
                    continue
                if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                    continue
                dj = np.linalg.norm(centers - self.positions[j], axis=1)
                keep |= (dj <= self.lidar_range)
            if keep.any():
                c_list.append(centers[keep]); r_list.append(radii[keep])

        # 3. Other drones (always visible, for collision avoidance)
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))

        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range

    def _own_lidar_only(self, idx):
        """OFF ablation: own obstacles (if sighted) + drones, no neighbor sharing."""
        pos = self.positions[idx]
        c_list, r_list = [], []
        if not self.lidar_blind[idx] and self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            c_list.append(arr[:, :2]); r_list.append(arr[:, 2])
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))
        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range

    def _observe(self, agent):
        self._sample_dropout()
        idx = self.agent_name_mapping[agent]
        base = super()._observe(agent)        # 650: [local(130), global(520)]; own lidar at [6:54]
        base[6:54] = self._fused_lidar(idx) if self.use_shared_map else self._own_lidar_only(idx)
        return base.astype(np.float32)        # 650-d
