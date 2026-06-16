"""
Visualize a rollout vs RAMMERS — adversaries in RED, honest drones in BLUE.

Runs one episode of a chosen model against f rammers and saves an animated GIF so you can
SEE how the swarm behaves (do honest drones dodge the red rammers, or get caught?).

Usage:
    python visualize_ram.py                                          # M1, f=2, density 0.30
    python visualize_ram.py models/apex_ultra_glide_M1_ram_final.zip 2 0.30 7
    python visualize_ram.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 2 0.30 7   # M0 for comparison
Args: [model_path] [f] [density] [seed]
Output: results/phase_c_probe/ram_viz_<tag>_f<f>_d<density>.gif
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")  # headless: save GIF, no display needed
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

MAX_FRAMES = 400
TRAIL = 12


class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], 130
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], 520
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f): return self.policy_net(f[:, :130])
    def forward_critic(self, f): return self.value_net(f[:, 130:])


class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else "models/apex_ultra_glide_M1_ram_final.zip"
    f = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    density = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
    traitors = set(range(f))
    tag = "M1" if "M1_ram" in model_path else ("M0" if ("comm8_lidar" in model_path or "8_0m" in model_path) else os.path.splitext(os.path.basename(model_path))[0])
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] VISUALIZE | model={model_path} ({tag}) | f={f} rammers (RED) | density={density} | seed={seed}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=8.0, congestion_mode="lidar")
    env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
    obs_dict, _ = env.reset(seed=seed)
    obstacles = list(env.obstacles)
    goal = env.goal.copy()
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

    # record rollout
    last_known = env.positions.copy()
    finished = set()
    fate = {i: None for i in range(10)}   # 'success' | 'collision' | None(alive)
    frames_pos, frames_alive = [], []
    t = 0
    while t < MAX_FRAMES:
        active = [a for a in obs_dict.keys() if a not in finished]
        if not active:
            break
        cur = last_known.copy()
        for a in active:
            cur[amap[a]] = env.positions[amap[a]].copy()
        alive = np.array([f"drone_{i}" in env.agents for i in range(10)])
        frames_pos.append(cur.copy()); frames_alive.append(alive.copy())
        last_known = cur

        obs_batch = np.array([obs_dict[a] for a in active])
        act, _ = model.predict(obs_batch, deterministic=True)
        action = {a: act[k] for k, a in enumerate(active)}
        obs_dict, _, terms, truncs, infos = env.step(action)
        for a in active:
            if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                finished.add(a)
                fate[amap[a]] = infos[a].get("cause")
        t += 1
        if not env.agents:
            break
    env.close()

    n_honest = 10 - f
    honest_reached = sum(1 for i in range(10) if i not in traitors and fate[i] == "success")
    print(f"[*] episode recorded: {len(frames_pos)} frames | honest reached {honest_reached}/{n_honest}")

    # ---- animate ----
    fig, ax = plt.subplots(figsize=(7, 7))
    posarr = np.array(frames_pos)        # (T,10,2)
    alivearr = np.array(frames_alive)    # (T,10)

    def draw(t):
        ax.clear()
        ax.set_xlim(0, env.WIDTH); ax.set_ylim(0, env.HEIGHT); ax.set_aspect('equal')
        ax.set_title(f"{tag} vs {f} rammers (RED)  |  step {t}/{len(frames_pos)}  |  honest reached {honest_reached}/{n_honest}")
        # obstacles
        for (ox, oy, orad) in obstacles:
            ax.add_patch(plt.Circle((ox, oy), orad, color="0.6", alpha=0.5, zorder=1))
        # goal
        ax.scatter([goal[0]], [goal[1]], marker="*", s=400, color="green", zorder=2, label="goal")
        lo = max(0, t - TRAIL)
        for i in range(10):
            is_ram = i in traitors
            alive_now = alivearr[t, i]
            xy = posarr[t, i]
            if xy[0] < -1:   # teleported (done) -> skip
                continue
            color = "red" if is_ram else "royalblue"
            # trail
            seg = posarr[lo:t + 1, i]
            seg = seg[(seg[:, 0] > -1)]
            if len(seg) > 1:
                ax.plot(seg[:, 0], seg[:, 1], color=color, alpha=0.3, lw=1, zorder=2)
            if alive_now:
                ax.scatter([xy[0]], [xy[1]], s=(150 if is_ram else 90),
                           color=color, edgecolors="black", zorder=3,
                           marker=("X" if is_ram else "o"))
        ax.legend(loc="upper left", fontsize=8)

    ani = FuncAnimation(fig, draw, frames=len(frames_pos), interval=60)
    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"ram_viz_{tag}_f{f}_d{density}.gif")
    try:
        ani.save(out, writer=PillowWriter(fps=15))
        print(f"[OK] saved GIF: {out}")
    except Exception as e:
        print(f"[!] GIF save failed ({e}); saving snapshot PNGs instead.")
        for tt in [0, len(frames_pos) // 3, 2 * len(frames_pos) // 3, len(frames_pos) - 1]:
            draw(tt); fig.savefig(os.path.join(out_dir, f"ram_snap_{tag}_f{f}_t{tt}.png"), dpi=120)
        print(f"[OK] saved snapshots in {out_dir}")
    plt.close(fig)


if __name__ == "__main__":
    main()
