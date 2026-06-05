import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
torch.set_num_threads(1)
import torch.nn as nn
import numpy as np
import sys
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3.common.callbacks import BaseCallback

# Make sure we can import local modules
sys.path.append(os.path.dirname(__file__))
from train_step_B5_sync_v15_master import MultiProcessEnv_v15, MAPPO_Policy_v15, MAPPO_Extractor_v15

class RecoveryCurriculumCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self._last_r_comm = -1.0
        self._last_density = -1.0
        
    def _on_step(self) -> bool:
        ts = self.num_timesteps
        # During recovery, we lock the environment to the target dense obstacle environment:
        r_comm, r_sensor = 10.0, 8.0
        density = 0.35  # Train directly on the target evaluation density!
        
        if abs(r_comm - self._last_r_comm) > 1e-4 or abs(density - self._last_density) > 1e-4:
            self.training_env.env_method("set_curriculum", r_sensor, r_comm)
            self.training_env.env_method("set_target_density", density)
            self._last_r_comm = r_comm
            self._last_density = density
            
        if ts % 100000 == 0:
            print(f"⏱️ [Recovery] Step {ts}: R_comm={r_comm:.1f}m, R_sensor={r_sensor:.1f}m, Density={density:.2f}")
            # Also log log_std to monitor that it doesn't drift!
            if hasattr(self.model.policy, "log_std"):
                log_std = self.model.policy.log_std.data.cpu().numpy()
                std = np.exp(log_std)
                print(f"📊 [Recovery] Action log_std: {log_std}, std: {std}")
        return True

    def _on_rollout_end(self) -> None:
        # Save intermediate checkpoints to allow early evaluation
        iter_num = self.num_timesteps // 204800
        print(f"\n💾 [Recovery] Rollout completed (Iteration {iter_num}, Step {self.num_timesteps})", flush=True)
        
        final_model_path = r"d:\Swarm\BTP\models\v15_Master_Recovered_Final.zip"
        final_norm_path = r"d:\Swarm\BTP\models\v15_Master_Recovered_Normalize.pkl"
        
        # Save numbered checkpoints for safety
        numbered_model_path = f"d:\\Swarm\\BTP\\models\\v15_Master_Recovered_{iter_num}iter.zip"
        numbered_norm_path = f"d:\\Swarm\\BTP\\models\\v15_Master_Recovered_{iter_num}iter_Normalize.pkl"
        
        print(f"💾 Saving model checkpoint to: {final_model_path} and {numbered_model_path}", flush=True)
        self.model.save(final_model_path)
        self.model.save(numbered_model_path)
        
        print(f"💾 Saving normalizer checkpoint to: {final_norm_path} and {numbered_norm_path}", flush=True)
        self.training_env.save(final_norm_path)
        self.training_env.save(numbered_norm_path)

def run_recovery_training():
    num_cpu = 10
    print("\n🚀 [V15-Recovery] Initializing Vectorized Environment (10 workers, 100 parallel drones)...")
    base_env = MultiProcessEnv_v15(n_workers=num_cpu)
    
    # Load reward normalization parameters from the 50M run to preserve training scale
    norm_path = r"d:\Swarm\BTP\models\v15_Master_Normalize.pkl"
    print(f"📦 Loading reward normalization parameters from: {norm_path}")
    env = VecNormalize.load(norm_path, base_env)
    
    # Ensure norm settings are correct
    env.training = True
    env.norm_obs = False
    env.norm_reward = True
    
    model_base_path = r"d:\Swarm\BTP\models\v15_Master_Repaired_Base.zip"
    print(f"🔄 Loading repaired base model from: {model_base_path}")
    
    # Load repaired model and override hyperparameters for fine-tuning
    model = PPO.load(
        model_base_path,
        env=env,
        custom_objects={
            "policy_class": MAPPO_Policy_v15
        },
        learning_rate=1e-4,     # Smaller learning rate for fine-tuning stability
        ent_coef=0.001,         # Tiny entropy coefficient to prevent standard deviation divergence
        tensorboard_log="./logs/v15_Recovery/"
    )
    
    # Verify the loaded parameters
    if hasattr(model.policy, "log_std"):
        print(f"🎯 Initial log_std parameter: {model.policy.log_std.data}")
        print(f"🎯 Initial Action standard deviation: {torch.exp(model.policy.log_std).data}")
        
    print("\n🥇 [V15-Recovery] Launching Policy Recovery Fine-Tuning (600K steps)...")
    curriculum = RecoveryCurriculumCallback()
    
    # Run 614,400 steps of fine-tuning (3 iterations)
    model.learn(total_timesteps=614_400, callback=[curriculum], progress_bar=False)
    
    # Save the recovered model and normalization params
    final_model_path = r"d:\Swarm\BTP\models\v15_Master_Recovered_Final.zip"
    final_norm_path = r"d:\Swarm\BTP\models\v15_Master_Recovered_Normalize.pkl"
    
    print(f"\n💾 Saving recovered final model to: {final_model_path}")
    model.save(final_model_path)
    
    print(f"💾 Saving recovered normalizer to: {final_norm_path}")
    env.save(final_norm_path)
    
    env.close()
    print("✅ Policy recovery fine-tuning complete and saved!")

if __name__ == "__main__":
    run_recovery_training()
