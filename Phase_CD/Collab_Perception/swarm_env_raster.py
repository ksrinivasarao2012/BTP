"""
B1 — Raster architecture env (Lever 2).

Adds a SEPARATE 48-d "communicated obstacle map" channel at obs[130:178] (16 sectors x {min,mean,std}
of neighbor-shared obstacles, ego frame), distinct from the ego's own LiDAR [6:54] so it survives
LiDAR dropout. Total obs = 130 + 48 + 520 = 698.

Key mechanisms:
  * lidar_dropout (per-step, per-drone, SUSTAINED): a drone's own LiDAR is masked while it is "blind".
  * SENDER-GATING: a blind neighbor shares NOTHING (cannot broadcast what it does not sense). This is the
    consistency fix — failure model. Only non-blind comm-neighbors contribute to the shared map.
  * use_shared_map=False -> shared block = zeros (the comm-OFF ablation).
  * probe_lidar_slot=True -> (probe only) returns a 650-d obs with the shared map IN the lidar slot and the
    ego blind to its own obstacles, so M0 can navigate on it ZERO-SHOT (re-verifies ~88, validates this code).

Trust-weighted fusion (B4) will later filter neighbors before they contribute; here all non-blind
neighbors are trusted (no traitors yet).
"""
import numpy as np
from gymnasium import spaces
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

SHARED_DIM = 48          # 16 sectors x {min, mean, std}
LOCAL_BASE = 130
GLOBAL = 520
OBS_DIM = LOCAL_BASE + SHARED_DIM + GLOBAL   # 698


class SwarmLidarEnv_Raster(SwarmLidarEnv_StepB10_8_0m):
    def __init__(self, *args, lidar_dropout=0.0, dropout_sustain=20, use_shared_map=True,
                 probe_lidar_slot=False, straight_line_goal=False, slot_fusion=False,
                 false_obstacle_attack=False, traitor_indices=None, n_phantom=4,
                 phantom_radius=1.0, phantom_block_dist=3.5, phantom_spacing=1.3, **kwargs):
        super().__init__(*args, **kwargs)
        self.lidar_dropout = lidar_dropout          # prob a non-blind drone goes blind this step
        self.dropout_sustain = dropout_sustain      # how many steps it stays blind
        self.use_shared_map = use_shared_map        # False -> comm-OFF (shared block zeroed)
        self.probe_lidar_slot = probe_lidar_slot    # probe-only: shared map -> lidar slot, 650-d
        self.straight_line_goal = straight_line_goal  # GATE-0 PROBE: replace the global-Dijkstra
        #   routed heading at obs[2:4] with a naive straight-line bearing (goal-ego, no obstacle
        #   knowledge). Strictly less info than Dijkstra -> cannot add leakage (invariant L3).
        self.slot_fusion = slot_fusion              # NEW: fuse shared map INTO lidar slot [6:54],
        #   return 650-d (no separate channel). When True, use_shared_map controls ON/OFF.
        # ---- Byzantine false-obstacle attack (Phase 4 potency probe) ----
        # Traitors broadcast a coherent, persistent PHANTOM wall placed across the goal approach.
        # Phantoms are NOT in self.obstacles (real solvability is unaffected) — they only corrupt
        # the FUSED obs[6:54] of honest victims that have a traitor in comm range. The attack
        # therefore ONLY touches the shared/ON path; the OFF path (own LiDAR) has no comm surface.
        self.false_obstacle_attack = false_obstacle_attack
        self.traitor_indices = list(traitor_indices) if traitor_indices else []
        self.n_phantom = n_phantom
        self.phantom_radius = phantom_radius
        self.phantom_block_dist = phantom_block_dist   # phantom wall this many m back from goal
        self.phantom_spacing = phantom_spacing         # gap between phantoms in the wall
        self._phantoms = np.empty((0, 3), dtype=np.float32)
        # obs_size: 650-d if probe or slot_fusion, else 698-d (separate channel)
        self.obs_size = LOCAL_BASE + GLOBAL if (probe_lidar_slot or slot_fusion) else OBS_DIM
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,),
                                                  dtype=np.float32) for a in self.possible_agents}
        self.observation_space = self.observation_spaces["drone_0"]
        self.lidar_blind = np.zeros(self.n_drones, dtype=bool)
        self._blind_timer = np.zeros(self.n_drones, dtype=int)
        self._dropout_step = -1

    # ---- dropout state (sampled once per step, sustained per drone) ----
    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)
        self.lidar_blind[:] = False
        self._blind_timer[:] = 0
        self._dropout_step = -1
        self._generate_phantoms()
        return out

    def _generate_phantoms(self):
        """Build a coherent phantom 'wall' across the goal approach (per episode, fixed).

        Placed phantom_block_dist metres back from the goal, perpendicular to the
        spawn->goal direction, so every drone heading to the shared goal meets it. Phantoms
        are fabricated (not in self.obstacles), so the map stays truly solvable — a victim
        that ignored the lie could still reach the goal."""
        if not (self.false_obstacle_attack and self.traitor_indices):
            self._phantoms = np.empty((0, 3), dtype=np.float32)
            return
        centroid = np.mean(self.positions, axis=0)
        approach = self.goal - centroid
        n = float(np.linalg.norm(approach))
        if n < 1e-6:
            self._phantoms = np.empty((0, 3), dtype=np.float32)
            return
        approach = approach / n
        perp = np.array([-approach[1], approach[0]], dtype=np.float32)
        wall_center = self.goal - approach * self.phantom_block_dist
        k = self.n_phantom
        offsets = (np.arange(k) - (k - 1) / 2.0) * self.phantom_spacing
        centers = wall_center[None, :] + offsets[:, None] * perp[None, :]
        centers = np.clip(centers, 0.3, self.WIDTH - 0.3).astype(np.float32)
        radii = np.full(k, self.phantom_radius, dtype=np.float32)
        self._phantoms = np.concatenate([centers, radii[:, None]], axis=1).astype(np.float32)

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

    # ---- ray-cast helper: 48-d {min,mean,std} against given obstacle circles + walls ----
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
            md = np.minimum(md, np.min(dists, axis=0))
        sec = md.reshape(16, 12)
        return np.concatenate([np.min(sec, axis=1), np.mean(sec, axis=1), np.std(sec, axis=1)]).astype(np.float32)

    # ---- unified fused channel: single _cast48 over union of {ego obstacles, sender-gated neighbors, drones} at 8m scale ----
    def _fused_lidar(self, idx):
        """Single _cast48 at 8m scale (ego's training regime, M0's native [6:54] scale).

        Union: ego obstacles (if sighted) + sender-gated neighbor obstacles + drones.
        Cast at lidar_range (8m), NOT collab_range (12m), to preserve M0's training regime.
        """
        pos = self.positions[idx]
        c_list, r_list = [], []

        # 1. Ego's own obstacles (only if sighted; if blind, skip ego sensing)
        if not self.lidar_blind[idx] and self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            c_list.append(arr[:, :2])
            r_list.append(arr[:, 2])

        # 2. Sender-gated neighbor obstacles (only from non-blind, in-range neighbors)
        if self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            centers, radii = arr[:, :2], arr[:, 2]
            keep = np.zeros(len(centers), dtype=bool)
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents:
                    continue
                if self.lidar_blind[j]:                                   # SENDER-GATING: blind -> shares nothing
                    continue
                if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                    continue
                dj = np.linalg.norm(centers - self.positions[j], axis=1)
                keep |= (dj <= self.lidar_range)                          # obstacles neighbor j senses (within 8m of neighbor)
            if keep.any():
                c_list.append(centers[keep])
                r_list.append(radii[keep])

        # 2b. Byzantine false-obstacle injection: any in-range, active traitor broadcasts the
        # fabricated phantom wall into this victim's fused map (defense OFF = no filtering).
        if self.false_obstacle_attack and len(self._phantoms):
            for j in self.traitor_indices:
                if j == idx or self.possible_agents[j] not in self.agents:
                    continue
                if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                    continue
                c_list.append(self._phantoms[:, :2])
                r_list.append(self._phantoms[:, 2])
                break  # full wall injected once; identical walls from extra traitors don't stack

        # 3. Other drones (always visible for collision avoidance)
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))

        # Single union, one _cast48 at 8m scale (lidar_range, M0's native scale)
        if c_list:
            centers = np.concatenate(c_list)
            radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32)
            radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range

    # ---- the 48-d shared-obstacle map (sender-gated, trusted neighbors only) ----
    def _shared_lidar(self, idx):
        pos = self.positions[idx]
        if not self.obstacles:
            return self._cast48(pos, np.empty((0, 2), np.float32), np.empty((0,), np.float32), self.collab_range) / self.collab_range
        arr = np.array(self.obstacles, dtype=np.float32)
        centers, radii = arr[:, :2], arr[:, 2]
        keep = np.zeros(len(centers), dtype=bool)
        for j in range(self.n_drones):
            if j == idx or self.possible_agents[j] not in self.agents:
                continue
            if self.lidar_blind[j]:                                   # SENDER-GATING: blind -> shares nothing
                continue
            if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                continue
            dj = np.linalg.norm(centers - self.positions[j], axis=1)
            keep |= (dj <= self.lidar_range)                          # obstacles neighbor j senses
        return self._cast48(pos, centers[keep], radii[keep], self.collab_range) / self.collab_range

    def _probe_lidar(self, idx):
        """PROBE-ONLY lidar slot: shared obstacles (sender-gated) PLUS drones (so M0 keeps its
        lidar-based drone avoidance) + walls. Matches full_blind: ego blind to own OBSTACLES only."""
        pos = self.positions[idx]
        c_list, r_list = [], []
        if self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            keep = np.zeros(len(arr), dtype=bool)
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents or self.lidar_blind[j]:
                    continue
                if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                    continue
                keep |= (np.linalg.norm(arr[:, :2] - self.positions[j], axis=1) <= self.lidar_range)
            if keep.any():
                c_list.append(arr[keep, :2]); r_list.append(arr[keep, 2])      # _cast48 adds drone_radius
        others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
        if others:
            c_list.append(self.positions[others])
            r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))  # ->2*drone_radius
        if c_list:
            centers = np.concatenate(c_list); radii = np.concatenate(r_list)
        else:
            centers = np.empty((0, 2), np.float32); radii = np.empty((0,), np.float32)
        return self._cast48(pos, centers, radii, self.collab_range) / self.collab_range

    def _observe(self, agent):
        self._sample_dropout()
        idx = self.agent_name_mapping[agent]
        base = super()._observe(agent)        # 650: [local(130), global(520)] ; own lidar at [6:54]

        if self.straight_line_goal:
            # GATE-0 PROBE: overwrite the Dijkstra heading at obs[2:4] with a unit straight-line
            # bearing to the goal. Uses only self.goal (disclosed destination) + ego position (L3).
            d = self.goal - self.positions[idx]
            n = float(np.linalg.norm(d))
            base[2:4] = (d / n).astype(np.float32) if n > 1e-6 else np.zeros(2, dtype=np.float32)

        if self.probe_lidar_slot:
            # PROBE: ego blind to own obstacles; put shared map (+drones) in the lidar slot for zero-shot M0.
            base[6:54] = self._probe_lidar(idx)
            return base                        # 650-d

        # Slot-fusion path: single unified _cast48 over union at 8m scale, return 650-d
        if self.slot_fusion:
            if self.use_shared_map:
                # ON: union of {ego obstacles (if sighted), sender-gated neighbors, drones} at 8m scale
                fused = self._fused_lidar(idx)
            else:
                # OFF: ego obstacles only (if sighted) + drones, at 8m scale (fair baseline, no neighbors)
                pos = self.positions[idx]
                c_list, r_list = [], []
                if not self.lidar_blind[idx] and self.obstacles:
                    arr = np.array(self.obstacles, dtype=np.float32)
                    c_list.append(arr[:, :2])
                    r_list.append(arr[:, 2])
                others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
                if others:
                    c_list.append(self.positions[others])
                    r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))
                if c_list:
                    centers = np.concatenate(c_list)
                    radii = np.concatenate(r_list)
                else:
                    centers = np.empty((0, 2), np.float32)
                    radii = np.empty((0,), np.float32)
                fused = self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range
            base[6:54] = fused
            return base.astype(np.float32)  # 650-d

        # Legacy path (backward compat): separate 48-d shared-map channel at [130:178], returns 698-d
        if self.lidar_blind[idx]:
            base[6:38] = 1.0                   # min+mean sectors -> max range (normalized /lidar_range)
            base[38:54] = 0.0                  # std -> 0  (sensor sees nothing)
        shared = self._shared_lidar(idx) if self.use_shared_map else np.zeros(SHARED_DIM, dtype=np.float32)
        return np.concatenate([base[:130], shared, base[130:]]).astype(np.float32)
