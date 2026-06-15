"""
Honest verification from Stage 1 data — answers two questions:
  1. For clustered, is the best config og=1.5/osc=1.5 or og=1.5/osc=2.0?
  2. Do clustered and scattered want the SAME env config or different ones?

Env config = (og, osc, sp, sc_g, bfs). The two free spawn params
(goal_spawn_clearance, inter_drone_min) do not affect BFS feasibility, so
pct_all10_ok is averaged over them (3x3 = 9 rows -> 450 maps per env config
per density) for a robust survey signal.

Ceiling = highest density where averaged pct_all10_ok >= 90%.
"""

import pandas as pd
import numpy as np

CSV = "density_sweep_v5_results_20260608_153206.csv"
ENV_KEYS = ['obs_goal_clearance', 'obs_sc_clearance', 'spawn_obstacle_clearance',
            'sc_goal_min_dist', 'bfs_clearance']

df = pd.read_csv(CSV)
df = df[df['stage'].astype(str) == '1'].copy()
for c in ENV_KEYS + ['goal_spawn_clearance', 'inter_drone_min', 'density', 'pct_all10_ok']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

DENSITIES = sorted(df['density'].unique())


def build_table(mode):
    d = df[df['spawn_mode'] == mode]
    # average pct over free params (gc, inter)
    g = (d.groupby(ENV_KEYS + ['density'])['pct_all10_ok']
           .mean().reset_index())
    piv = g.pivot_table(index=ENV_KEYS, columns='density',
                        values='pct_all10_ok')

    def ceiling(row):
        c = None
        for dd in DENSITIES:
            if dd in row.index and row[dd] >= 90.0:
                c = dd
            else:
                break
        return c

    piv['ceiling'] = piv.apply(ceiling, axis=1)
    piv['pct@ceil'] = piv.apply(
        lambda r: r[r['ceiling']] if pd.notna(r['ceiling']) else np.nan, axis=1)
    piv = piv.reset_index().sort_values(
        ['ceiling', 'pct@ceil'], ascending=False, na_position='last')
    return piv


def show_top(piv, mode, n=15):
    print(f"\n{'='*100}")
    print(f"TOP {n} ENV CONFIGS — {mode.upper()}  (pct averaged over gc, inter; ceiling = last density >=90%)")
    print(f"{'='*100}")
    hdr = (f"{'og':>4} {'osc':>4} {'sp':>5} {'sc_g':>5} {'bfs':>5} | "
           + " ".join(f"d{d:.2f}".rjust(7) for d in DENSITIES)
           + f" | {'CEIL':>5} {'pct@c':>7}")
    print(hdr)
    print("-" * len(hdr))
    for _, r in piv.head(n).iterrows():
        cells = " ".join(f"{r[d]:6.1f}" if pd.notna(r[d]) else "    --" for d in DENSITIES)
        ceil = f"{r['ceiling']:.2f}" if pd.notna(r['ceiling']) else "NONE"
        pc = f"{r['pct@ceil']:.1f}" if pd.notna(r['pct@ceil']) else "--"
        print(f"{r['obs_goal_clearance']:>4} {r['obs_sc_clearance']:>4} "
              f"{r['spawn_obstacle_clearance']:>5} {r['sc_goal_min_dist']:>5} "
              f"{r['bfs_clearance']:>5} | {cells} | {ceil:>5} {pc:>7}")


def osc_head_to_head(piv, mode):
    """For og=1.5, same (sp, sc_g, bfs), compare osc=1.5 vs 2.0 vs 2.5 directly."""
    print(f"\n{'-'*100}")
    print(f"OSC HEAD-TO-HEAD — {mode.upper()}, og=1.5 only (does osc=1.5 beat osc=2.0?)")
    print(f"{'-'*100}")
    sub = piv[piv['obs_goal_clearance'] == 1.5]
    # pivot mean pct@0.30 and ceiling by osc
    for osc in sorted(sub['obs_sc_clearance'].unique()):
        s = sub[sub['obs_sc_clearance'] == osc]
        mean_ceil = s['ceiling'].mean()
        # fraction hitting each ceiling
        n_030 = (s['ceiling'] == 0.30).sum()
        n_025 = (s['ceiling'] == 0.25).sum()
        mean_d30 = s[0.30].mean()
        mean_d35 = s[0.35].mean()
        print(f"  osc={osc}: mean_ceiling={mean_ceil:.3f} | "
              f"#ceil0.30={n_030:2d} #ceil0.25={n_025:2d} | "
              f"avg pct@0.30={mean_d30:5.1f}%  avg pct@0.35={mean_d35:5.1f}%  "
              f"(n={len(s)} configs)")


def cross_mode(pc, ps):
    """Can ONE env config serve both modes? Match on ENV_KEYS."""
    print(f"\n{'='*100}")
    print("CROSS-MODE — same env config, ceiling under each spawn mode")
    print("(scattered is the harder mode; a config good for scattered should be good for clustered too)")
    print(f"{'='*100}")
    m = pc.merge(ps, on=ENV_KEYS, suffixes=('_clus', '_scat'))

    # Best clustered config — how does it do scattered?
    bc = pc.iloc[0]
    bc_row = m[(m['obs_goal_clearance'] == bc['obs_goal_clearance']) &
               (m['obs_sc_clearance'] == bc['obs_sc_clearance']) &
               (m['spawn_obstacle_clearance'] == bc['spawn_obstacle_clearance']) &
               (m['sc_goal_min_dist'] == bc['sc_goal_min_dist']) &
               (m['bfs_clearance'] == bc['bfs_clearance'])]

    # Best scattered config — how does it do clustered?
    bs = ps.iloc[0]
    bs_row = m[(m['obs_goal_clearance'] == bs['obs_goal_clearance']) &
               (m['obs_sc_clearance'] == bs['obs_sc_clearance']) &
               (m['spawn_obstacle_clearance'] == bs['spawn_obstacle_clearance']) &
               (m['sc_goal_min_dist'] == bs['sc_goal_min_dist']) &
               (m['bfs_clearance'] == bs['bfs_clearance'])]

    def fmt(row, key):
        if len(row) == 0:
            return "not found"
        r = row.iloc[0]
        cc = f"{r['ceiling_clus']:.2f}" if pd.notna(r['ceiling_clus']) else "NONE"
        cs = f"{r['ceiling_scat']:.2f}" if pd.notna(r['ceiling_scat']) else "NONE"
        return (f"clustered ceiling={cc} (pct@c={r['pct@ceil_clus']:.1f}%) | "
                f"scattered ceiling={cs} (pct@c={r['pct@ceil_scat']:.1f}%)")

    print(f"\n  Best CLUSTERED config: og={bc['obs_goal_clearance']} osc={bc['obs_sc_clearance']} "
          f"sp={bc['spawn_obstacle_clearance']} sc_g={bc['sc_goal_min_dist']} bfs={bc['bfs_clearance']}")
    print(f"    -> {fmt(bc_row, bc)}")
    print(f"\n  Best SCATTERED config: og={bs['obs_goal_clearance']} osc={bs['obs_sc_clearance']} "
          f"sp={bs['spawn_obstacle_clearance']} sc_g={bs['sc_goal_min_dist']} bfs={bs['bfs_clearance']}")
    print(f"    -> {fmt(bs_row, bs)}")

    # Find a single shared config: best scattered pct@0.25 that also has clustered ceiling>=0.30
    print(f"\n  --- SINGLE SHARED CONFIG candidates (scattered ceiling>=0.25 AND clustered ceiling>=0.30) ---")
    shared = m[(m['ceiling_scat'] >= 0.25) & (m['ceiling_clus'] >= 0.30)].copy()
    shared = shared.sort_values(['pct@ceil_scat', 'pct@ceil_clus'], ascending=False)
    if len(shared) == 0:
        print("    NONE — modes require different configs.")
    else:
        print(f"    {len(shared)} configs work for both. Top 8:")
        hdr = (f"    {'og':>4} {'osc':>4} {'sp':>5} {'sc_g':>5} {'bfs':>5} | "
               f"{'clus_ceil':>9} {'clus_pct':>8} | {'scat_ceil':>9} {'scat_pct':>8}")
        print(hdr)
        for _, r in shared.head(8).iterrows():
            print(f"    {r['obs_goal_clearance']:>4} {r['obs_sc_clearance']:>4} "
                  f"{r['spawn_obstacle_clearance']:>5} {r['sc_goal_min_dist']:>5} "
                  f"{r['bfs_clearance']:>5} | {r['ceiling_clus']:>9.2f} {r['pct@ceil_clus']:>7.1f}% | "
                  f"{r['ceiling_scat']:>9.2f} {r['pct@ceil_scat']:>7.1f}%")


pc = build_table('clustered')
ps = build_table('scattered')
show_top(pc, 'clustered')
show_top(ps, 'scattered')
osc_head_to_head(pc, 'clustered')
osc_head_to_head(ps, 'scattered')
cross_mode(pc, ps)
print()
