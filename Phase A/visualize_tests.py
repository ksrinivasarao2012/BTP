"""
╔══════════════════════════════════════════════════════════╗
║  Visual Test Case Runner — TA-MAPPO Swarm Visualization  ║
╚══════════════════════════════════════════════════════════╝
Renders the trained drone swarm navigating test scenarios in PyGame
with a full HUD overlay showing live metrics and drone status.

Usage:
    python visualize_tests.py                  # Run all 5 edge cases sequentially
    python visualize_tests.py edge_case_1      # Run a specific edge case
    python visualize_tests.py random           # Watch 10 random scenarios
    python visualize_tests.py random 25        # Watch 25 random scenarios
"""

import numpy as np
import pygame
import json
import glob
import sys
import os
import time
from stable_baselines3 import PPO
from swarm_env_step_A import SwarmLidarEnv_StepA

# ──────────────────── Color Palette ────────────────────
BG_COLOR       = (20, 20, 30)
GRID_COLOR     = (40, 40, 55)
GOAL_COLOR     = (50, 200, 80)
GOAL_GLOW      = (30, 120, 50)
DRONE_ALIVE    = (80, 140, 255)
DRONE_SUCCESS  = (50, 220, 100)
DRONE_DEAD     = (220, 60, 60)
TRAIL_COLOR    = (60, 100, 200, 80)
HUD_BG         = (15, 15, 25, 200)
TEXT_WHITE      = (230, 230, 240)
TEXT_DIM        = (140, 140, 160)
TEXT_GREEN      = (80, 220, 120)
TEXT_RED        = (220, 80, 80)
TEXT_YELLOW     = (240, 200, 60)
SEPARATOR      = (60, 60, 80)

# ──────────────────── Constants ────────────────────
SCREEN_W, SCREEN_H = 900, 900
FIELD_SIZE = 20.0
HUD_HEIGHT = 160
FIELD_AREA_H = SCREEN_H - HUD_HEIGHT
FPS = 30


def world_to_screen(pos):
    """Convert world coordinates (0-20) to screen pixel coordinates."""
    px = max(0.0, min(float(pos[0]), FIELD_SIZE))
    py = max(0.0, min(float(pos[1]), FIELD_SIZE))
    sx = int((px / FIELD_SIZE) * SCREEN_W)
    sy = int(FIELD_AREA_H - (py / FIELD_SIZE) * FIELD_AREA_H)
    return sx, sy


def draw_grid(screen):
    """Draw a subtle background grid."""
    for i in range(21):
        x = int((i / FIELD_SIZE) * SCREEN_W)
        y = int(FIELD_AREA_H - (i / FIELD_SIZE) * FIELD_AREA_H)
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, FIELD_AREA_H), 1)
        pygame.draw.line(screen, GRID_COLOR, (0, y), (SCREEN_W, y), 1)


def draw_goal(screen, goal_pos, pulse_frame):
    """Draw the goal with a pulsing glow effect."""
    gx, gy = world_to_screen(goal_pos)
    pulse = int(8 * abs(np.sin(pulse_frame * 0.05)))
    
    # Outer glow
    glow_surf = pygame.Surface((60 + pulse * 2, 60 + pulse * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*GOAL_GLOW, 40), (30 + pulse, 30 + pulse), 30 + pulse)
    screen.blit(glow_surf, (gx - 30 - pulse, gy - 30 - pulse))
    
    # Inner goal circle
    pygame.draw.circle(screen, GOAL_COLOR, (gx, gy), 18)
    pygame.draw.circle(screen, (255, 255, 255), (gx, gy), 6)


def draw_drones(screen, env, trails, font_small):
    """Draw all drones with ID labels and color-coded status."""
    for i in range(env.n_drones):
        agent_name = env.possible_agents[i]
        pos = env.positions[i]
        sx, sy = world_to_screen(pos)
        
        # Determine drone status and color
        is_alive = agent_name in env.agents
        is_success = env.terminations.get(agent_name, False) and not is_alive
        
        if is_alive:
            color = DRONE_ALIVE
            radius = 9
            # Draw trail
            if len(trails[i]) > 1:
                trail_points = [world_to_screen(p) for p in trails[i][-30:]]
                if len(trail_points) >= 2:
                    for j in range(len(trail_points) - 1):
                        alpha = int(60 * (j / len(trail_points)))
                        trail_col = (TRAIL_COLOR[0], TRAIL_COLOR[1], TRAIL_COLOR[2], alpha)
                        trail_surf = pygame.Surface((SCREEN_W, FIELD_AREA_H), pygame.SRCALPHA)
                        pygame.draw.line(trail_surf, trail_col, trail_points[j], trail_points[j+1], 2)
                        screen.blit(trail_surf, (0, 0))
        elif is_success:
            color = DRONE_SUCCESS
            radius = 7
        else:
            color = DRONE_DEAD
            radius = 7
        
        # Draw drone body
        pygame.draw.circle(screen, color, (sx, sy), radius)
        pygame.draw.circle(screen, (255, 255, 255, 120), (sx, sy), radius, 1)
        
        # Draw drone ID
        id_text = font_small.render(str(i), True, TEXT_WHITE)
        screen.blit(id_text, (sx - id_text.get_width() // 2, sy - radius - 14))


def draw_hud(screen, fonts, test_name, episode_num, total_episodes, step, 
             successes, collisions, timeouts, active_count, total_drones=10):
    """Draw the heads-up display panel at the bottom."""
    font_title, font_main, font_small = fonts
    
    # HUD background
    hud_rect = pygame.Rect(0, FIELD_AREA_H, SCREEN_W, HUD_HEIGHT)
    hud_surf = pygame.Surface((SCREEN_W, HUD_HEIGHT), pygame.SRCALPHA)
    hud_surf.fill(HUD_BG)
    screen.blit(hud_surf, (0, FIELD_AREA_H))
    
    # Separator line
    pygame.draw.line(screen, SEPARATOR, (0, FIELD_AREA_H), (SCREEN_W, FIELD_AREA_H), 2)
    
    y_base = FIELD_AREA_H + 10
    
    # Row 1: Test case name & episode counter
    title_surf = font_title.render(f"📋 {test_name}", True, TEXT_WHITE)
    screen.blit(title_surf, (15, y_base))
    
    ep_text = f"Episode {episode_num}/{total_episodes}"
    ep_surf = font_main.render(ep_text, True, TEXT_DIM)
    screen.blit(ep_surf, (SCREEN_W - ep_surf.get_width() - 15, y_base + 2))
    
    y_base += 35
    
    # Row 2: Live metrics
    # Step counter
    step_surf = font_main.render(f"Step: {step}/600", True, TEXT_DIM)
    screen.blit(step_surf, (15, y_base))
    
    # Active drones
    active_surf = font_main.render(f"Active: {active_count}/10", True, TEXT_YELLOW)
    screen.blit(active_surf, (180, y_base))
    
    y_base += 30
    
    # Row 3: Cumulative results  
    # Success count
    suc_surf = font_main.render(f"✅ Success: {successes}", True, TEXT_GREEN)
    screen.blit(suc_surf, (15, y_base))
    
    # Collision count
    col_surf = font_main.render(f"💥 Collisions: {collisions}", True, TEXT_RED)
    screen.blit(col_surf, (220, y_base))
    
    # Timeout count
    to_surf = font_main.render(f"⏳ Timeout: {timeouts}", True, TEXT_DIM)
    screen.blit(to_surf, (460, y_base))
    
    # Success rate
    total_resolved = successes + collisions + timeouts
    if total_resolved > 0:
        rate = (successes / total_resolved) * 100
        rate_color = TEXT_GREEN if rate >= 95 else TEXT_YELLOW if rate >= 80 else TEXT_RED
        rate_surf = font_main.render(f"Rate: {rate:.1f}%", True, rate_color)
        screen.blit(rate_surf, (SCREEN_W - rate_surf.get_width() - 15, y_base))
    
    y_base += 30
    
    # Row 4: Controls
    ctrl_surf = font_small.render("SPACE=Pause  N=Next  ESC=Quit  +/-=Speed", True, TEXT_DIM)
    screen.blit(ctrl_surf, (15, y_base))


def load_test_cases(specific_file=None):
    """Load test case scenarios from JSON files."""
    scenarios = []
    
    if specific_file:
        path = f"test_cases/basic/{specific_file}"
        if not path.endswith('.json'):
            path += '.json'
        json_files = [path]
    else:
        json_files = sorted(glob.glob("test_cases/basic/*.json"))
    
    for file in json_files:
        if not os.path.exists(file):
            print(f"❌ File not found: {file}")
            continue
        with open(file, 'r') as f:
            data = json.load(f)
            for scenario in data["scenarios"]:
                scenarios.append({
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "options": {
                        "start_positions": scenario["start_positions"],
                        "goal": scenario["goal"]
                    }
                })
    return scenarios


def generate_random_scenarios(count):
    """Generate random test scenarios."""
    scenarios = []
    for i in range(count):
        scenarios.append({
            "name": f"Random Scenario #{i+1}",
            "description": "Randomly generated drone positions and goal",
            "options": {
                "start_positions": [
                    [np.random.uniform(1.0, 19.0), np.random.uniform(1.0, 19.0)] 
                    for _ in range(10)
                ],
                "goal": [np.random.uniform(1.0, 19.0), np.random.uniform(1.0, 19.0)]
            }
        })
    return scenarios


def run_visual(scenarios):
    """Main visual runner — renders scenarios with full HUD."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("TA-MAPPO Swarm Visualizer")
    clock = pygame.time.Clock()
    
    # Fonts
    try:
        font_title = pygame.font.SysFont("DejaVu Sans", 22, bold=True)
        font_main = pygame.font.SysFont("DejaVu Sans", 18)
        font_small = pygame.font.SysFont("DejaVu Sans", 14)
    except:
        font_title = pygame.font.Font(None, 26)
        font_main = pygame.font.Font(None, 22)
        font_small = pygame.font.Font(None, 18)
    fonts = (font_title, font_main, font_small)
    
    # Load model
    print("Loading model...")
    model = PPO.load("./models/step_A_foundation_model")
    env = SwarmLidarEnv_StepA(render_mode=None)  # We do our own rendering
    
    # Global metrics
    total_success = 0
    total_collision = 0
    total_timeout = 0
    
    paused = False
    speed_mult = 1.0
    
    for ep_idx, scenario in enumerate(scenarios):
        test_name = scenario["name"]
        options = scenario["options"]
        
        print(f"\n▶ Episode {ep_idx+1}/{len(scenarios)}: {test_name}")
        
        obs, info = env.reset(options=options)
        trails = [[] for _ in range(10)]  # Position trails per drone
        step = 0
        ep_success = 0
        ep_collision = 0
        
        # Store initial positions for trails
        for i in range(10):
            trails[i].append(env.positions[i].copy())
        
        running = True
        skip_episode = False
        
        while env.agents and running and not skip_episode:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_n:
                        skip_episode = True
                    elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                        speed_mult = min(speed_mult * 2, 8.0)
                    elif event.key == pygame.K_MINUS:
                        speed_mult = max(speed_mult / 2, 0.25)
            
            if paused:
                # Still draw the frame while paused
                draw_frame(screen, env, trails, fonts, test_name, 
                          ep_idx + 1, len(scenarios), step,
                          total_success + ep_success, 
                          total_collision + ep_collision,
                          total_timeout, font_small)
                
                # Draw pause indicator
                pause_surf = font_title.render("⏸ PAUSED", True, TEXT_YELLOW)
                screen.blit(pause_surf, (SCREEN_W // 2 - pause_surf.get_width() // 2, 20))
                pygame.display.flip()
                clock.tick(15)
                continue
            
            # Step the environment
            actions = {}
            for agent in env.agents:
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
            
            obs, rewards, terminations, truncations, infos = env.step(actions)
            step += 1
            
            # Record trails
            for i in range(10):
                if env.possible_agents[i] in env.agents:
                    trails[i].append(env.positions[i].copy())
            
            # Count terminations
            for agent, term in terminations.items():
                if term and agent in rewards:
                    if rewards[agent] <= -50.0:
                        ep_collision += 1
                    elif rewards[agent] >= 50.0:
                        ep_success += 1
            
            # Draw the frame
            draw_frame(screen, env, trails, fonts, test_name,
                      ep_idx + 1, len(scenarios), step,
                      total_success + ep_success,
                      total_collision + ep_collision,
                      total_timeout, font_small)
            pygame.display.flip()
            
            # Speed control
            target_fps = int(FPS * speed_mult)
            clock.tick(target_fps)
        
        # Episode finished — count timeouts
        ep_timeout = 10 - ep_success - ep_collision
        total_success += ep_success
        total_collision += ep_collision
        total_timeout += ep_timeout
        
        print(f"   ✅ {ep_success}  💥 {ep_collision}  ⏳ {ep_timeout}")
        
        # Brief pause between episodes 
        if not skip_episode and ep_idx < len(scenarios) - 1:
            # Show "COMPLETE" overlay for 1.5 seconds
            draw_frame(screen, env, trails, fonts, test_name,
                      ep_idx + 1, len(scenarios), step,
                      total_success, total_collision, total_timeout, font_small)
            
            result_text = f"Episode Complete — ✅ {ep_success}/10"
            result_color = TEXT_GREEN if ep_success == 10 else TEXT_YELLOW if ep_success >= 8 else TEXT_RED
            result_surf = font_title.render(result_text, True, result_color)
            
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_W, FIELD_AREA_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
            screen.blit(result_surf, (SCREEN_W // 2 - result_surf.get_width() // 2, FIELD_AREA_H // 2 - 15))
            
            next_surf = font_main.render("Next episode in 2s... (Press N to skip)", True, TEXT_DIM)
            screen.blit(next_surf, (SCREEN_W // 2 - next_surf.get_width() // 2, FIELD_AREA_H // 2 + 20))
            
            pygame.display.flip()
            
            # Wait 2 seconds but allow skipping
            wait_start = time.time()
            while time.time() - wait_start < 2.0:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_n, pygame.K_SPACE, pygame.K_RETURN):
                            break
                        elif event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            return
                else:
                    clock.tick(30)
                    continue
                break
    
    # ────── Final Summary Screen ─────
    total_drones = len(scenarios) * 10
    rate = (total_success / total_drones * 100) if total_drones > 0 else 0
    
    print(f"\n{'='*50}")
    print(f" FINAL RESULTS")
    print(f"{'='*50}")
    print(f" Episodes:   {len(scenarios)}")
    print(f" Drones:     {total_drones}")
    print(f" ✅ Success:  {total_success} ({total_success/total_drones*100:.1f}%)")
    print(f" 💥 Collision: {total_collision} ({total_collision/total_drones*100:.1f}%)")
    print(f" ⏳ Timeout:  {total_timeout} ({total_timeout/total_drones*100:.1f}%)")
    print(f"{'='*50}")
    
    # Final screen
    screen.fill(BG_COLOR)
    y = 100
    lines = [
        ("VISUALIZATION COMPLETE", font_title, TEXT_WHITE),
        ("", font_small, TEXT_DIM),
        (f"Episodes: {len(scenarios)}    Drones: {total_drones}", font_main, TEXT_DIM),
        ("", font_small, TEXT_DIM),
        (f"✅ Success: {total_success}  ({total_success/total_drones*100:.1f}%)", font_main, TEXT_GREEN),
        (f"💥 Collision: {total_collision}  ({total_collision/total_drones*100:.1f}%)", font_main, TEXT_RED),
        (f"⏳ Timeout: {total_timeout}  ({total_timeout/total_drones*100:.1f}%)", font_main, TEXT_DIM),
        ("", font_small, TEXT_DIM),
        (f"Overall Rate: {rate:.1f}%", font_title, TEXT_GREEN if rate >= 95 else TEXT_YELLOW),
        ("", font_small, TEXT_DIM),
        ("Press ESC or close window to exit", font_small, TEXT_DIM),
    ]
    for text, font, color in lines:
        if text:
            surf = font.render(text, True, color)
            screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))
        y += 35
    
    pygame.display.flip()
    
    # Wait for the user to close
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                waiting = False
        clock.tick(15)
    
    pygame.quit()


def draw_frame(screen, env, trails, fonts, test_name, ep_num, total_eps, 
               step, successes, collisions, timeouts, font_small):
    """Draw a single complete frame: field + drones + HUD."""
    # Clear
    screen.fill(BG_COLOR)
    
    # Grid
    draw_grid(screen)
    
    # Goal
    draw_goal(screen, env.goal, step)
    
    # Drones
    draw_drones(screen, env, trails, font_small)
    
    # HUD
    active_count = len(env.agents)
    draw_hud(screen, fonts, test_name, ep_num, total_eps, step,
             successes, collisions, timeouts, active_count)


# ──────────────────── Main ────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Running all edge cases visually...")
        scenarios = load_test_cases()
    elif sys.argv[1].lower() == "random":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"Generating {count} random scenarios...")
        scenarios = generate_random_scenarios(count)
    else:
        specific = sys.argv[1]
        print(f"Loading specific test case: {specific}")
        scenarios = load_test_cases(specific)
    
    if not scenarios:
        print("❌ No test cases found!")
        sys.exit(1)
    
    print(f"Loaded {len(scenarios)} scenario(s). Launching visualizer...")
    run_visual(scenarios)
