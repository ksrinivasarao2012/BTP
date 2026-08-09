"""
R3 REALISM STUDY - does the temporal defense survive LOSSY communication?

Reuses eval_temporal's machinery (env builder, worker, model). For each packet-loss level p,
each neighbour's broadcast is independently dropped with probability p per (receiver, sender, step):
a lost packet contributes neither to fusion nor to verification that frame. We sweep p over
{0, 0.1, 0.2, 0.3} at every noise level sigma in {0, 0.2, 0.4, 0.6}, for one attack mode, with
arms {base, off(attack), temporal, temporal_nh}. Recovery = temporal - off; no-harm = temporal_nh - base
(both at the SAME p). The temporal slow path needs ~min_k/(1-p) frames to reach a verdict, still far
below the 1200-step episode for moderate p; this quantifies the graceful degradation.

Usage:
  python eval_comm_loss.py <model> <n_maps> [k] [n_workers] [attack_mode]
  python eval_comm_loss.py models/noise_robust_ON_stage2_final.zip 500 2 10 camouflage
"""
import os, sys
import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# reuse everything heavy from eval_temporal (env builder reads cfg["comm_loss"])
import eval_temporal as ET
from eval_temporal import (_init, _run, resolve_path, _cfg,
                           NOISE_LEVELS, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU,
                           TEMPORAL_EPS, TEMPORAL_MIN_K)
from boot_ci import diff_ci, pr_ci

LOSS_LEVELS = (0.0, 0.1, 0.2, 0.3)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else ET.DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    attack_mode = sys.argv[5] if len(sys.argv) > 5 else "camouflage"
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    # conditions: for each (loss p, noise nz) -> base / off / temporal / temporal_nh
    conds, index = [], {}
    for p in LOSS_LEVELS:
        for nz in NOISE_LEVELS:
            for arm, ntr, defense, temporal in (("base", 0, False, False),
                                                ("off", k, False, False),
                                                ("temporal", k, True, True),
                                                ("nh", 0, True, True)):
                index[(p, nz, arm)] = len(conds)
                conds.append(_cfg(f"p{p}_n{nz}_{arm}", nz, ntr, defense,
                                  ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                                  temporal=temporal, eps=TEMPORAL_EPS, min_k=TEMPORAL_MIN_K,
                                  randomize=True, comm_loss=p))
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*100}")
    print(f"COMM-LOSS SWEEP (R3) | {os.path.basename(model_path)} | {attack_mode} | k={k} | "
          f"{n_maps} maps/cond | {len(conds)} conds | {n_workers}w")
    print(f"  loss p in {LOSS_LEVELS} | noise in {NOISE_LEVELS} | temporal eps={TEMPORAL_EPS}, "
          f"min_k={TEMPORAL_MIN_K}")
    print(f"{'='*100}", flush=True)

    rates = {ci: np.zeros(n_maps, np.float32) for ci in range(len(conds))}
    detTP = {ci: np.zeros(n_maps, np.float32) for ci in range(len(conds))}
    detFP = {ci: np.zeros(n_maps, np.float32) for ci in range(len(conds))}
    detFN = {ci: np.zeros(n_maps, np.float32) for ci in range(len(conds))}
    done, total = 0, len(tasks)
    chunk = max(1, n_maps // n_workers)
    with Pool(n_workers, initializer=_init, initargs=(model_path, conds)) as pool:
        for ci, mi, rate, TP, FP, FN in pool.imap(_run, tasks, chunksize=chunk):
            rates[ci][mi] = rate
            detTP[ci][mi] = TP; detFP[ci][mi] = FP; detFN[ci][mi] = FN
            done += 1
            if done % max(1, total // 20) == 0:
                print(f"  ... {done}/{total} ({100*done/total:.0f}%)", flush=True)

    def raw(p, nz, arm):                 # per-map success array in [0,1]
        return rates[index[(p, nz, arm)]]

    print(f"\n{'='*100}")
    print(f"RESULTS - temporal defense under comm loss ({attack_mode}, k={k})")
    print(f"  recovery = temporal - off ; no-harm = temporal_nh - base (same p) ; R = temporal recall")
    print(f"{'='*100}")
    for p in LOSS_LEVELS:
        print(f"\n  --- packet loss p = {p:.1f} ---")
        print(f"  noise |   base    off  temporal  temp.nh | recovery  no-harm |   R")
        for nz in NOISE_LEVELS:
            base = 100.0 * float(np.mean(raw(p, nz, "base")))
            off = 100.0 * float(np.mean(raw(p, nz, "off")))
            tmp = 100.0 * float(np.mean(raw(p, nz, "temporal")))
            nh = 100.0 * float(np.mean(raw(p, nz, "nh")))
            ci = index[(p, nz, "temporal")]
            sTP, sFN = detTP[ci].sum(), detFN[ci].sum()
            R = sTP / (sTP + sFN) if (sTP + sFN) else 0.0
            print(f"   {nz:.2f} | {base:5.1f}  {off:5.1f}   {tmp:5.1f}    {nh:5.1f} | "
                  f"  {tmp-off:+5.1f}   {nh-base:+5.1f}  | {R:.2f}")

    # CI on the decisive cell: recovery at sigma=0.6 for each p (paired bootstrap over the SAME maps)
    print(f"\n{'='*100}")
    print(f"95% CONFIDENCE INTERVALS - sigma=0.6 recovery vs off, per loss level (paired bootstrap)")
    print(f"{'='*100}")
    for p in LOSS_LEVELS:
        rec, rlo, rhi = diff_ci(raw(p, 0.6, "temporal"), raw(p, 0.6, "off"))     # scale=100 -> pp
        nhm, nlo, nhi = diff_ci(raw(p, 0.6, "nh"), raw(p, 0.6, "base"))
        ci = index[(p, 0.6, "temporal")]
        pp, plo, phi, rr, rrlo, rrhi = pr_ci(detTP[ci], detFP[ci], detFN[ci])
        print(f"  p={p:.1f}: recovery {rec:+5.1f} [{rlo:+5.1f},{rhi:+5.1f}]pp  "
              f"no-harm {nhm:+5.1f} [{nlo:+5.1f},{nhi:+5.1f}]pp  "
              f"det P {pp:.2f} R {rr:.2f}[{rrlo:.2f},{rrhi:.2f}]")
    print(f"{'='*100}")
    print("[INTERPRETATION] Temporal survives loss if sigma=0.6 recovery stays positive (CI>0) as p grows; "
          "graceful if it declines slowly. no-harm should stay ~0 throughout.")


if __name__ == "__main__":
    main()
