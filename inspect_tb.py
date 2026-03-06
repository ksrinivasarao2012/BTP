import os
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

def inspect_keys(log_dir):
    event_acc = EventAccumulator(log_dir)
    event_acc.Reload()
    print(f"\nKeys found in {log_dir}:")
    print(event_acc.Tags()['scalars'])

base_dir = "./ppo_swarm_tensorboard_experiments"
first_exp = os.path.join(base_dir, os.listdir(base_dir)[0])
inspect_keys(first_exp)
