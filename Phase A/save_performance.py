import csv
import os
import datetime

def save_results(script_name, num_episodes, success_count, crash_obs, crash_wall, timeouts):
    filename = "performance_results.csv"
    file_exists = os.path.isfile(filename)
    
    success_rate = (success_count / num_episodes) * 100
    crash_obs_rate = (crash_obs / num_episodes) * 100
    crash_wall_rate = (crash_wall / num_episodes) * 100
    timeout_rate = (timeouts / num_episodes) * 100
    
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Write header if file is new
        if not file_exists:
            writer.writerow(["Timestamp", "Script", "Episodes", "Success Rate (%)", "Crash Obstacle (%)", "Crash Wall (%)", "Timeout (%)"])
            
        writer.writerow([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            script_name,
            num_episodes,
            f"{success_rate:.2f}",
            f"{crash_obs_rate:.2f}",
            f"{crash_wall_rate:.2f}",
            f"{timeout_rate:.2f}"
        ])
    
    print(f"\n📊 Results saved to {filename}")
