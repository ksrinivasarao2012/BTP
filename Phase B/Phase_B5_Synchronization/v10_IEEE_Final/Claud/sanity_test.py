import sys
import numpy as np

# Adjust this path if needed
sys.path.insert(
    0,
    r"D:\Swarm\BTP\Phase B\Phase_B5_Synchronization\v10_IEEE_Final"
)

from swarm_env_step_B5_v20_sensing_ablation import (
    SwarmLidarEnv_v20_SensingAblation
)


def main():
    print("=" * 60)
    print("ORCA ACTION MAPPING SANITY TEST")
    print("=" * 60)

    env = SwarmLidarEnv_v20_SensingAblation(
        width=40.0,
        height=40.0,
        target_density=0.30,
    )

    obs, info = env.reset(seed=42)

    print("\nEnvironment Info")
    print("-" * 40)
    print(f"Goal: {env.goal}")
    print(f"Max Velocity: {env.max_velocity}")
    print(f"dt: {env.dt}")

    # First drone
    idx = 0

    v_before = env.velocities[idx].copy()

    print("\nBefore Step")
    print("-" * 40)
    print("Velocity:", v_before)

    # Apply +1 x acceleration command to every drone
    actions = {}

    for agent in env.agents:
        actions[agent] = np.array([1.0, 0.0], dtype=np.float32)

    env.step(actions)

    v_after = env.velocities[idx].copy()

    print("\nAfter Step")
    print("-" * 40)
    print("Velocity:", v_after)

    delta_v = v_after - v_before

    print("\nVelocity Change")
    print("-" * 40)
    print("Delta:", delta_v)

    expected = np.array([1.0, 0.0])

    error = np.linalg.norm(delta_v - expected)

    print("\nVerification")
    print("-" * 40)
    print("Expected Delta:", expected)
    print("Observed Delta:", delta_v)
    print("L2 Error:", error)

    if error < 1e-3:
        print("\n✅ PASS")
        print("Action [1,0] produces approximately +1 m/s velocity change.")
        print("ORCA mapping:")
        print("action = v_target - v_current")
        print("is VALID.")
    else:
        print("\n❌ FAIL")
        print("Velocity update does not match the assumed dynamics.")
        print("Revisit ORCA action conversion before benchmarking.")

    env.close()


if __name__ == "__main__":
    main()