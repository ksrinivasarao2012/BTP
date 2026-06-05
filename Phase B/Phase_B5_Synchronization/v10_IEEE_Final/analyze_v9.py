import csv
import glob
import math
import os

results_dir = r"d:\Swarm\BTP\Phase B\Phase_B5_Synchronization\v10_IEEE_Final\results\v8\apex_ultra_sync_v9_final"
csv_files = glob.glob(os.path.join(results_dir, "**", "*.csv"), recursive=True)

collision_distances_to_obs = []
collision_distances_to_drones = []
collision_steps = []
timeout_distances_to_goal = []

print(f"Analyzing {len(csv_files)} trajectory logs...")

for f in csv_files:
    try:
        with open(f, 'r') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if not rows: continue
            
            # Group by agent
            agent_data = {}
            for row in rows:
                agent = row['Agent']
                if agent not in agent_data:
                    agent_data[agent] = []
                agent_data[agent].append(row)
            
            last_steps = {}
            for agent, data in agent_data.items():
                last_steps[agent] = data[-1]
                
            first_agent = list(last_steps.keys())[0]
            goal_x, goal_y = float(last_steps[first_agent]['Goal_X']), float(last_steps[first_agent]['Goal_Y'])
            obs_str = last_steps[first_agent]['Obstacles']
            obstacles = []
            if isinstance(obs_str, str) and obs_str.strip():
                for o in obs_str.split(';'):
                    try:
                        ox, oy, orad = map(float, o.split(','))
                        obstacles.append((ox, oy, orad))
                    except: pass
                    
            for agent, row in last_steps.items():
                step = int(row['Step'])
                x, y = float(row['X']), float(row['Y'])
                dist_to_goal = math.sqrt((x - goal_x)**2 + (y - goal_y)**2)
                
                if step < 798 and dist_to_goal > 1.0:
                    collision_steps.append(step)
                    
                    min_obs_dist = 999.0
                    for ox, oy, orad in obstacles:
                        d = math.sqrt((x - ox)**2 + (y - oy)**2) - orad
                        if d < min_obs_dist: min_obs_dist = d
                    collision_distances_to_obs.append(min_obs_dist)
                    
                    # Find other drones at this step
                    min_drone_dist = 999.0
                    for other_agent, other_data in agent_data.items():
                        if other_agent != agent:
                            # find the row for other_agent at the same step
                            for r in reversed(other_data):
                                if int(r['Step']) == step:
                                    d = math.sqrt((x - float(r['X']))**2 + (y - float(r['Y']))**2)
                                    if d < min_drone_dist: min_drone_dist = d
                                    break
                    collision_distances_to_drones.append(min_drone_dist)
                    
                elif step >= 798:
                    timeout_distances_to_goal.append(dist_to_goal)
                    
    except Exception as e:
        pass

print(f"Total Collisions Detected in Analysis: {len(collision_steps)}")
if collision_steps:
    print(f"Average Step of Collision: {sum(collision_steps)/len(collision_steps):.1f}")
if collision_distances_to_obs:
    print(f"Average Distance to Nearest Obstacle at Collision: {sum(collision_distances_to_obs)/len(collision_distances_to_obs):.3f}m")
    print(f"Collisions primarily caused by obstacles (< 0.2m): {sum(1 for d in collision_distances_to_obs if d < 0.2)} / {len(collision_distances_to_obs)}")
if collision_distances_to_drones:
    print(f"Average Distance to Nearest Drone at Collision: {sum(collision_distances_to_drones)/len(collision_distances_to_drones):.3f}m")
    print(f"Collisions primarily caused by drone-drone crash (< 0.35m): {sum(1 for d in collision_distances_to_drones if d < 0.35)} / {len(collision_distances_to_drones)}")

print(f"\nTotal Timeouts Detected in Analysis: {len(timeout_distances_to_goal)}")
if timeout_distances_to_goal:
    print(f"Average Distance to Goal at Timeout: {sum(timeout_distances_to_goal)/len(timeout_distances_to_goal):.3f}m")

