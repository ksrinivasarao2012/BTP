import os
import time
import multiprocessing
import torch
import numpy as np
from stable_baselines3 import PPO
from gym_wrapper import SwarmVecEnv
from networks import MAPPOPolicy

def benchmark_config(num_threads):
    # Set thread limits BEFORE import/initialization where possible, but we apply it dynamically
    os.environ["OMP_NUM_THREADS"] = str(num_threads)
    os.environ["MKL_NUM_THREADS"] = str(num_threads)
    torch.set_num_threads(num_threads)
    
    # Re-verify torch threads
    actual_threads = torch.get_num_threads()
    
    # Create env
    env = SwarmVecEnv(density=0.05, enable_communication=True, seed=42)
    
    # Initialize PPO model
    model = PPO(
        policy=MAPPOPolicy,
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=4,
        gamma=0.99,
        device="cpu"
    )
    
    # Warmup steps
    print(f"  Warmup for core count {num_threads}...")
    model.learn(total_timesteps=1000)
    
    # Benchmark run (5000 steps)
    steps_to_run = 5000
    start_time = time.time()
    model.learn(total_timesteps=steps_to_run)
    elapsed = time.time() - start_time
    
    sps = steps_to_run / elapsed
    projected_hours = (3_000_000 / sps) / 3600.0
    
    env.close()
    return sps, projected_hours

def main():
    max_cores = multiprocessing.cpu_count()
    print(f"System detected with {max_cores} logical CPU cores.")
    
    # We will test a range of core counts
    test_configs = [2, 4]
    if max_cores >= 8:
        test_configs.append(8)
    if max_cores >= 12:
        test_configs.append(12)
    if max_cores not in test_configs:
        test_configs.append(max_cores)
        
    test_configs = sorted(list(set(test_configs)))
    
    results = {}
    print("\nStarting benchmark of different core configurations...")
    for cores in test_configs:
        print(f"\nBenchmarking with {cores} cores...")
        try:
            sps, proj_hours = benchmark_config(cores)
            results[cores] = (sps, proj_hours)
            print(f"  Result: {sps:.1f} steps/second | Projected 3M time: {proj_hours:.2f} hours")
        except Exception as e:
            print(f"  Failed for configuration {cores}: {e}")
            
    # Write report
    report_path = "core_benchmark_results.txt"
    with open(report_path, "w") as f:
        f.write("="*60 + "\n")
        f.write("         CPU CORES PERFORMANCE BENCHMARK (3M STEPS)\n")
        f.write("="*60 + "\n")
        f.write(f"{'Cores':<10}{'Steps/Sec (SPS)':<20}{'Projected Time (3M)':<20}\n")
        f.write("-"*60 + "\n")
        for cores, (sps, proj_hours) in results.items():
            h = int(proj_hours)
            m = int((proj_hours - h) * 60)
            f.write(f"{cores:<10}{sps:<20.1f}{h}h {m}m\n")
        f.write("="*60 + "\n")
        
    print(f"\n[OK] Benchmark complete! Results written to {report_path}")

if __name__ == "__main__":
    main()
