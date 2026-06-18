"""
PAPER ENV 2/2 — Byzantine False-Obstacle Attack + Consistency-Trust Defense (Phase-4).

Extends `CollabPerceptionEnv` (env_collab_perception.py). With attack and defense OFF it
reproduces the Phase-3 numbers exactly (per-neighbor fusion is min-idempotent w.r.t. the
pooled fusion, so the cast48 output is identical).

THREAT — coherent false obstacles (the only meaningful comm attack here):
  Each traitor broadcasts a PERSISTENT phantom "wall" placed across the goal approach
  (fabricated; NOT in self.obstacles, so the map stays truly solvable). Because the fused
  slot is a MIN over {own, neighbor, phantom}, a fabricated near-obstacle wins the min and
  overrides even a fully-sighted drone's own true LiDAR — hence the attack is dropout-
  independent (verified: ~10-12 pp honest-success drop at k=2 even at 0% blindness).

DEFENSE — consistency-trust filter ("T-Cell self / non-self"):
  Per (observer i, neighbor j) trust score t_ij in [0,1], EWMA, reset to 1.0 each episode.
    * When i is SIGHTED, it judges j's broadcast: any broadcast obstacle that lies within i's
      own sensing range but matches NO real obstacle there is a contradiction (i is in a
      position to see it; nothing is there -> it is fabricated).
    * A contradiction drives t_ij down; a clean judgement drives it toward 1. When i is blind
      it has no opinion and t_ij is left unchanged (a caught traitor stays caught through the
      blind window -> T-cell memory).
    * A neighbor with t_ij < tau_trust is excluded from i's fusion entirely.
  Honesty notes (disclose in paper):
    - The check reads self.obstacles only to answer "would i's own LiDAR confirm this?",
      i.e. exactly what i physically senses — not a privileged label.
    - A phantom placed atop / very near a real obstacle is unfalsifiable and slips through;
      this is the fundamental limit of consistency detection, not a bug.
"""
import numpy as np
from env_collab_perception import CollabPerceptionEnv


class ByzantineTrustEnv(CollabPerceptionEnv):
    def __init__(self, *args,
                 false_obstacle_attack=False, traitor_indices=None,
                 n_phantom=4, phantom_radius=1.0, phantom_block_dist=3.5, phantom_spacing=1.3,
                 trust_defense=False, trust_alpha=0.5, tau_trust=0.5, verify_eps=0.6, **kwargs):
        super().__init__(*args, **kwargs)
        # ---- attack ----
        self.false_obstacle_attack = false_obstacle_attack
        self.traitor_indices = list(traitor_indices) if traitor_indices else []
        self.n_phantom = n_phantom
        self.phantom_radius = phantom_radius
        self.phantom_block_dist = phantom_block_dist
        self.phantom_spacing = phantom_spacing
        self._phantoms = np.empty((0, 3), dtype=np.float32)
        # ---- defense ----
        self.trust_defense = trust_defense
        self.trust_alpha = trust_alpha
        self.tau_trust = tau_trust
        self.verify_eps = verify_eps
        self.trust = np.ones((self.n_drones, self.n_drones), dtype=np.float32)

    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)
        self.trust[:] = 1.0
        self._generate_phantoms()
        return out

    # ---- phantom wall across the goal approach (fixed per episode) ----
    def _generate_phantoms(self):
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
        centers = np.clip(wall_center[None, :] + offsets[:, None] * perp[None, :],
                          0.3, self.WIDTH - 0.3).astype(np.float32)
        radii = np.full(k, self.phantom_radius, dtype=np.float32)
        self._phantoms = np.concatenate([centers, radii[:, None]], axis=1).astype(np.float32)

    # ---- ego consistency judgement of a broadcast obstacle set ----
    def _ego_judgement(self, idx, cand_centers):
        """Return (judged, contradicted).
        judged=False  -> ego is blind or saw none of the candidates in range -> no opinion.
        contradicted  -> at least one in-sight candidate has no real obstacle there (fabricated)."""
        if self.lidar_blind[idx] or not len(cand_centers):
            return False, False
        pos = self.positions[idx]
        real_c = (np.array(self.obstacles, dtype=np.float32)[:, :2]
                  if self.obstacles else np.empty((0, 2), np.float32))
        judged = False
        for o in cand_centers:
            if np.linalg.norm(pos - o) > self.lidar_range:
                continue                                   # out of ego's sight -> can't judge this one
            judged = True
            if len(real_c) == 0 or float(np.min(np.linalg.norm(real_c - o, axis=1))) > self.verify_eps:
                return True, True                          # in sight, nothing real there -> fabricated
        return judged, False                               # saw some, all consistent

    # ---- fused slot with attack injection + (optional) trust defense ----
    def _fused_lidar(self, idx):
        pos = self.positions[idx]
        real = np.array(self.obstacles, dtype=np.float32) if self.obstacles else np.empty((0, 3), np.float32)
        real_c = real[:, :2] if len(real) else np.empty((0, 2), np.float32)
        c_list, r_list = [], []

        # 1. Ego's own obstacles (only if sighted)
        if not self.lidar_blind[idx] and len(real):
            c_list.append(real[:, :2]); r_list.append(real[:, 2])

        # 2. Per-neighbor broadcasts (real sensed + any fabricated phantoms), with trust gating
        for j in range(self.n_drones):
            if j == idx or self.possible_agents[j] not in self.agents:
                continue
            if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                continue
            bc_c, bc_r = [], []
            # real obstacles j senses (sender-gating: only if j is non-blind)
            if not self.lidar_blind[j] and len(real):
                m = np.linalg.norm(real_c - self.positions[j], axis=1) <= self.lidar_range
                if m.any():
                    bc_c.append(real_c[m]); bc_r.append(real[m, 2])
            # fabricated phantoms (traitor; attack on; broadcast regardless of j's own blindness)
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
                    continue                                # distrusted neighbor excluded entirely
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

    # ---- detection readout (for eval metrics) ----
    def predicted_traitors(self):
        """Per honest observer, the set of neighbors it currently distrusts (t_ij < tau)."""
        honest = [i for i in range(self.n_drones) if i not in self.traitor_indices]
        return {i: [j for j in range(self.n_drones) if j != i and self.trust[i, j] < self.tau_trust]
                for i in honest}
