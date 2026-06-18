"""
PAPER ENV 2b — Adaptive / camouflaged Byzantine attack (extends env_byzantine_trust).

The base attack ("wall") drops a phantom barrier in the locally-open near-goal zone, which a
sighted drone trivially contradicts. This file adds a HARDER, more realistic placement:

  attack_mode = "wall"        -> inherited near-goal phantom barrier (easy to detect)
  attack_mode = "camouflage"  -> phantoms HUG real obstacles that sit on the spawn->goal
                                 corridor, each pushed toward the corridor midline so it
                                 EXTENDS a real obstacle into the gap the drones use.

Why camouflage is the proper test:
  A sighted drone looking where the phantom sits ALSO sees a real obstacle right next to it,
  so the "nothing is there -> fabricated" consistency check is murkier. The experiment reveals
  the attacker's intrinsic bind (a key finding): to EVADE a consistency filter the phantom must
  sit so close to a real obstacle that it blocks little NEW space (stealthy => harmless); to
  block new space it must protrude into the open (harmful => detectable). `camouflage_gap`
  tunes exactly this stealth/harm dial.
"""
import numpy as np
from env_byzantine_trust import ByzantineTrustEnv


class AdaptiveByzantineEnv(ByzantineTrustEnv):
    def __init__(self, *args, attack_mode="wall", camouflage_gap=0.3, **kwargs):
        super().__init__(*args, **kwargs)
        self.attack_mode = attack_mode          # "wall" | "camouflage"
        self.camouflage_gap = camouflage_gap    # phantom surface-to-obstacle gap (m); small = stealthy

    def _generate_phantoms(self):
        if not (self.false_obstacle_attack and self.traitor_indices):
            self._phantoms = np.empty((0, 3), dtype=np.float32)
            return
        if self.attack_mode != "camouflage" or not self.obstacles:
            super()._generate_phantoms()        # "wall" (or no real obstacles to hug)
            return

        real = np.array(self.obstacles, dtype=np.float32)          # (M,3): x,y,r
        centroid = np.mean(self.positions, axis=0).astype(np.float32)
        approach = self.goal - centroid
        napp = float(np.linalg.norm(approach))
        approach = (approach / napp).astype(np.float32) if napp > 1e-6 else np.array([1.0, 0.0], np.float32)

        rel = real[:, :2] - centroid                                # (M,2)
        proj = rel @ approach                                       # along-corridor distance
        perp_vec = rel - proj[:, None] * approach[None, :]          # offset from corridor midline
        perp_dist = np.linalg.norm(perp_vec, axis=1)

        # candidate real obstacles: those BETWEEN spawn and goal (on the corridor)
        on_corridor = (proj > 0.0) & (proj < napp)
        cand = np.where(on_corridor)[0]
        if len(cand) == 0:
            cand = np.arange(len(real))                             # fallback: any obstacle
        # nearest to the corridor midline first (most in-the-way)
        chosen = cand[np.argsort(perp_dist[cand])][: self.n_phantom]

        phantoms = []
        for ci in chosen:
            rc, rr = real[ci, :2], float(real[ci, 2])
            d = -perp_vec[ci]                                       # push from obstacle toward midline
            nd = float(np.linalg.norm(d))
            d = (d / nd) if nd > 1e-6 else np.array([-approach[1], approach[0]], np.float32)
            center = rc + d * (rr + self.phantom_radius + self.camouflage_gap)
            center = np.clip(center, 0.3, self.WIDTH - 0.3)
            phantoms.append([center[0], center[1], self.phantom_radius])

        self._phantoms = (np.array(phantoms, dtype=np.float32)
                          if phantoms else np.empty((0, 3), dtype=np.float32))
