import os

with open("evaluate_v15_IEEE_Final.py", "r", encoding="utf-8") as f:
    eval_code = f.read()

eval_code = eval_code.replace("v15", "v16")
eval_code = eval_code.replace("V15", "V16")
eval_code = eval_code.replace("SwarmLidarEnv_v15_Final", "SwarmLidarEnv_v16_Final")
eval_code = eval_code.replace("MAPPO_Policy_v15", "MAPPO_Policy_v16")
eval_code = eval_code.replace("swarm_env_step_B5_v15_master", "swarm_env_step_B5_v16_master")
eval_code = eval_code.replace("train_step_B5_sync_v15_v4", "train_step_B5_sync_v16_master")

with open("evaluate_v16_IEEE_Final.py", "w", encoding="utf-8") as f:
    f.write(eval_code)

print("Evaluation script created successfully.")
