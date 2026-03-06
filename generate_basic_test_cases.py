import json
import os
import numpy as np

# Create the test cases directory if it doesn't exist
os.makedirs("test_cases/basic", exist_ok=True)

# Helper function to convert numpy arrays to lists for JSON serialization
def to_list(arr):
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    elif isinstance(arr, list):
        return [to_list(item) if isinstance(item, (np.ndarray, list)) else item for item in arr]
    return arr

# ==============================================================
# EDGE CASE 1: Instant Win (Spawning precisely on the goal)
# ==============================================================
edge_case_1 = {
    "name": "Edge Case 1 - Instant Win",
    "description": "Drones spawn directly inside the goal radius to test success logic.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": to_list([[17.5 + np.random.uniform(-0.1, 0.1), 17.5 + np.random.uniform(-0.1, 0.1)] for _ in range(10)]),
            "goal": [18.0, 18.0]
        }
    ]
}

# ==============================================================
# EDGE CASE 2: Maximum Distance Journey (Cross-map traversal)
# ==============================================================
edge_case_2 = {
    "name": "Edge Case 2 - Maximum Distance Journey",
    "description": "Drones spawn in the extreme bottom-left, goal in extreme top-right.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": to_list([[1.0 + np.random.uniform(-0.5, 0.5), 1.0 + np.random.uniform(-0.5, 0.5)] for _ in range(10)]),
            "goal": [19.0, 19.0]
        }
    ]
}

# ==============================================================
# EDGE CASE 3: Complete Random Scatter
# ==============================================================
edge_case_3 = {
    "name": "Edge Case 3 - Complete Random Scatter",
    "description": "Drones are scattered completely randomly across the entire map, looking for a center goal.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": to_list([[np.random.uniform(1.0, 19.0), np.random.uniform(1.0, 19.0)] for _ in range(10)]),
            "goal": [10.0, 10.0]
        }
    ]
}

# ==============================================================
# EDGE CASE 4: Extreme Claustrophobia (High collision risk)
# ==============================================================
edge_case_4 = {
    "name": "Edge Case 4 - Extreme Claustrophobia",
    "description": "Drones spawn nearly touching each other and must separate to reach the goal without crashing.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": to_list([[10.0 + np.random.uniform(-0.1, 0.1), 10.0 + np.random.uniform(-0.1, 0.1)] for _ in range(10)]),
            "goal": [2.0, 18.0]
        }
    ]
}

# ==============================================================
# EDGE CASE 5: The Wall Hugging Test
# ==============================================================
edge_case_5 = {
    "name": "Edge Case 5 - The Wall Hugging Test",
    "description": "Drones literally spawn touching the X=0.1 boundary wall and must fly to the opposite wall.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": to_list([[0.1, y] for y in np.linspace(1.0, 19.0, 10)]),
            "goal": [19.0, 10.0]
        }
    ]
}

# Save all edge cases to JSON files
with open("test_cases/basic/edge_case_1_instant_win.json", "w") as f:
    json.dump(edge_case_1, f, indent=4)
    
with open("test_cases/basic/edge_case_2_max_distance.json", "w") as f:
    json.dump(edge_case_2, f, indent=4)
    
with open("test_cases/basic/edge_case_3_random_scatter.json", "w") as f:
    json.dump(edge_case_3, f, indent=4)
    
with open("test_cases/basic/edge_case_4_claustrophobia.json", "w") as f:
    json.dump(edge_case_4, f, indent=4)
    
with open("test_cases/basic/edge_case_5_wall_hugging.json", "w") as f:
    json.dump(edge_case_5, f, indent=4)

print("✅ Saved 5 Basic Edge Case JSON files into `test_cases/basic/`")
