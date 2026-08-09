"""
R7 GENERALIZATION STUDY - does the temporal defense hold at other obstacle densities?

The whole camera-ready study is at density 0.27. This sweeps density in {0.20, 0.24, 0.27, 0.30}
(same 10-drone model, NO retraining) at the headline stress cell: sigma=0.6, camouflage, k traitors,
arms {base, off, temporal, temporal_nh}. Confirms the security result is not an artifact of one density.

Usage:
  python eval_density_sweep.py <model> <n_maps> [k] [n_workers] [attack_mode]
  python eval_density_sweep.py models/noise_robust_ON_stage2_final.zip 500 2 10 camouflage
"""
import os, sys
import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import eval_temporal as ET
from eval_temporal import (_init, _run, resolve_path, _cfg,
                           ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, TEMPORAL_EPS, TEMPORAL_MIN_K)
from boot_ci import diff_ci, pr_ci

DENSITIES = (0.20, 0.24, 0.27, 0.30)
SIGMA = 0.6                      # headline stress level


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else ET.DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    attack_mode = sys.argv[5] if len(sys.argv) > 5 else "camouflage"
    model_path = resolve_path(model_path)
    if model_path is None:
        print("[!] model not found"); return

    conds, index = [], {}
    for d in DENSITIES:
        for arm, ntr, defense, temporal in (("base", 0, False, False),
                                            ("off", k, False, False),
                                            ("temporal", k, True, True),
                                            ("nh", 0, True, True)):
            index[(d, arm)] = len(conds)
            conds.append(_cfg(f"d{d}_{arm}", SIGMA, ntr, defense,
                              ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                              temporal=temporal, eps=TEMPORAL_EPS, min_k=TEMPORAL_MIN_K,
                              randomize=True, density=d))
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*100}")
    print(f"DENSITY SWEEP (R7) | {os.path.basename(model_path)} | {attack_mode} | k={k} | sigma={SIGMA} | "
          f"{n_maps} maps/cond | {len(conds)} conds | {n_workers}w")
    print(f"  densities {DENSITIES} | temporal eps={TEMPORAL_EPS}, min_k={TEMPORAL_MIN_K}")
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

    def raw(d, arm):
        return rates[index[(d, arm)]]

    print(f"\n{'='*100}")
    print(f"RESULTS - temporal defense vs obstacle density (sigma={SIGMA}, {attack_mode}, k={k})")
    print(f"{'='*100}")
    print(f"  density |   base    off  temporal  temp.nh | recovery  no-harm |   P/R")
    for d in DENSITIES:
        base = 100.0 * float(np.mean(raw(d, "base")))
        off = 100.0 * float(np.mean(raw(d, "off")))
        tmp = 100.0 * float(np.mean(raw(d, "temporal")))
        nh = 100.0 * float(np.mean(raw(d, "nh")))
        ci = index[(d, "temporal")]
        sTP, sFP, sFN = detTP[ci].sum(), detFP[ci].sum(), detFN[ci].sum()
        P = sTP / (sTP + sFP) if (sTP + sFP) else 0.0
        R = sTP / (sTP + sFN) if (sTP + sFN) else 0.0
        print(f"    {d:.2f} | {base:5.1f}  {off:5.1f}   {tmp:5.1f}    {nh:5.1f} | "
              f"  {tmp-off:+5.1f}   {nh-base:+5.1f}  | {P:.2f}/{R:.2f}")

    print(f"\n{'='*100}")
    print(f"95% CONFIDENCE INTERVALS - recovery & no-harm per density (paired bootstrap)")
    print(f"{'='*100}")
    for d in DENSITIES:
        rec, rlo, rhi = diff_ci(raw(d, "temporal"), raw(d, "off"))
        nhm, nlo, nhi = diff_ci(raw(d, "nh"), raw(d, "base"))
        ci = index[(d, "temporal")]
        pp, plo, phi, rr, rrlo, rrhi = pr_ci(detTP[ci], detFP[ci], detFN[ci])
        print(f"  d={d:.2f}: recovery {rec:+5.1f} [{rlo:+5.1f},{rhi:+5.1f}]pp  "
              f"no-harm {nhm:+5.1f} [{nlo:+5.1f},{nhi:+5.1f}]pp  "
              f"det P {pp:.2f} R {rr:.2f}[{rrlo:.2f},{rrhi:.2f}]")
    print(f"{'='*100}")
    print("[INTERPRETATION] Generalizes if recovery stays positive (CI>0) and no-harm ~0 across densities.")


if __name__ == "__main__":
    main()
