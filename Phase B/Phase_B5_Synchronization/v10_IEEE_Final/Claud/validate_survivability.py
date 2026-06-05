import os
import sys
import csv
import random
import numpy as np

# Suppresses MKL/OpenMP duplicate runtime warnings on Windows.
# Required for stable multiprocessing with PyTorch + NumPy stack.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import argparse
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from swarm_env_step_B5_v20_sensing_ablation import SwarmLidarEnv_v20_SensingAblation

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "survivability_validation")

# ==============================================================================
# OPTIMIZATION 1: Lean episode runner — minimal object creation, no redundant
#                 state kept in memory, IPC payload is scalars only.
# ==============================================================================
def run_single_episode(args):
    """
    Unpacks a single tuple so executor.map() can call this with one argument.
    Keeps IPC payload minimal: returns only scalar values, no lists.
    """
    w, h, density, ep_seed, max_steps = args

    env = SwarmLidarEnv_v20_SensingAblation(target_density=density, width=w, height=h)
    env.current_r_sensor = 8.0
    env.current_r_comm   = 10.0

    for space in env.action_spaces.values():
        space.seed(ep_seed)

    try:
        obs, _ = env.reset(seed=ep_seed)

        step_count          = 0
        ep_collisions       = 0
        first_collision_step = None
        agents_reached      = 0
        n_drones            = env.n_drones
        dt                  = env.dt
        cascade_count       = 0
        prev_collision_step = None   # track last collision step for cascade check

        # OPTIMIZATION 2: cache action_spaces lookup outside inner loop
        action_spaces = env.action_spaces

        while env.agents and step_count < max_steps:
            actions = {a: action_spaces[a].sample() for a in env.agents}
            obs, rewards, terminations, truncations, infos = env.step(actions)
            step_count += 1

            for agent, info in infos.items():
                done = terminations.get(agent, False) or truncations.get(agent, False)
                if not done:
                    continue
                cause = info.get('cause')
                if cause == 'collision':
                    ep_collisions += 1
                    if first_collision_step is None:
                        first_collision_step = step_count
                    # cascade: collision within 20 steps of the previous one
                    if prev_collision_step is not None and (step_count - prev_collision_step) <= 20:
                        cascade_count += 1
                    prev_collision_step = step_count
                elif cause == 'success':
                    agents_reached += 1

        instant_death = (
            first_collision_step is not None
            and first_collision_step * dt <= 1.0
        )

        return (
            step_count,                                          # 0
            ep_collisions,                                       # 1
            first_collision_step,                                # 2
            agents_reached,                                      # 3
            cascade_count,                                       # 4
            n_drones,                                            # 5
            int(step_count >= max_steps and bool(env.agents)),   # 6  is_timeout
            int(instant_death),                                  # 7
        )
    finally:
        env.close()


# ==============================================================================
# OPTIMIZATION 3: Bootstrap CI — vectorised, no Python loop
# ==============================================================================
def compute_bootstrap_ci(data, num_samples=1000, ci=95):
    if len(data) < 2:
        return 0.0
    data = np.asarray(data, dtype=np.float64)
    idx  = np.random.randint(0, len(data), (num_samples, len(data)))
    means = data[idx].mean(axis=1)
    lo = np.percentile(means, (100 - ci) / 2)
    hi = np.percentile(means, 100 - (100 - ci) / 2)
    return (hi - lo) / 2   # symmetric ± margin; fine for benchmarking


# ==============================================================================
# OPTIMIZATION 4: Build the full job list up-front, dispatch in ONE pool,
#                 reuse workers across all regimes — no repeated pool creation.
# ==============================================================================
class SurvivabilityValidator:
    def __init__(
        self,
        dimensions=[(30.0, 30.0), (40.0, 40.0)],
        densities=[0.20, 0.30, 0.35],
        episodes_per_regime=20,
        seeds=[42],
        workers=None,
        max_steps=800,
    ):
        self.dimensions         = dimensions
        self.densities          = densities
        self.episodes_per_regime = episodes_per_regime
        self.seeds              = seeds
        # OPTIMIZATION 5: default to all-but-one core automatically
        self.workers            = workers or max(1, (os.cpu_count() or 2) - 1)
        self.max_steps          = max_steps

    # ------------------------------------------------------------------
    def _build_job_list(self):
        """
        Returns a flat list of (job_args, regime_key) pairs, one per episode.
        Seeds are generated deterministically but are uncorrelated across episodes
        via SeedSequence so episodes don't share RNG state.
        """
        jobs = []
        for w, h in self.dimensions:
            for density in self.densities:
                regime_key = f"{int(w)}x{int(h)} D={density:.2f}"
                for macro_seed in self.seeds:
                    seed_seq = np.random.SeedSequence(macro_seed)
                    ep_seeds = seed_seq.generate_state(self.episodes_per_regime)
                    for ep_seed in ep_seeds:
                        jobs.append(
                            ((w, h, density, int(ep_seed), self.max_steps), regime_key)
                        )
        return jobs

    # ------------------------------------------------------------------
    def run_validation(self):
        print("\n=========================================================")
        print("       STAGE 2: RANDOM POLICY SURVIVABILITY (OPTIMIZED)  ")
        print(f"  Seeds: {self.seeds} | Eps/seed: {self.episodes_per_regime} | Workers: {self.workers}")
        print(f"  Max steps/episode: {self.max_steps}")
        print("=========================================================\n")

        # ---- initialise empty stats containers for every regime --------
        regime_stats = {}
        for w, h in self.dimensions:
            for density in self.densities:
                key = f"{int(w)}x{int(h)} D={density:.2f}"
                regime_stats[key] = self._empty_stats(f"{int(w)}x{int(h)}", density)

        # ---- build flat job list & dispatch all at once -----------------
        jobs = self._build_job_list()
        total = len(jobs)
        print(f"  Total episodes to run: {total}\n")

        # OPTIMIZATION 6: one persistent pool; map() keeps workers busy
        # without any IPC round-trip per chunk boundary.
        with ProcessPoolExecutor(max_workers=self.workers) as pool:
            args_list   = [j[0] for j in jobs]
            regime_keys = [j[1] for j in jobs]

            # imap-style: results stream back as they complete
            for regime_key, result in tqdm(
                zip(regime_keys, pool.map(run_single_episode, args_list, chunksize=4)),
                total=total,
                desc="Episodes",
                unit="ep",
                dynamic_ncols=True,
            ):
                self._aggregate(regime_stats[regime_key], result)

        self._print_report(regime_stats)
        self._save_csv(regime_stats)
        self._generate_plots(regime_stats)

    # ------------------------------------------------------------------
    @staticmethod
    def _empty_stats(dimension, density):
        return {
            "dimension":            dimension,
            "density":              density,
            "survival_steps":       [],
            "collisions_per_ep":    [],
            "cascade_counts":       [],
            "throughput":           0,
            "total_agents_seen":    0,
            "collision_timings":    [],
            "raw_ttcs":             [],
            "instant_death_eps":    0,
            "timeout_freq":         0,
            "survival_fractions":   [],
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _aggregate(stats, res):
        (step_count, ep_collisions, first_collision_step,
         agents_reached, cascade_count, n_drones,
         is_timeout, instant_death) = res

        stats["survival_steps"].append(step_count)
        stats["collisions_per_ep"].append(ep_collisions)
        stats["cascade_counts"].append(cascade_count)
        stats["throughput"]        += agents_reached
        stats["total_agents_seen"] += n_drones
        stats["raw_ttcs"].append(first_collision_step)
        stats["survival_fractions"].append(
            agents_reached / n_drones if n_drones > 0 else 0.0
        )
        if first_collision_step is not None:
            stats["collision_timings"].append(first_collision_step)
        stats["instant_death_eps"] += instant_death
        stats["timeout_freq"]      += is_timeout

    # ------------------------------------------------------------------
    def _compute_metrics(self, stats):
        dur = np.array(stats["survival_steps"],    dtype=float)
        ttc = np.array(stats["collision_timings"], dtype=float) if stats["collision_timings"] else np.array([])
        col = np.array(stats["collisions_per_ep"], dtype=float)
        cas = np.array(stats["cascade_counts"],    dtype=float)
        n   = len(dur)

        return {
            "mean_duration":    np.mean(dur),
            "bs_ci_duration":   compute_bootstrap_ci(dur),
            "p05_duration":     np.percentile(dur, 5),
            "p95_duration":     np.percentile(dur, 95),

            "mean_ttc":         np.mean(ttc) if len(ttc) else float('inf'),
            "bs_ci_ttc":        compute_bootstrap_ci(ttc) if len(ttc) else float('nan'),
            "p05_ttc":          np.percentile(ttc, 5) if len(ttc) else float('nan'),

            "inst_death_pct":   stats["instant_death_eps"] / n * 100,
            "throughput_pct":   stats["throughput"] / max(1, stats["total_agents_seen"]) * 100,

            "mean_collisions":  np.mean(col),
            "bs_ci_collisions": compute_bootstrap_ci(col),

            "mean_cascades":    np.mean(cas),
            "timeouts":         stats["timeout_freq"],
            "total_episodes":   n,
        }

    # ------------------------------------------------------------------
    def _print_report(self, results):
        W = 155
        print("\n" + "=" * W)
        print("                       RANDOM POLICY SURVIVABILITY METRICS  (OPTIMIZED)")
        print(f"                       Seeds: {self.seeds} | Episodes/Seed: {self.episodes_per_regime} | Max Steps: {self.max_steps}")
        print("=" * W)
        hdr = (f"{'Regime':<15} | {'Ep.Dur (Mean±CI)':<18} | {'TTC (Mean±CI)':<16} | "
               f"{'TTC p5':<8} | {'Inst.Death%':<12} | {'Throughput':<11} | "
               f"{'Coll/Ep (Mean±CI)':<19} | {'Cascades':<10} | {'Timeouts':<8} | {'N':<5}")
        print(hdr)
        print("-" * W)

        for regime, stats in results.items():
            m = self._compute_metrics(stats)
            dur_str  = f"{m['mean_duration']:.0f}±{m['bs_ci_duration']:.0f}"
            ttc_str  = f"{m['mean_ttc']:.1f}±{m['bs_ci_ttc']:.1f}" if m['mean_ttc'] != float('inf') else "N/A"
            ttc_p5   = f"{m['p05_ttc']:.0f}" if not np.isnan(m['p05_ttc']) else "N/A"
            col_str  = f"{m['mean_collisions']:.1f}±{m['bs_ci_collisions']:.1f}"

            print(
                f"{regime:<15} | {dur_str:<18} | {ttc_str:<16} | {ttc_p5:<8} | "
                f"{m['inst_death_pct']:<11.1f}% | {m['throughput_pct']:<9.1f}% | "
                f"{col_str:<19} | {m['mean_cascades']:<10.1f} | {m['timeouts']:<8} | {m['total_episodes']:<5}"
            )

        print("\n[Legend]")
        print("  Ep.Dur      = Steps before episode ends (Bootstrap 95% CI)")
        print("  TTC         = Step of first collision   (Bootstrap 95% CI)")
        print("  Inst.Death% = Episodes with collision within 1.0 s of start")
        print("  Throughput  = Fraction of drones that reached the goal")
        print("  Coll/Ep     = Collisions per episode    (Bootstrap 95% CI)")
        print("  Cascades    = Collisions within 20 steps of prior collision")
        print("  N           = Total episodes completed")

    # ------------------------------------------------------------------
    def _save_csv(self, results):
        os.makedirs(RESULTS_DIR, exist_ok=True)

        summary_path = os.path.join(RESULTS_DIR, "survivability_results.csv")
        fieldnames = [
            "Dimension", "Density", "Total_Episodes",
            "Mean_Episode_Duration", "BS_CI_Duration", "P05_Duration", "P95_Duration",
            "Mean_TTC", "BS_CI_TTC", "P05_TTC",
            "Instant_Death_Percent", "Throughput_Percent",
            "Collisions_Per_Episode", "BS_CI_Collisions",
            "Mean_Cascades", "Timeout_Count",
        ]
        with open(summary_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for regime, stats in results.items():
                m = self._compute_metrics(stats)
                writer.writerow({
                    "Dimension":              stats["dimension"],
                    "Density":                stats["density"],
                    "Total_Episodes":         m["total_episodes"],
                    "Mean_Episode_Duration":  f"{m['mean_duration']:.1f}",
                    "BS_CI_Duration":         f"{m['bs_ci_duration']:.1f}",
                    "P05_Duration":           f"{m['p05_duration']:.1f}",
                    "P95_Duration":           f"{m['p95_duration']:.1f}",
                    "Mean_TTC":               f"{m['mean_ttc']:.1f}" if m['mean_ttc'] != float('inf') else "N/A",
                    "BS_CI_TTC":              f"{m['bs_ci_ttc']:.1f}" if not np.isnan(m['bs_ci_ttc']) else "N/A",
                    "P05_TTC":                f"{m['p05_ttc']:.1f}" if not np.isnan(m['p05_ttc']) else "N/A",
                    "Instant_Death_Percent":  f"{m['inst_death_pct']:.1f}",
                    "Throughput_Percent":     f"{m['throughput_pct']:.1f}",
                    "Collisions_Per_Episode": f"{m['mean_collisions']:.1f}",
                    "BS_CI_Collisions":       f"{m['bs_ci_collisions']:.1f}",
                    "Mean_Cascades":          f"{m['mean_cascades']:.1f}",
                    "Timeout_Count":          m["timeouts"],
                })

        raw_path = os.path.join(RESULTS_DIR, "survivability_raw_episodes.csv")
        raw_fields = ["Dimension", "Density", "Episode_Index", "Duration",
                      "First_Collision_Step", "Total_Collisions", "Cascades"]
        with open(raw_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=raw_fields)
            writer.writeheader()
            for regime, stats in results.items():
                for i, dur in enumerate(stats["survival_steps"]):
                    writer.writerow({
                        "Dimension":           stats["dimension"],
                        "Density":             stats["density"],
                        "Episode_Index":       i + 1,
                        "Duration":            dur,
                        "First_Collision_Step": stats["raw_ttcs"][i] if stats["raw_ttcs"][i] is not None else "N/A",
                        "Total_Collisions":    stats["collisions_per_ep"][i],
                        "Cascades":            stats["cascade_counts"][i],
                    })

        print(f"\n  Results saved to {RESULTS_DIR}")

    # ------------------------------------------------------------------
    def _generate_plots(self, results):
        os.makedirs(RESULTS_DIR, exist_ok=True)

        dim_groups = {}
        for regime, stats in results.items():
            dim = stats["dimension"]
            if dim not in dim_groups:
                dim_groups[dim] = {"densities": [], "metrics": []}
            dim_groups[dim]["densities"].append(stats["density"])
            dim_groups[dim]["metrics"].append(self._compute_metrics(stats))

        # FIX: sort by density to prevent zig-zag lines
        for dim in dim_groups:
            pairs = sorted(zip(dim_groups[dim]["densities"], dim_groups[dim]["metrics"]), key=lambda x: x[0])
            dim_groups[dim]["densities"] = [p[0] for p in pairs]
            dim_groups[dim]["metrics"]   = [p[1] for p in pairs]

        colors  = {"30x30": "#2196F3", "40x40": "#FF5722"}
        markers = {"30x30": "o",       "40x40": "s"}

        def _plot(ax, y_key, err_key, ylabel, title, nan_val=None):
            for dim, group in dim_groups.items():
                ys   = [m[y_key]   if (nan_val is None or m[y_key] != nan_val) else np.nan for m in group["metrics"]]
                errs = [m[err_key] if not np.isnan(m[err_key]) else 0                      for m in group["metrics"]]
                ax.errorbar(group["densities"], ys, yerr=errs,
                            label=dim, marker=markers.get(dim, "o"),
                            color=colors.get(dim, "gray"),
                            capsize=4, linewidth=1.5, markersize=6)
            ax.set_xlabel("Obstacle Density", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_title(title, fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)

        for fname, y_key, err_key, ylabel, title, nan_val in [
            ("ttc_vs_density.png",        "mean_ttc",        "bs_ci_ttc",        "Mean TTC (steps)",      "TTC vs Density (Bootstrap CI)",        float('inf')),
            ("collisions_vs_density.png", "mean_collisions", "bs_ci_collisions", "Collisions per Episode", "Collision Rate vs Density (Bootstrap CI)", None),
        ]:
            fig, ax = plt.subplots(figsize=(6, 4))
            _plot(ax, y_key, err_key, ylabel, title, nan_val)
            fig.tight_layout()
            fig.savefig(os.path.join(RESULTS_DIR, fname), dpi=150)
            plt.close(fig)


# ==============================================================================
# Entry point
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 2: Random Policy Survivability Validation (Optimized)")
    parser.add_argument("--episodes",  type=int,           default=50,
                        help="Episodes per regime per seed")
    parser.add_argument("--workers",   type=int,           default=None,
                        help="Parallel workers (default: cpu_count - 1)")
    parser.add_argument("--seeds",     type=int, nargs="+", default=[42],
                        help="Macro random seeds")
    parser.add_argument("--max_steps", type=int,           default=800,
                        help="Max steps per episode")
    args = parser.parse_args()

    validator = SurvivabilityValidator(
        dimensions=[(30.0, 30.0), (40.0, 40.0)],
        densities=[0.20, 0.25, 0.30, 0.35],
        episodes_per_regime=args.episodes,
        seeds=args.seeds,
        workers=args.workers,
        max_steps=args.max_steps,
    )
    validator.run_validation()
