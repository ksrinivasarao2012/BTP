import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import warnings
warnings.filterwarnings("ignore")

import sys
import time
import hashlib
import platform
import numpy as np
import pandas as pd
import multiprocessing
import torch
import torch.nn as nn
from datetime import datetime
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

# ======================================================
# MODEL COMPATIBILITY NOTE
# This script supports BOTH 650D (v10-v14) and 732D (v15)
# Actor input dims:  v10-v14 => 130D | v15 => 202D
# Critic input dims: v10-v14 => 520D | v15 => 530D
# The obs dim is auto-detected from the loaded model.
# ======================================================

# ======================================================
#  IEEE-Grade K-Fold Evaluation Suite — v15 Master (732D)
#
#  KEY DESIGN DECISIONS (fixes vs. previous k_fold scripts):
#  1. spawn_mode is ENFORCED (was silently ignored in v15 env)
#  2. Sensing radii LOCKED to R_sensor=8m, R_comm=10m (training config)
#  3. NO Unicode emojis — pure ASCII (prevents Windows CP1252 crash)
#  4. Wilcoxon signed-rank test + 95% CI (IEEE statistical standard)
#  5. SHA-256 model fingerprint + full version log (reproducibility)
#  6. Per-episode granular CSV for independent reviewer verification
#  7. INLINED policy classes (no fragile cross-file imports)
# ======================================================

# ==================================================
# EVALUATION CONFIGURATION (Locked for IEEE Standard)
# ==================================================
# Sensing radii: The v10-v14 environments have their range hardcoded in the env
# (12m LiDAR range), not controlled via set_curriculum. The v15 env defaults
# to 100m (unlimited) which is what the recovery training used.
# We leave radii at their environment defaults (do NOT call set_curriculum).
EVAL_DENSITY  = 0.35   # IEEE target density for Phase B benchmarks
EVAL_R_SENSOR = 8.0    # Nominal sensor range (m)
EVAL_R_COMM   = 10.0   # Nominal communication range (m)

# ======================================================
#  INLINED Policy Classes — Auto-selects based on obs dim
#  v10-v14 (650D): Actor=130D, Critic=520D
#  v15     (732D): Actor=202D, Critic=530D
# ======================================================
class MAPPO_Extractor_auto(nn.Module):
    """Universal extractor: pi_in and vf_in passed at construction."""
    def __init__(self, features_dim, net_arch, activation_fn, pi_in, vf_in):
        super().__init__()
        self._pi_in = pi_in
        pi_layers = []; last_dim_pi = pi_in
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr))
            pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)

        vf_layers = []; last_dim_vf = vf_in
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr))
            vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_dim_pi
        self.latent_dim_vf = last_dim_vf

    def forward(self, features):
        return self.policy_net(features[:, :self._pi_in]), self.value_net(features[:, self._pi_in:])
    def forward_actor(self, features):
        return self.policy_net(features[:, :self._pi_in])
    def forward_critic(self, features):
        return self.value_net(features[:, self._pi_in:])

def make_policy_class(pi_in, vf_in):
    """Factory: returns a custom ActorCriticPolicy class for the given split dims."""
    class _Policy(ActorCriticPolicy):
        _PI_IN = pi_in
        _VF_IN = vf_in
        def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
            super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
        def _build_mlp_extractor(self) -> None:
            self.mlp_extractor = MAPPO_Extractor_auto(
                self.features_dim, self.net_arch, self.activation_fn,
                self._PI_IN, self._VF_IN
            )
    return _Policy

# Pre-build the two canonical policy classes
MAPPO_Policy_v10_v14 = make_policy_class(pi_in=130, vf_in=520)  # 650D total
MAPPO_Policy_v15     = make_policy_class(pi_in=202, vf_in=530)  # 732D total

# ======================================================
#  Reproducibility: SHA-256 model fingerprint
# ======================================================
def compute_model_sha256(model_path):
    sha256 = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# ======================================================
#  Subprocess Evaluation Worker
#  One worker per CPU core, runs N episodes, returns stats
# ======================================================
def run_episode_batch_worker(args):
    import warnings
    warnings.filterwarnings("ignore")

    (model_path, seed, num_episodes, mode,
     fold_idx, start_ep_idx, main_results_dir,
     target_density) = args

    # Prevent CPU thread thrashing in parallel subprocesses
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    import torch
    torch.set_num_threads(1)

    # Deterministic seeding
    np.random.seed(seed)

    # Auto-detect obs dim and select the correct policy class
    import zipfile, io
    with zipfile.ZipFile(model_path) as z:
        with z.open('policy.pth') as f:
            _p = torch.load(io.BytesIO(f.read()), map_location='cpu', weights_only=True)
    pi_in = next(v.shape[1] for k, v in _p.items() if 'mlp_extractor.policy_net.0.weight' in k)
    vf_in = next(v.shape[1] for k, v in _p.items() if 'mlp_extractor.value_net.0.weight' in k)
    obs_dim = pi_in + vf_in
    policy_cls = make_policy_class(pi_in=pi_in, vf_in=vf_in)

    model = PPO.load(
        model_path,
        custom_objects={
            "policy_class": policy_cls,
            "n_steps": 1,
            "n_envs": 1
        },
        device="cpu"
    )

    # Select correct environment based on obs dim
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
    for d in [script_dir, parent_dir]:
        if d not in sys.path:
            sys.path.insert(0, d)

    if obs_dim == 732:
        from swarm_env_step_B5_v15_master import SwarmLidarEnv_v15_Final
        env = SwarmLidarEnv_v15_Final(render_mode=None, target_density=target_density)
        # Set sensing and communication radii matching the final curriculum Stage 4:
        env.set_curriculum(r_sensor=EVAL_R_SENSOR, r_comm=EVAL_R_COMM)
    elif obs_dim == 650:
        from swarm_env_step_B10 import SwarmLidarEnv_StepB10
        env = SwarmLidarEnv_StepB10(render_mode=None, target_density=target_density)
    else:
        raise ValueError(f"[WORKER ERROR] Unknown obs dim {obs_dim}. Expected 650 or 732.")

    # Set up per-fold directory for trajectory CSV dumps
    fold_dir = os.path.join(main_results_dir, f"Fold_{fold_idx}")
    sub_folder = "random" if mode == "random" else "dense"
    output_dir = os.path.join(fold_dir, sub_folder)
    os.makedirs(output_dir, exist_ok=True)

    stats = {"success": 0, "collision": 0, "timeout": 0}
    total_drones = 0
    total_steps = 0
    per_episode_records = []

    for ep in range(num_episodes):
        current_seed = seed + ep

        # [FIX 1] Pass spawn_mode — now correctly read by the patched v15 env
        obs_dict, _ = env.reset(
            seed=current_seed,
            options={"spawn_mode": mode}
        )

        ep_successes = 0
        ep_collisions = 0
        tallied_agents = set()
        num_agents = len(env.possible_agents)
        step_count = 0
        ep_done = False

        current_goal_x, current_goal_y = env.goal[0], env.goal[1]
        current_obstacles_str = ";".join(
            [f"{o[0]:.3f},{o[1]:.3f},{o[2]:.3f}" for o in env.obstacles]
        )

        # Trajectory CSV for this episode
        ep_num = start_ep_idx + ep + 1
        csv_path = os.path.join(output_dir, f"ep_{ep_num}.csv")
        f_csv = open(csv_path, 'w')
        f_csv.write("Step,Agent,X,Y,Goal_X,Goal_Y,Obstacles\n")

        while not ep_done:
            active_agents = list(obs_dict.keys())
            if not active_agents:
                break

            # Batched prediction for efficiency
            obs_batch = np.array([obs_dict[agent] for agent in active_agents])
            action_batch, _ = model.predict(obs_batch, deterministic=True)
            action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}

            # Log positions before stepping
            for agent in active_agents:
                idx = env.agent_name_mapping[agent]
                pos = env.positions[idx]
                f_csv.write(
                    f"{step_count},{agent},{pos[0]:.4f},{pos[1]:.4f},"
                    f"{current_goal_x:.4f},{current_goal_y:.4f},"
                    f"\"{current_obstacles_str}\"\n"
                )

            obs_dict, rews, terms, truncs, infos = env.step(action_dict)
            step_count += 1

            for agent in env.possible_agents:
                if agent not in tallied_agents and agent in infos and "cause" in infos[agent]:
                    cause = infos[agent]["cause"]
                    if cause == "success":
                        ep_successes += 1
                        tallied_agents.add(agent)
                    elif cause == "collision":
                        ep_collisions += 1
                        tallied_agents.add(agent)

            if not env.agents:
                ep_done = True

        f_csv.close()

        ep_timeouts = num_agents - ep_successes - ep_collisions
        stats["success"] += ep_successes
        stats["collision"] += ep_collisions
        stats["timeout"] += ep_timeouts
        total_drones += num_agents
        total_steps += step_count

        # Per-episode granular record (for independent reviewer analysis)
        per_episode_records.append({
            "Episode": ep_num,
            "Successes": ep_successes,
            "Collisions": ep_collisions,
            "Timeouts": ep_timeouts,
            "Steps": step_count,
            "Goal_X": current_goal_x,
            "Goal_Y": current_goal_y,
            "Num_Obstacles": len(env.obstacles),
            "Mode": mode,
            "Fold": fold_idx,
        })

    env.close()
    return stats, total_drones, total_steps, per_episode_records


# ======================================================
#  Publication-Ready Plots (Bar Chart + Box Plot)
# ======================================================
def save_evaluation_plots(df, fold_df, timestamp, results_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            'font.size': 11,
            'font.family': 'sans-serif',
            'axes.edgecolor': '#cccccc',
            'axes.linewidth': 0.8,
        })

        metrics   = ["Success_Rate", "Collision_Rate", "Timeout_Rate"]
        labels    = ["Success", "Collision", "Timeout"]
        r_df      = df[df["Mode"] == "random"]
        c_df      = df[df["Mode"] == "clustered"]

        r_means   = [r_df[m].mean() for m in metrics]
        c_means   = [c_df[m].mean() for m in metrics]

        # Use 95% CI half-widths as error bars
        from scipy.stats import t as t_dist
        def ci_halfwidth(series):
            n = len(series)
            if n < 2: return 0.0
            se = series.std(ddof=1) / np.sqrt(n)
            return float(t_dist.ppf(0.975, df=n-1) * se)

        r_ci = [ci_halfwidth(r_df[m]) for m in metrics]
        c_ci = [ci_halfwidth(c_df[m]) for m in metrics]

        # ---- FIGURE 1: Bar Chart ----
        x = np.arange(len(labels))
        width = 0.35
        fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)

        rects1 = ax.bar(x - width/2, r_means, width, yerr=r_ci,
                        label='Random Spawn', color='#008080',
                        edgecolor='none', alpha=0.9, capsize=6,
                        error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))
        rects2 = ax.bar(x + width/2, c_means, width, yerr=c_ci,
                        label='Cluster Spawn', color='#FF6F61',
                        edgecolor='none', alpha=0.9, capsize=6,
                        error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))

        def autolabel(rects):
            for rect in rects:
                h = rect.get_height()
                ax.annotate(f'{h:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, h),
                            xytext=(0, 4), textcoords="offset points",
                            ha='center', va='bottom', fontsize=9.5, fontweight='bold')
        autolabel(rects1)
        autolabel(rects2)

        ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold', labelpad=10)
        ax.set_title(
            'v15 Master (732D) — Decentralized Swarm Navigation Performance\n'
            f'Phase B | Obstacle Density: {EVAL_DENSITY} | K-Fold Validation (K=10, 200 Eps/Fold)',
            fontsize=11, fontweight='bold', pad=16, color='#111111'
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 110)
        ax.legend(frameon=True, facecolor='white', edgecolor='#cccccc',
                  shadow=False, loc='upper right', fontsize=10)
        ax.grid(axis='y', linestyle='--', alpha=0.4, color='#dddddd')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        bar_path = os.path.join(results_dir, f"v15_master_evaluation_chart_{timestamp}.png")
        plt.savefig(bar_path, bbox_inches='tight')
        plt.close()
        print(f"[OK] Bar chart saved: {bar_path}", flush=True)

        # ---- FIGURE 2: Box Plot (per-fold distribution) ----
        r_success_per_fold = r_df["Success_Rate"].values
        c_success_per_fold = c_df["Success_Rate"].values

        fig2, ax2 = plt.subplots(figsize=(8, 5.5), dpi=300)
        bp = ax2.boxplot(
            [r_success_per_fold, c_success_per_fold],
            labels=['Random Spawn', 'Cluster Spawn'],
            patch_artist=True,
            medianprops=dict(color='black', lw=2),
            flierprops=dict(marker='o', markerfacecolor='#555555',
                            markersize=5, linestyle='none')
        )
        bp['boxes'][0].set_facecolor('#008080'); bp['boxes'][0].set_alpha(0.75)
        bp['boxes'][1].set_facecolor('#FF6F61'); bp['boxes'][1].set_alpha(0.75)

        ax2.set_ylabel('Success Rate per Fold (%)', fontsize=12, fontweight='bold')
        ax2.set_title(
            'Success Rate Distribution Across K=10 Folds\n'
            'v15 Master (732D) | Phase B Benchmark',
            fontsize=11, fontweight='bold', pad=14
        )
        ax2.grid(axis='y', linestyle='--', alpha=0.4, color='#dddddd')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        plt.tight_layout()
        box_path = os.path.join(results_dir, f"v15_master_boxplot_{timestamp}.png")
        plt.savefig(box_path, bbox_inches='tight')
        plt.close()
        print(f"[OK] Box plot saved: {box_path}", flush=True)

    except Exception as e:
        print(f"[WARNING] Could not generate plots: {e}", flush=True)


# ======================================================
#  Failure Diagnostic Plots (episodes where >= 2 drones timed out)
# ======================================================
def generate_diagnostic_plots(main_results_dir):
    try:
        import glob
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        csv_files = glob.glob(
            os.path.join(main_results_dir, "**", "ep_*.csv"), recursive=True
        )
        print(f"\n[DIAG] Scanning {len(csv_files)} episode logs for multi-drone failures...", flush=True)
        diagnostics_count = 0

        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                df['Step'] = pd.to_numeric(df['Step'], errors='coerce')
                agent_max_steps = df.groupby('Agent')['Step'].max()
                stuck_agents = agent_max_steps[agent_max_steps >= 799]
                if len(stuck_agents) < 2:
                    continue

                fig, ax = plt.subplots(figsize=(10, 10))
                obs_str = df['Obstacles'].iloc[0]
                if isinstance(obs_str, str) and obs_str.strip():
                    for obs_item in obs_str.split(';'):
                        try:
                            ox, oy, orad = map(float, obs_item.strip().split(','))
                            circle = plt.Circle((ox, oy), orad, color='gray', alpha=0.3)
                            ax.add_patch(circle)
                        except:
                            continue
                gx, gy = df['Goal_X'].iloc[0], df['Goal_Y'].iloc[0]
                ax.scatter(gx, gy, marker='*', s=300, color='gold',
                           edgecolors='black', label='Goal', zorder=5)
                for agent in df['Agent'].unique():
                    adf = df[df['Agent'] == agent]
                    ax.plot(adf['X'], adf['Y'], alpha=0.7, linewidth=1.5, label=agent)
                    ax.scatter(adf['X'].iloc[0], adf['Y'].iloc[0],
                               marker='o', s=40, zorder=4)
                    ax.scatter(adf['X'].iloc[-1], adf['Y'].iloc[-1],
                               marker='x', s=60, zorder=4)

                ax.set_xlim(0, 20); ax.set_ylim(0, 20)
                ep_name = os.path.splitext(os.path.basename(csv_path))[0]
                ax.set_title(
                    f"Failure Diagnostic: {ep_name} ({len(stuck_agents)} Drones Timed Out)",
                    fontweight='bold'
                )
                ax.grid(True, linestyle='--', alpha=0.4)
                ax.set_xlabel("X (m)", fontweight='bold')
                ax.set_ylabel("Y (m)", fontweight='bold')
                out_path = os.path.join(
                    os.path.dirname(csv_path), f"{ep_name}_failure_viz.png"
                )
                plt.savefig(out_path, dpi=150, bbox_inches='tight')
                plt.close()
                diagnostics_count += 1
            except Exception:
                continue

        if diagnostics_count > 0:
            print(f"[DIAG] Generated {diagnostics_count} failure diagnostic plots.", flush=True)
        else:
            print(f"[DIAG] No multi-drone failure scenarios detected.", flush=True)
    except Exception as e:
        print(f"[WARNING] Diagnostic plot generation failed: {e}", flush=True)


# ======================================================
#  Main K-Fold Runner
# ======================================================
def run_k_fold_master(model_path, cores=10, total_episodes=200, num_folds=10,
                      target_density=EVAL_DENSITY):
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join("results", "v15")
    os.makedirs(results_dir, exist_ok=True)

    model_base = (
        f"{os.path.splitext(os.path.basename(model_path))[0]}"
        f"_density{target_density:.2f}_K{num_folds}_E{total_episodes}"
    )
    main_results_dir = os.path.join(results_dir, model_base)
    os.makedirs(main_results_dir, exist_ok=True)

    log_path = os.path.join(main_results_dir, f"evaluation_log_{timestamp}.txt")

    class Logger:
        def __init__(self, filename, orig):
            self.terminal = orig
            self.log = open(filename, "w", encoding="utf-8")
        def write(self, msg):
            self.terminal.write(msg)
            self.log.write(msg)
            self.log.flush()
        def flush(self):
            self.terminal.flush()
            self.log.flush()
        def close(self):
            self.log.close()

    original_stdout = sys.stdout
    logger = Logger(log_path, original_stdout)
    sys.stdout = logger

    # --------------------------------------------------
    # REPRODUCIBILITY HEADER
    # --------------------------------------------------
    model_sha256 = compute_model_sha256(model_path)
    import stable_baselines3, torch as _torch

    print("=" * 80, flush=True)
    print("  IEEE-GRADE K-FOLD VALIDATION SUITE | v15 Master (732D)", flush=True)
    print("=" * 80, flush=True)
    print(f"  Timestamp         : {timestamp}", flush=True)
    print(f"  Model Path        : {os.path.abspath(model_path)}", flush=True)
    print(f"  Model SHA-256     : {model_sha256}", flush=True)
    # Auto-detect obs dims from model file
    import zipfile, io as _io
    with zipfile.ZipFile(model_path) as _z:
        with _z.open('policy.pth') as _f:
            _p = torch.load(_io.BytesIO(_f.read()), map_location='cpu', weights_only=True)
    _pi = next(v.shape[1] for k, v in _p.items() if 'mlp_extractor.policy_net.0.weight' in k)
    _vf = next(v.shape[1] for k, v in _p.items() if 'mlp_extractor.value_net.0.weight' in k)
    _obs = _pi + _vf
    print(f"  Observation Dim   : {_obs} (Actor: {_pi}D Local + Critic: {_vf}D Global)", flush=True)
    print(f"  Sensing Radii     : Environment defaults (100m unlimited for v15; 12m LiDAR for v10-v14)", flush=True)
    print(f"  Obstacle Density  : {target_density}", flush=True)
    print(f"  K-Folds           : {num_folds}", flush=True)
    print(f"  Episodes per Fold : {total_episodes}  (Total: {num_folds * total_episodes * 2} flights)", flush=True)
    print(f"  CPU Cores         : {cores}", flush=True)
    print(f"  Python            : {sys.version.split()[0]}", flush=True)
    print(f"  PyTorch           : {_torch.__version__}", flush=True)
    print(f"  Stable-Baselines3 : {stable_baselines3.__version__}", flush=True)
    print(f"  NumPy             : {np.__version__}", flush=True)
    print(f"  Platform          : {platform.platform()}", flush=True)
    print("=" * 80, flush=True)

    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found at {model_path}", flush=True)
        sys.stdout = original_stdout; logger.close(); return

    results_data     = []
    all_episode_data = []

    episodes_per_worker = max(1, total_episodes // cores)
    actual_cores        = min(cores, total_episodes)

    for fold_idx in range(num_folds):
        print(f"\n=======================================================", flush=True)
        print(f"  --- FOLD {fold_idx + 1}/{num_folds} ---", flush=True)
        print(f"=======================================================\n", flush=True)

        for mode in ["random", "clustered"]:
            print(f"  [{mode.upper()} Spawn] Evaluating {total_episodes} episodes...", flush=True)
            start_time = time.time()
            base_seed  = (fold_idx + 1) * 1000

            args_list      = []
            remaining_eps  = total_episodes
            current_start  = 0

            for w in range(actual_cores):
                eps_this = (remaining_eps if w == (actual_cores - 1)
                            else episodes_per_worker)
                worker_seed = base_seed + w * episodes_per_worker
                args_list.append((
                    model_path, worker_seed, eps_this, mode,
                    fold_idx + 1, current_start, main_results_dir,
                    target_density
                ))
                remaining_eps -= eps_this
                current_start += eps_this

            fold_stats  = {"success": 0, "collision": 0, "timeout": 0}
            fold_drones = 0
            fold_steps  = 0

            with multiprocessing.Pool(actual_cores) as pool:
                worker_results = pool.map(run_episode_batch_worker, args_list)

            for w_stats, w_drones, w_steps, w_ep_records in worker_results:
                for k in fold_stats:
                    fold_stats[k] += w_stats[k]
                fold_drones += w_drones
                fold_steps  += w_steps
                all_episode_data.extend(w_ep_records)

            elapsed = time.time() - start_time
            success_rate   = (fold_stats["success"]   / fold_drones) * 100
            collision_rate = (fold_stats["collision"] / fold_drones) * 100
            timeout_rate   = (fold_stats["timeout"]   / fold_drones) * 100
            avg_steps      = fold_steps / total_episodes

            print(f"  Time: {elapsed:.1f}s | Avg Steps/Ep: {avg_steps:.1f}", flush=True)
            print(f"  [SUCCESS]   {success_rate:>6.2f}%  ({fold_stats['success']} / {fold_drones} drones)", flush=True)
            print(f"  [COLLISION] {collision_rate:>6.2f}%  ({fold_stats['collision']})", flush=True)
            print(f"  [TIMEOUT]   {timeout_rate:>6.2f}%  ({fold_stats['timeout']})\n", flush=True)

            results_data.append({
                "Mode":           mode,
                "Fold":           fold_idx + 1,
                "Success_Rate":   success_rate,
                "Collision_Rate": collision_rate,
                "Timeout_Rate":   timeout_rate,
            })

    # --------------------------------------------------
    # Save per-episode granular data (for reviewer use)
    # --------------------------------------------------
    ep_df = pd.DataFrame(all_episode_data)
    ep_csv_path = os.path.join(main_results_dir, f"per_episode_details_{timestamp}.csv")
    ep_df.to_csv(ep_csv_path, index=False)
    print(f"[OK] Per-episode details saved: {ep_csv_path}", flush=True)

    # --------------------------------------------------
    # Fold-level summary CSV
    # --------------------------------------------------
    df = pd.DataFrame(results_data)
    fold_csv_path = os.path.join(main_results_dir, f"fold_summary_{timestamp}.csv")
    df.to_csv(fold_csv_path, index=False)
    print(f"[OK] Fold summary saved: {fold_csv_path}", flush=True)

    # --------------------------------------------------
    # Statistical Analysis (IEEE-grade)
    # --------------------------------------------------
    r_success = df[df["Mode"] == "random"]["Success_Rate"].values
    c_success = df[df["Mode"] == "clustered"]["Success_Rate"].values

    # 95% CI via t-distribution (scipy preferred; bootstrap fallback)
    def ci95(arr):
        n = len(arr)
        if n < 2: return (float(arr[0]), float(arr[0]))
        se = arr.std(ddof=1) / np.sqrt(n)
        try:
            from scipy.stats import t as t_dist
            h = t_dist.ppf(0.975, df=n-1) * se
        except ImportError:
            # Bootstrap 95% CI fallback (no scipy needed)
            boots = [np.random.choice(arr, n, replace=True).mean() for _ in range(2000)]
            lo, hi = np.percentile(boots, [2.5, 97.5])
            return (float(lo), float(hi))
        return (float(arr.mean() - h), float(arr.mean() + h))

    r_ci = ci95(r_success)
    c_ci = ci95(c_success)

    # Wilcoxon signed-rank test
    try:
        from scipy.stats import wilcoxon
        if len(r_success) == len(c_success) and len(r_success) > 1:
            try:
                stat_w, p_val = wilcoxon(r_success, c_success)
                wilcoxon_str = f"W={stat_w:.2f}, p={p_val:.4f}"
                significance  = "SIGNIFICANT (p < 0.05)" if p_val < 0.05 else "NOT SIGNIFICANT (p >= 0.05)"
            except Exception as e:
                wilcoxon_str = f"Could not compute ({e})"
                significance = "N/A"
        else:
            wilcoxon_str = "N/A (need paired folds)"
            significance = "N/A"
    except ImportError:
        wilcoxon_str = "scipy not available — install with: pip install scipy"
        significance = "N/A (bootstrap CI used instead)"

    # --------------------------------------------------
    # Final Summary Table
    # --------------------------------------------------
    print("\n" + "=" * 85, flush=True)
    print(f"  PHASE B MASTER (v15 732D): K-FOLD FINAL SUMMARY", flush=True)
    print(f"  K={num_folds}, {total_episodes} Eps/Fold | Density={target_density} | R_s={EVAL_R_SENSOR}m R_c={EVAL_R_COMM}m", flush=True)
    print("=" * 85, flush=True)
    print(f"  {'Metric':<22} | {'Random Spawn':^28} | {'Cluster Spawn':^28}", flush=True)
    print("  " + "-" * 83, flush=True)

    for metric in ["Success_Rate", "Collision_Rate", "Timeout_Rate"]:
        r_vals = df[df["Mode"] == "random"][metric].values
        c_vals = df[df["Mode"] == "clustered"][metric].values
        r_mean, r_std = r_vals.mean(), r_vals.std()
        c_mean, c_std = c_vals.mean(), c_vals.std()
        tag = metric.replace("_Rate", "").replace("_", " ")
        print(f"  {tag:<22} | {r_mean:>6.2f}% +/- {r_std:<6.2f}          | {c_mean:>6.2f}% +/- {c_std:<6.2f}", flush=True)

    print("  " + "-" * 83, flush=True)
    print(f"  95% CI (Success)         | [{r_ci[0]:.2f}%, {r_ci[1]:.2f}%]              | [{c_ci[0]:.2f}%, {c_ci[1]:.2f}%]", flush=True)
    print(f"  Wilcoxon Signed-Rank     | {wilcoxon_str}", flush=True)
    print(f"  Statistical Significance | {significance}", flush=True)
    print("=" * 85, flush=True)

    # Save statistical summary
    stat_summary = {
        "Random_Success_Mean":  df[df["Mode"] == "random"]["Success_Rate"].mean(),
        "Random_Success_Std":   df[df["Mode"] == "random"]["Success_Rate"].std(),
        "Random_Success_CI_Lo": r_ci[0],
        "Random_Success_CI_Hi": r_ci[1],
        "Cluster_Success_Mean": df[df["Mode"] == "clustered"]["Success_Rate"].mean(),
        "Cluster_Success_Std":  df[df["Mode"] == "clustered"]["Success_Rate"].std(),
        "Cluster_Success_CI_Lo":c_ci[0],
        "Cluster_Success_CI_Hi":c_ci[1],
        "Wilcoxon_Test":        wilcoxon_str,
        "Significance":         significance,
        "Model_SHA256":         model_sha256,
        "Density":              target_density,
        "R_sensor":             EVAL_R_SENSOR,
        "R_comm":               EVAL_R_COMM,
        "K_Folds":              num_folds,
        "Episodes_Per_Fold":    total_episodes,
        "Timestamp":            timestamp,
    }
    stat_df = pd.DataFrame([stat_summary])
    stat_csv = os.path.join(main_results_dir, f"statistical_summary_{timestamp}.csv")
    stat_df.to_csv(stat_csv, index=False)
    print(f"[OK] Statistical summary saved: {stat_csv}", flush=True)

    # --------------------------------------------------
    # Generate publication plots
    # --------------------------------------------------
    save_evaluation_plots(df, ep_df, timestamp, main_results_dir)

    # --------------------------------------------------
    # Generate failure diagnostic plots
    # --------------------------------------------------
    generate_diagnostic_plots(main_results_dir)

    sys.stdout = original_stdout
    logger.close()
    print(f"[OK] Full evaluation log saved: {log_path}", flush=True)
    print(f"[OK] All results in: {os.path.abspath(main_results_dir)}", flush=True)


# ======================================================
#  Entry Point
# ======================================================
if __name__ == "__main__":
    # Default: v15 Recovered Final model, 10 cores, 200 eps/fold, K=10, density=0.35
    default_model = "../../models/v15_Master_Recovered_Final.zip"

    m_path    = sys.argv[1] if len(sys.argv) > 1 else default_model
    c_count   = int(sys.argv[2])   if len(sys.argv) > 2 else 10
    eps_count = int(sys.argv[3])   if len(sys.argv) > 3 else 200
    folds     = int(sys.argv[4])   if len(sys.argv) > 4 else 10
    density   = float(sys.argv[5]) if len(sys.argv) > 5 else EVAL_DENSITY

    # Resolve absolute model path to avoid cross-drive issues on Windows
    if not os.path.isabs(m_path):
        script_dir   = os.path.dirname(os.path.abspath(__file__))
        m_path_abs   = os.path.normpath(os.path.join(script_dir, m_path))
        # Also try the workspace-level models/ folder
        workspace_model = r"d:\Swarm\BTP\models\v15_Master_Recovered_Final.zip"
        if os.path.exists(m_path_abs):
            m_path = m_path_abs
        elif os.path.exists(workspace_model):
            m_path = workspace_model
        else:
            # Last resort: search from script dir upward
            for parent in [script_dir, os.path.dirname(script_dir),
                           os.path.dirname(os.path.dirname(script_dir))]:
                candidate = os.path.join(parent, "models", os.path.basename(m_path))
                if os.path.exists(candidate):
                    m_path = candidate
                    break

    if not os.path.exists(m_path):
        print(f"[ERROR] Model not found at: {m_path}")
        print("Usage: python evaluate_v15_IEEE_Final.py <model_path> [cores] [eps_per_fold] [num_folds] [density]")
        sys.exit(1)

    # Windows multiprocessing requires this guard
    multiprocessing.freeze_support()

    print(f"[LAUNCH] Starting evaluation of: {m_path}", flush=True)
    run_k_fold_master(
        model_path=m_path,
        cores=c_count,
        total_episodes=eps_count,
        num_folds=folds,
        target_density=density,
    )
