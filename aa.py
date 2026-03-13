import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def draw_circle(ax, x, y, radius, color, label, fill=True, alpha=1.0):
    circle = patches.Circle((x, y), radius, linewidth=2, edgecolor=color, facecolor=color if fill else 'none', alpha=alpha, label=label)
    ax.add_patch(circle)

def setup_plot(ax, title):
    ax.set_xlim(-1, 8)
    ax.set_ylim(-2, 2)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.axhline(0, color='black', linewidth=0.5)

# --- Scene Setup ---
drone_x, drone_y = 0.0, 0.0
drone_radius = 0.5

# We place the obstacle slightly off-center. 
# It is high enough that the center laser misses it, 
# but low enough that the drone's physical body will crash into it.
obs_x, obs_y = 5.0, 0.6  
obs_radius = 0.4

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

# ==========================================
# 1. Standard Raycasting (The Problem)
# ==========================================
setup_plot(ax1, "1. Standard Ray (Misses & Crashes)")
draw_circle(ax1, drone_x, drone_y, drone_radius, 'blue', 'Drone Body', alpha=0.3)
draw_circle(ax1, obs_x, obs_y, obs_radius, 'red', 'Obstacle')

# Draw a thin ray straight ahead
ax1.plot([drone_x, 8], [drone_y, drone_y], color='green', linewidth=2, label='Thin Laser Ray')

# Highlight the problem
ax1.text(2, -1.5, "Ray misses obstacle.\nDrone flies forward and crashes!", color='red', fontsize=10, ha='center')
ax1.legend(loc="upper left")

# ==========================================
# 2. Ray Sweeping (The Concept)
# ==========================================
setup_plot(ax2, "2. Ray Sweeping (The Safe Capsule)")
draw_circle(ax2, drone_x, drone_y, drone_radius, 'blue', 'Drone Body', alpha=0.3)
draw_circle(ax2, obs_x, obs_y, obs_radius, 'red', 'Obstacle')

# Draw the Swept Capsule
capsule_rect = patches.Rectangle((drone_x, drone_y - drone_radius), 8, drone_radius * 2, 
                                 linewidth=0, facecolor='green', alpha=0.3, label='Swept Capsule Area')
ax2.add_patch(capsule_rect)
ax2.plot([drone_x, 8], [drone_y, drone_y], color='green', linewidth=2, linestyle='--')

ax2.text(4, -1.5, "Capsule overlaps obstacle.\nCollision detected safely!", color='green', fontsize=10, ha='center')
ax2.legend(loc="upper left")

# ==========================================
# 3. Minkowski Addition (The Math Trick)
# ==========================================
setup_plot(ax3, "3. Fat Obstacle (How computers do it)")

# Drone is shrunk to a dot
ax3.plot(drone_x, drone_y, marker='o', color='blue', markersize=8, label='Drone (Shrunk to Point)')

# Obstacle gets fatter
fat_radius = obs_radius + drone_radius
draw_circle(ax3, obs_x, obs_y, fat_radius, 'purple', 'Fat Obstacle (Obs + Drone)', alpha=0.3)
draw_circle(ax3, obs_x, obs_y, obs_radius, 'red', 'Original Obstacle')

# Draw the thin ray again
ax3.plot([drone_x, 8], [drone_y, drone_y], color='green', linewidth=2, label='Thin Laser Ray')

# Highlight the intersection
intersection_x = obs_x - np.sqrt(fat_radius**2 - obs_y**2)
ax3.plot(intersection_x, 0, marker='x', color='black', markersize=12, markeredgewidth=3, label='Math Intersection')

ax3.text(4, -1.5, "Thin ray hits Fat Obstacle.\nFast math, same safe result!", color='purple', fontsize=10, ha='center')
ax3.legend(loc="upper left")

plt.tight_layout()
plt.show()