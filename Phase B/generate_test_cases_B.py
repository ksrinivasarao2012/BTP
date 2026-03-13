import json
import os
import numpy as np

# Create the test cases directory if it doesn't exist
os.makedirs("test_cases/basic", exist_ok=True)
os.makedirs("test_cases/edge", exist_ok=True)

# Helper function to convert numpy arrays to lists for JSON serialization
def to_list(arr):
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    elif isinstance(arr, list):
        return [to_list(item) if isinstance(item, (np.ndarray, list)) else item for item in arr]
    return arr

# Helper to generate safely packed clusters
def get_safe_cluster(cx, cy, radius, min_dist=0.26):
    placed = []
    placed.append([cx, cy])
    
    while len(placed) < 10:
        x = np.random.uniform(cx - radius, cx + radius)
        y = np.random.uniform(cy - radius, cy + radius)
        
        safe = True
        for px, py in placed:
            dist = np.sqrt((x - px)**2 + (y - py)**2)
            if dist < min_dist:
                safe = False
                break
                
        if safe:
            placed.append([x, y])
            
    return to_list(placed)

# ==============================================================
# BASIC TEST CASE 1: The Single Pillar
# ==============================================================
basic_1 = {
    "name": "Basic 1 - The Single Pillar",
    "description": "A single massive 1.5m obstacle placed dead-center between spawning zone and goal. Tests basic LiDAR-to-Motor coupling.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(3.0, 3.0, radius=1.0),
            "goal": [17.0, 17.0],
            "obstacles": [(10.0, 10.0, 1.5)]  # Dead center between spawn and goal
        }
    ]
}

# ==============================================================
# BASIC TEST CASE 2: The Asteroid Field (Uniform Scatter)
# ==============================================================
np.random.seed(42)
asteroid_obstacles = []
for _ in range(15):
    x = np.random.uniform(2.0, 18.0)
    y = np.random.uniform(2.0, 18.0)
    r = np.random.uniform(0.6, 1.2)
    # Keep clear of goal zone
    if np.sqrt((x - 17.0)**2 + (y - 17.0)**2) > (r + 2.5):
        asteroid_obstacles.append((round(x, 2), round(y, 2), round(r, 2)))

basic_2 = {
    "name": "Basic 2 - The Asteroid Field",
    "description": "15 medium obstacles scattered uniformly across the map (15% density). Tests general chaotic pathfinding.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(2.0, 2.0, radius=1.0),
            "goal": [17.0, 17.0],
            "obstacles": asteroid_obstacles
        }
    ]
}

# ==============================================================
# BASIC TEST CASE 3: The Narrow Corridor
# ==============================================================
# Create 2 walls of pillars forming a 0.8m wide corridor
corridor_obstacles = []
for y in np.linspace(3.0, 17.0, 12):
    corridor_obstacles.append((9.6, round(y, 2), 0.5))  # Left wall
    corridor_obstacles.append((11.4, round(y, 2), 0.5))  # Right wall (gap = 11.4-0.5 - (9.6+0.5) = 0.8m)

basic_3 = {
    "name": "Basic 3 - The Narrow Corridor",
    "description": "Two parallel obstacle walls form a 0.8m wide corridor. Tests kinematic precision and single-file formation.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(5.0, 10.0, radius=1.5),
            "goal": [15.0, 10.0],
            "obstacles": corridor_obstacles
        }
    ]
}

# ==============================================================
# BASIC TEST CASE 4: The Wall Hugger
# ==============================================================
wall_hugger_obstacles = []
# Obstacles flush against bounding walls
for x in np.linspace(2.0, 18.0, 8):
    wall_hugger_obstacles.append((round(x, 2), 0.6, 0.5))  # Bottom wall
    wall_hugger_obstacles.append((round(x, 2), 19.4, 0.5)) # Top wall
for y in np.linspace(2.0, 18.0, 8):
    wall_hugger_obstacles.append((0.6, round(y, 2), 0.5))   # Left wall
    wall_hugger_obstacles.append((19.4, round(y, 2), 0.5))  # Right wall

basic_4 = {
    "name": "Basic 4 - The Wall Hugger",
    "description": "Obstacles placed flush against all 4 bounding walls. Tests sensor disambiguation between flat walls and circular obstacles.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(5.0, 5.0, radius=1.0),
            "goal": [15.0, 15.0],
            "obstacles": wall_hugger_obstacles
        }
    ]
}


# ==============================================================
# EDGE CASE 1: The Great Concave Trap (U-Shape)
# ==============================================================
u_trap_obstacles = []
# Left arm of the U
for y in np.linspace(6.0, 14.0, 7):
    u_trap_obstacles.append((8.0, round(y, 2), 0.7))
# Bottom of the U
for x in np.linspace(8.0, 14.0, 5):
    u_trap_obstacles.append((round(x, 2), 6.0, 0.7))
# Right arm of the U
for y in np.linspace(6.0, 14.0, 7):
    u_trap_obstacles.append((14.0, round(y, 2), 0.7))
# Opening faces the spawn (top)

edge_1 = {
    "name": "Edge 1 - The Great Concave Trap (U-Shape)",
    "description": "A massive U-shaped wall with the opening facing the spawn. Tests local minima avoidance — greedy AI will fly into the pocket and get stuck.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(11.0, 17.0, radius=1.0),
            "goal": [11.0, 3.0],
            "obstacles": u_trap_obstacles
        }
    ]
}

# ==============================================================
# EDGE CASE 2: The Great Wall (Flank Test)
# ==============================================================
wall_obstacles = []
# Continuous wall from Y=0 to Y=18.5 at X=10, with a single gap at Y=19.0
for y in np.linspace(0.5, 18.0, 18):
    wall_obstacles.append((10.0, round(y, 2), 0.6))

edge_2 = {
    "name": "Edge 2 - The Great Wall (Flank Test)",
    "description": "Continuous obstacle wall across the Y-axis with one 0.6m gap at the extreme top edge. Tests long-term non-linear path planning.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(3.0, 10.0, radius=1.0),
            "goal": [17.0, 10.0],
            "obstacles": wall_obstacles
        }
    ]
}

# ==============================================================
# EDGE CASE 3: The Micro-Minefield (LiDAR Sweep Test)
# ==============================================================
np.random.seed(99)
micro_obstacles = []
for _ in range(50):
    x = np.random.uniform(1.5, 18.5)
    y = np.random.uniform(1.5, 18.5)
    r = np.random.uniform(0.15, 0.3)
    # Keep clear of goal zone
    if np.sqrt((x - 17.0)**2 + (y - 17.0)**2) > 2.5:
        micro_obstacles.append((round(x, 2), round(y, 2), round(r, 2)))

edge_3 = {
    "name": "Edge 3 - The Micro-Minefield",
    "description": "50+ tiny 0.2m obstacles scattered across the map. Explicitly tests the Ray-Sweeping LiDAR fix — standard 16-ray will miss these.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(2.0, 2.0, radius=1.0),
            "goal": [17.0, 17.0],
            "obstacles": micro_obstacles
        }
    ]
}

# ==============================================================
# EDGE CASE 4: The Claustrophobic Prison
# ==============================================================
prison_obstacles = []
# Tight arc of boulders surrounding the bottom-left corner
for angle in np.linspace(0, np.pi/2, 6):
    ox = 2.0 + 2.5 * np.cos(angle)
    oy = 2.0 + 2.5 * np.sin(angle)
    prison_obstacles.append((round(ox, 2), round(oy, 2), 1.0))

edge_4 = {
    "name": "Edge 4 - The Claustrophobic Prison",
    "description": "10 drones spawn tightly in the corner, surrounded by 1.0m boulders with a single exit. Tests Cluster Panic + Static Geometry combined.",
    "episodes": 1,
    "scenarios": [
        {
            "start_positions": get_safe_cluster(1.5, 1.5, radius=0.6, min_dist=0.26),
            "goal": [17.0, 17.0],
            "obstacles": prison_obstacles
        }
    ]
}

# ==============================================================
# SAVE ALL TEST CASES
# ==============================================================
with open("test_cases/basic/basic_1_single_pillar.json", "w") as f:
    json.dump(basic_1, f, indent=4)
    
with open("test_cases/basic/basic_2_asteroid_field.json", "w") as f:
    json.dump(basic_2, f, indent=4)
    
with open("test_cases/basic/basic_3_narrow_corridor.json", "w") as f:
    json.dump(basic_3, f, indent=4)
    
with open("test_cases/basic/basic_4_wall_hugger.json", "w") as f:
    json.dump(basic_4, f, indent=4)

with open("test_cases/edge/edge_1_u_shape_trap.json", "w") as f:
    json.dump(edge_1, f, indent=4)
    
with open("test_cases/edge/edge_2_flank_wall.json", "w") as f:
    json.dump(edge_2, f, indent=4)
    
with open("test_cases/edge/edge_3_micro_minefield.json", "w") as f:
    json.dump(edge_3, f, indent=4)
    
with open("test_cases/edge/edge_4_claustrophobic_prison.json", "w") as f:
    json.dump(edge_4, f, indent=4)

print("✅ Saved 4 Basic + 4 Edge Test Case JSON files for Phase B into `test_cases/`")
