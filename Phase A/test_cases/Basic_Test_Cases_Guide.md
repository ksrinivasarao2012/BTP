# Basic Test Cases Guide

This document explains the 5 fundamental test scenarios found in `test_cases/basic/`. These scripts are "basic" edge cases because they isolate and test specific extremes of the physics boundaries and the reward function, making sure there are no obvious blind spots in the neural network's navigation logic.

## 🛠️ How to Visualize Test Cases
You can watch the AI solve any single test case visually in real-time. Run the evaluation suite from the `Phase A` folder and pass the name of the JSON file you want to watch.

```bash
# General Command Format
python test_suite_step_A.py <filename.json>

# Specific Examples
python test_suite_step_A.py edge_case_1.json
python test_suite_step_A.py edge_case_4.json
```

---

## 🗂️ The Scenarios

### 1. `edge_case_1.json` (Instant Win)
- **Why it is a basic case:** Tests the termination logic.
- **Description:** All 10 drones spawn directly on top of the goal.
- **Purpose:** Verifies that the environment instantly triggers `terminated=True` on frame 1, granting the success rewards without allowing the drones to sit there and accumulate existential penalties or slowly drift into each other.

### 2. `edge_case_2.json` (Maximum Distance Journey)
- **Why it is a basic case:** Tests long-haul velocity maintenance.
- **Description:** Drones spawn in the extreme bottom-left corner (`1.0, 1.0`), while the goal is placed at the extreme top-right corner (`19.0, 19.0`).
- **Purpose:** Forces the drones to travel the maximum possible diagonal distance across the map. It ensures the policy doesn't time out or drift off-course over long distances, confirming the $R_{goal}$ potential field provides a steady gradient.

### 3. `edge_case_3.json` (Complete Random Scatter)
- **Why it is a basic case:** Tests uncoordinated, asymmetric pathing.
- **Description:** Drones are scattered completely randomly across the entire map, looking for a center goal (`10.0, 10.0`).
- **Purpose:** This simulates the average "messy" scenario. Because drones approach from all 360 degrees simultaneously, it tests the goal-funneling logic and ensures drones arriving from the North don't fatally crash head-on into drones arriving from the South.

### 4. `edge_case_4.json` (Extreme Claustrophobia)
- **Why it is a basic case:** Tests the *Social Distancing* and *School Zone* constraints.
- **Description:** All 10 drones spawn densely packed, practically touching each other, and must fly to a goal on the other side of the map.
- **Purpose:** This explicitly triggers the panic conditions that originally broke the Step A model. It verifies that the AI correctly throttles its speed and pushes away from its neighbors upon spawning, untangling itself safely before heading to the objective.

### 5. `edge_case_5.json` (The Wall Hugging Test)
- **Why it is a basic case:** Tests the $R_{safe}$ boundary penalty logic.
- **Description:** Drones literally spawn touching the $X=0.1$ physical boundary wall limit and must fly parallel/away from it.
- **Purpose:** If a drone steps outside the 20x20 boundary, it receives a `-100` penalty and dies. This edge case ensures that drones don't aggressively swing out of bounds to avoid their neighbors when forced into a tight corner.
