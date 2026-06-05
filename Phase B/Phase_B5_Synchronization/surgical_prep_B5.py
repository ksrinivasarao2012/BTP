import os
import torch
import numpy as np
import zipfile
import io
from stable_baselines3 import PPO
from swarm_env_step_B5 import SwarmLidarEnv_StepB5
from train_step_B5_sync import MAPPO_Policy_B5, MultiProcessPZEnv_B5, VecNormalize

def perform_surgery():
    # Setup directories
    os.makedirs("./models", exist_ok=True)
    
    # Paths
    base_model_path = "../../models/v15_Master_Recovered_Final.zip"
    if not os.path.exists(base_model_path):
        base_model_path = "./models/apex_ultra_glide_v14_final.zip"
        
    if not os.path.exists(base_model_path):
        print(f"Error: Base reactive model not found at {base_model_path}!")
        return False
        
    output_model_path = "./models/stigmergy_step_B5_sync_base"
    
    print(f"Loading environment to initialize observation spaces (132 local + 520 global)...")
    base_env = MultiProcessPZEnv_B5(n_workers=1, density=0.35)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    
    policy_kwargs = dict(net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128]), activation_fn=torch.nn.ReLU)
    
    print("Initializing target Stigmergy model...")
    model = PPO(MAPPO_Policy_B5, env, learning_rate=2e-5, n_steps=2048, batch_size=256, ent_coef=0.01, gamma=0.99, policy_kwargs=policy_kwargs, verbose=0)
    
    print(f"Performing weight surgery on {base_model_path} (adapting 130 -> 132 dims)...")
    with zipfile.ZipFile(base_model_path, "r") as zip_f:
        with zip_f.open("policy.pth") as pth_f:
            old_params = torch.load(io.BytesIO(pth_f.read()), map_location="cpu", weights_only=True)
            
    new_state = model.policy.state_dict()
    for k, v in old_params.items():
        if k == "mlp_extractor.policy_net.0.weight":
            # Expand first layer weights from (256, 130) to (256, 132)
            nv = torch.zeros((256, 132))
            nv[:, :130] = v
            new_state[k] = nv
            print("Successfully expanded Actor input layer mapping tensor (130 -> 132).")
        elif k in new_state and new_state[k].shape == v.shape:
            new_state[k] = v
            
    model.policy.load_state_dict(new_state)
    
    # Save the surgically adapted base model
    model.save(output_model_path)
    env.close()
    print(f"Success! Surgically adapted Stigmergy base model saved to {output_model_path}.zip")
    return True

if __name__ == "__main__":
    perform_surgery()
