"""
Collision Diagnostic for v15 Master.

Runs the TRAINED v15 model on the ORIGINAL v15 environment and measures
WHY collisions happen, instead of guessing from code. For every collision it records:
  - sub-cause: wall / obstacle / drone-drone
  - speed at impact
  - for drone-drone: previous-step separation + closing speed  (detects tunneling)

A "tunneling" collision = two drones that were clearly separated (>0.45m) one step
ago but are now in collision — i.e. they moved through each other in a single step.

No GPU needed. ~200 episodes, a few minutes on CPU.
"""

import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np

V15_DIR = r"D:\Swarm\BTP\Phase B\Phase_B5_Synchronization\v10_IEEE_Final"
sys.path.insert(0, V15_DIR)

from swarm_env_step_B5_v15_master import SwarmLidarEnv_v15_Final
import train_step_B5_sync_v15_master  # registers MAPPO_Policy_v15 / extractor for loading
from stable_baselines3 import PPO

MODEL_PATH    = r"D:\Swarm\BTP\models\v15_Master_Final_50M"
N_EPISODES    = 200
TEST_DENSITY  = 0.26      # the density v15 was trained/locked at
R_SENSOR_EVAL = 8.0       # final curriculum values
R_COMM_EVAL   = 10.0


class DiagEnv(SwarmLidarEnv_v15_Final):
    """Identical to v15 but records the collision sub-cause and impact kinematics."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.collision_events = []   # list of dicts

    def step(self, actions):
        if not self.agents:
            return {}, {}, {}, {}, {}
        self._prepare_broadcasts()
        old_p = np.copy(self.positions)
        old_v = np.copy(self.velocities)
        self._compute_distance_matrix()

        for agent, act in actions.items():
            idx = self.agent_name_mapping[agent]; act = np.clip(act, -1.0, 1.0)
            self.velocities[idx] += act * self.dt * 10.0
            nc = sum(1 for j in range(self.n_drones)
                     if j != idx and f"drone_{j}" in self.agents and self.dist_matrix[idx, j] < 1.0)
            mx = max(self.max_velocity * np.exp(-0.08 * nc), 1.1)
            sp = np.linalg.norm(self.velocities[idx])
            if sp > mx:
                self.velocities[idx] = (self.velocities[idx] / sp) * mx
            self.positions[idx] = np.clip(self.positions[idx] + self.velocities[idx] * self.dt, 0, 20.0)

        self.steps += 1
        self._compute_distance_matrix()
        self.lidar_cache = {a: self._ray_cast(self.agent_name_mapping[a]) for a in self.agents}
        self._prepare_global_state()

        rew, terms, truncs = {}, {}, {}
        for a in self.agents:
            idx = self.agent_name_mapping[a]; pos = self.positions[idx]
            speed = np.linalg.norm(self.velocities[idx])

            hw = min(pos[0], 20 - pos[0], pos[1], 20 - pos[1]) <= 0.05
            ho = any(np.linalg.norm(pos - np.array([ox, oy])) < 0.15 + orad
                     for ox, oy, orad in self.obstacles)
            hd = any(self.dist_matrix[idx, j] < 0.3
                     for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents)

            if hw or ho or hd:
                cause = "wall" if hw else ("obstacle" if ho else "drone")
                ev = {"cause": cause, "impact_speed": float(speed)}
                if cause == "drone":
                    # find offending neighbour
                    best_j, best_d = None, 1e9
                    for j in range(self.n_drones):
                        if j != idx and f"drone_{j}" in self.agents and self.dist_matrix[idx, j] < best_d:
                            best_d, best_j = self.dist_matrix[idx, j], j
                    if best_j is not None:
                        d_prev = float(np.linalg.norm(old_p[idx] - old_p[best_j]))
                        d_now  = float(best_d)
                        closing = (d_prev - d_now) / self.dt
                        ev.update({"d_prev": d_prev, "d_now": d_now, "closing_speed": float(closing),
                                   "tunneled": d_prev > 0.45})
                self.collision_events.append(ev)
                terms[a] = True
            else:
                path_dist = self.get_shortest_path_distance(pos)
                terms[a] = path_dist < 0.75

            truncs[a] = self.steps >= self.max_steps
            rew[a] = 0.0

        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms.get(a, False) or truncs.get(a, False):
                self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0])
                self.agents.remove(a)
        return obs, rew, terms, truncs, self.infos


def run():
    print(f"Loading model: {MODEL_PATH}")
    model = PPO.load(MODEL_PATH, device="cpu")

    env = DiagEnv(target_density=TEST_DENSITY)
    env.set_curriculum(R_SENSOR_EVAL, R_COMM_EVAL)
    env.set_target_density(TEST_DENSITY)

    n_success = n_timeout = 0
    total_drone_arrivals = 0

    for ep in range(N_EPISODES):
        obs_dict, _ = env.reset()
        env.set_curriculum(R_SENSOR_EVAL, R_COMM_EVAL)
        done = False
        while env.agents:
            agents = list(env.agents)
            obs_batch = np.array([obs_dict[a] for a in agents], dtype=np.float32)
            actions, _ = model.predict(obs_batch, deterministic=True)
            act_dict = {a: actions[i] for i, a in enumerate(agents)}
            obs_dict, _, terms, truncs, _ = env.step(act_dict)
            for a in agents:
                if terms.get(a, False) and a not in env.agents:
                    # arrived or collided — collisions already logged; count arrivals separately below
                    pass
        if (ep + 1) % 25 == 0:
            print(f"  ...{ep+1}/{N_EPISODES} episodes")

    ev = env.collision_events
    total = len(ev)
    print("\n" + "=" * 55)
    print(f"COLLISION DIAGNOSTIC — {N_EPISODES} episodes, density={TEST_DENSITY}")
    print("=" * 55)
    print(f"Total collisions logged: {total}")
    if total == 0:
        print("No collisions — nothing to diagnose.")
        return

    by_cause = {}
    for e in ev:
        by_cause.setdefault(e["cause"], []).append(e)

    print(f"\n{'Cause':>10} | {'Count':>6} | {'%':>6} | {'Avg impact speed':>16}")
    print("-" * 50)
    for cause in ["wall", "obstacle", "drone"]:
        lst = by_cause.get(cause, [])
        if not lst: continue
        pct = len(lst) / total * 100
        avg_sp = np.mean([e["impact_speed"] for e in lst])
        print(f"{cause:>10} | {len(lst):>6} | {pct:>5.1f}% | {avg_sp:>16.2f}")

    drones = by_cause.get("drone", [])
    if drones:
        tunneled = [e for e in drones if e.get("tunneled")]
        print(f"\nDrone-drone collisions: {len(drones)}")
        print(f"  Tunneled (prev gap >0.45m -> collision in 1 step): {len(tunneled)} "
              f"({len(tunneled)/len(drones)*100:.1f}%)")
        print(f"  Avg previous-step separation: {np.mean([e['d_prev'] for e in drones]):.3f} m")
        print(f"  Avg closing speed at impact:  {np.mean([e['closing_speed'] for e in drones]):.2f} m/s")

    print("\nINTERPRETATION:")
    wpct = len(by_cause.get('wall', [])) / total * 100
    dpct = len(drones) / total * 100
    opct = len(by_cause.get('obstacle', [])) / total * 100
    dom = max([('wall', wpct), ('obstacle', opct), ('drone', dpct)], key=lambda x: x[1])
    print(f"  Dominant cause: {dom[0]} ({dom[1]:.1f}%)")
    if drones and len(tunneled) / len(drones) > 0.3:
        print("  -> Significant tunneling. Reducing per-step displacement (lower dt) will help.")
    if wpct > 30:
        print("  -> Walls are a major cause. Zeroing boundary velocity will help.")
    if dpct > 30 and (not drones or len(tunneled)/len(drones) <= 0.3):
        print("  -> Drone collisions are mostly low-speed/decision-based, NOT tunneling.")
        print("     This points to a reward/policy problem, not a physics fix.")


if __name__ == "__main__":
    run()
