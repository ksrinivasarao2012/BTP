from stable_baselines3 import PPO
from swarm_env_vanilla import SwarmLidarEnv_Vanilla
import supersuit as ss
import os

def train():
    env = SwarmLidarEnv_Vanilla()
    # Wrap for SB3 compatibility
    env = ss.black_death_v3(env)
    env = ss.pettingzoo_env_to_vec_env_v1(env)
    env = ss.concat_vec_envs_v1(env, 1, num_cpus=1, base_class='stable_baselines3')

    # Use the same hyperparameters as Exp_1 for a fair comparison
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=3e-4, n_steps=2048, batch_size=256, n_epochs=10, gamma=0.995)
    
    print("Training Vanilla Model (1M steps)...")
    model.learn(total_timesteps=1_000_000)
    
    os.makedirs("Vanilla_Model", exist_ok=True)
    model.save("Vanilla_Model/vanilla_fixed_physics_model")
    print("Vanilla Model Saved!")

if __name__ == "__main__":
    train()
