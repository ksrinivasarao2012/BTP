import os
import torch
import sys
from stable_baselines3 import PPO

# Make sure we can import local modules
sys.path.append(os.path.dirname(__file__))
from train_step_B5_sync_v15_master import MAPPO_Policy_v15, MAPPO_Extractor_v15

def perform_surgery():
    model_path = r"d:\Swarm\BTP\models\v15_Master_Final_50M.zip"
    repaired_path = r"d:\Swarm\BTP\models\v15_Master_Repaired_Base.zip"
    
    print(f"🤖 Loading v15 master model from: {model_path}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_v15})
    
    print("\n🔍 Parameter state BEFORE surgery:")
    if hasattr(model.policy, "log_std"):
        log_std = model.policy.log_std
        print(f"   log_std parameter: {log_std.data}")
        print(f"   Corresponding std: {torch.exp(log_std).data}")
    else:
        print("   Warning: model.policy does not have direct 'log_std' attribute!")
        return
        
    print("\n🔧 Executing Model Surgery...")
    with torch.no_grad():
        # Set standard deviation to ~0.15 (log(0.15) ≈ -1.9)
        model.policy.log_std.fill_(-1.9)
        
    print("\n🔍 Parameter state AFTER surgery:")
    print(f"   log_std parameter: {model.policy.log_std.data}")
    print(f"   Corresponding std: {torch.exp(model.policy.log_std).data}")
    
    print(f"\n💾 Saving surgically repaired model to: {repaired_path}")
    model.save(repaired_path)
    print("✅ Model surgery successfully completed and serialized!")

if __name__ == "__main__":
    perform_surgery()
