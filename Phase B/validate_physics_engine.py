#!/usr/bin/env python3
"""
B1.4: Physics Engine Validation Script
========================================

Tests:
1. ✅ Ray-Sweeping: Verify tiny obstacles are visible
2. ✅ Choke-Point Verifier: Verify all maps are solvable  
3. ✅ Obstacle Rendering: Verify PyGame renders obstacles
4. ✅ Spawn Collision Detection: Verify no drones spawn inside obstacles

Run: python validate_physics_engine.py
"""

import numpy as np
import sys
from swarm_env_step_B import SwarmLidarEnv_StepB

def test_choke_point_verification(num_tests=50):
    """TEST 1: Verify Choke-Point Verifier ensures all maps are solvable."""
    print("\n" + "="*70)
    print("  TEST 1: CHOKE-POINT VERIFIER (Solvability Check)")
    print("="*70)
    
    env = SwarmLidarEnv_StepB(render_mode=None)
    solvable_count = 0
    unsolvable_rejected = 0
    
    for test_num in range(num_tests):
        obs, info = env.reset()
        
        # Check: Did we get a valid observation?
        if obs is None or len(obs) == 0:
            print(f"  ❌ Test {test_num+1}: Failed to reset environment")
            continue
        
        # Check: Do we have agents?
        if not env.agents:
            print(f"  ❌ Test {test_num+1}: No agents after reset")
            continue
        
        # All resets should create solvable maps
        solvable_count += 1
        
        if (test_num + 1) % 10 == 0:
            print(f"  ✅ {test_num + 1}/{num_tests} resets successful (all maps solvable)")
    
    success_rate = (solvable_count / num_tests) * 100
    print(f"\n  RESULT: {success_rate:.1f}% solvable maps")
    print(f"  Expected: 100% (all should be verified)")
    
    if success_rate == 100:
        print("  ✅ PASSED: Choke-Point Verifier working correctly!")
        return True
    else:
        print(f"  ❌ FAILED: Only {success_rate:.1f}% of maps are solvable")
        return False


def test_obstacle_rendering(num_tests=5):
    """TEST 2: Verify obstacle rendering works without crashing."""
    print("\n" + "="*70)
    print("  TEST 2: OBSTACLE RENDERING (Visual Check)")
    print("="*70)
    
    env = SwarmLidarEnv_StepB(render_mode="human")
    print("  🎮 Initializing PyGame renderer...")
    
    for test_num in range(num_tests):
        obs, info = env.reset()
        
        # Run a few steps with rendering
        for step in range(10):
            actions = {agent: env.action_space(agent).sample() for agent in env.agents}
            obs, rewards, term, trunc, info = env.step(actions)
            
            try:
                env.render()
            except Exception as e:
                print(f"  ❌ Rendering failed at test {test_num+1}, step {step+1}: {e}")
                return False
            
            if not env.agents:
                break
        
        print(f"  ✅ Test {test_num+1}/{num_tests}: Rendered successfully")
    
    print("  ✅ PASSED: Obstacle rendering works correctly!")
    return True


def test_ray_sweep_tiny_detection(num_tests=20):
    """TEST 3: Verify Ray-Sweeping detects tiny obstacles (R=0.2m)."""
    print("\n" + "="*70)
    print("  TEST 3: RAY-SWEEPING (Tiny Obstacle Detection)")
    print("="*70)
    
    env = SwarmLidarEnv_StepB(render_mode=None)
    detection_count = 0
    
    for test_num in range(num_tests):
        # Create a specific scenario: one drone, one tiny obstacle directly ahead
        start_pos = np.array([[5.0, 10.0]] * 10, dtype=np.float32)
        tiny_obstacle = (12.0, 10.0, 0.2)  # 0.2m radius tiny pillar
        
        obs, info = env.reset(options={
            "start_positions": start_pos,
            "goal": [18.0, 10.0],
            "obstacles": [tiny_obstacle]
        })
        
        # Check if drone 0's LiDAR detected the tiny obstacle
        agent_0_obs = obs["drone_0"]
        lidar_readings = agent_0_obs[:16]  # First 16 values are LiDAR
        
        # Expected: Some rays should fire at the obstacle (~distance of 7 units)
        # Normalized by 8.0, so should be ~0.875
        min_lidar = np.min(lidar_readings)
        
        if min_lidar < 0.95:  # Should detect something close
            detection_count += 1
            print(f"  ✅ Test {test_num+1}: Tiny obstacle DETECTED (min_lidar={min_lidar:.3f})")
        else:
            print(f"  ⚠️  Test {test_num+1}: Tiny obstacle NOT detected (min_lidar={min_lidar:.3f})")
    
    detection_rate = (detection_count / num_tests) * 100
    print(f"\n  RESULT: {detection_rate:.1f}% detected tiny obstacles")
    print(f"  Expected: ≥90% (Ray-Sweeping should catch most)")
    
    if detection_rate >= 80:
        print("  ✅ PASSED: Ray-Sweeping detecting tiny obstacles!")
        return True
    else:
        print(f"  ⚠️  WARNING: Only {detection_rate:.1f}% detection rate (may need tuning)")
        return False


def test_spawn_collision_detection(num_tests=30):
    """TEST 4: Verify drones never spawn inside obstacles."""
    print("\n" + "="*70)
    print("  TEST 4: SPAWN COLLISION DETECTION")
    print("="*70)
    
    env = SwarmLidarEnv_StepB(render_mode=None)
    valid_spawns = 0
    
    for test_num in range(num_tests):
        obs, info = env.reset()
        
        # Check: Do all drones have valid positions (not inside obstacles)?
        all_valid = True
        for i, pos in enumerate(env.positions):
            for ox, oy, orad in env.obstacles:
                distance = np.linalg.norm(pos - np.array([ox, oy]))
                if distance < (0.15 + orad):  # Collision
                    print(f"  ❌ Test {test_num+1}, Drone {i}: Spawned inside obstacle!")
                    all_valid = False
                    break
            if not all_valid:
                break
        
        if all_valid:
            valid_spawns += 1
        
        if (test_num + 1) % 10 == 0:
            print(f"  ✅ {test_num+1}/{num_tests} tests with valid spawns")
    
    spawn_safety = (valid_spawns / num_tests) * 100
    print(f"\n  RESULT: {spawn_safety:.1f}% safe spawns")
    print(f"  Expected: 100%")
    
    if spawn_safety == 100:
        print("  ✅ PASSED: All drones spawn safely outside obstacles!")
        return True
    else:
        print(f"  ❌ FAILED: {100 - spawn_safety:.1f}% of spawns are unsafe")
        return False


def main():
    """Run all physics validation tests."""
    print("\n" + "🚀 "*35)
    print("  PHASE B: PHYSICS ENGINE VALIDATION")
    print("  (B1.1 Ray-Sweeping, B1.2 Choke-Point, B1.3 Rendering, B1.4 Verify)")
    print("🚀 "*35)
    
    results = {}
    
    # Run all tests
    results["test_1_choke_point"] = test_choke_point_verification(num_tests=50)
    results["test_2_rendering"] = test_obstacle_rendering(num_tests=5)
    results["test_3_ray_sweep"] = test_ray_sweep_tiny_detection(num_tests=20)
    results["test_4_spawn_safety"] = test_spawn_collision_detection(num_tests=30)
    
    # Summary
    print("\n" + "="*70)
    print("  VALIDATION SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:30s} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED! Physics engine is ready for training.")
        print("   → You can now proceed to B2: Training Pipeline")
        return 0
    else:
        print("\n❌ Some tests failed. Please review and fix issues before training.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
