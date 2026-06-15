import numpy as np
from gym_wrapper import SwarmVecEnv

def main():
    print("Initializing environment...")
    env = SwarmVecEnv(density=0.05, enable_communication=True, seed=42)
    
    print("Resetting environment...")
    obs, infos = env.reset()
    print(f"Initial observations shape: {obs.shape}")
    assert obs.shape == (10, 151), f"Expected shape (10, 151), got {obs.shape}"
    
    print("Stepping environment with random actions...")
    for step_idx in range(100):
        # Sample random actions in [-1, 1] for 10 agents
        actions = np.random.uniform(-1.0, 1.0, size=(10, 2))
        obs, rewards, dones, infos = env.step(actions)
        
        # Check observations shape
        assert obs.shape == (10, 151), f"Step {step_idx}: Expected shape (10, 151), got {obs.shape}"
        
        # Check rewards
        if step_idx % 10 == 0:
            print(f"Step {step_idx:2d} - Mean reward: {np.mean(rewards):.4f}, Min: {np.min(rewards):.4f}, Max: {np.max(rewards):.4f}")
            
    print("Diagnostic run completed successfully! Everything works.")

if __name__ == "__main__":
    main()
