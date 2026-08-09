"""
ASSUMPTION-VI STUDY (Stage 1) — does a per-agent SYSTEMATIC sensor bias break the temporal filter?

The temporal test assumes honest offsets are ZERO-MEAN. A miscalibrated-but-honest sensor adds a
persistent per-agent offset b_j to EVERY obstacle it senses, so the honest pairwise offset has mean
(b_j - b_i) != 0 -> a naive temporal test could flag an honest neighbour (precision down, no-harm
down). This sweeps the bias magnitude at the headline stress cell (sigma=0.6, camouflage, k traitors)
and reports what happens. sensor_bias is a per-agent CONSTANT offset (metres), fixed per episode.

Arms per bias level: base / off(attack) / temporal / temporal_nh (no-attacker, defense ON).
The decisive columns: temporal NO-HARM (does bias make the defense harm honest swarms?) and
detection PRECISION (does bias cause false accusations of honest neighbours?).

Usage:
  python eval_bias_sweep.py <model> <n_maps> [k] [n_workers] [attack_mode]
  python eval_bias_sweep.py models/noise_robust_ON_stage2_final.zip 500 2 10 camouflage
"""
import os, sys
import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import eval_temporal as ET
from eval_temporal import (_init, _run, resolve_path, _cfg,
                           NOISE_LEVELS, ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU,
                           TEMPORAL_EPS, TEMPORAL_MIN_K)
from boot_ci import diff_ci, pr_ci

BIAS_LEVELS = (0.0, 0.2, 0.4, 0.6)   # per-agent constant offset magnitude (m)
SIGMA_LEVELS = NOISE_LEVELS          # sweep noise too: (0, 0.2, 0.4, 0.6)


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
    for sg in SIGMA_LEVELS:
        for b in BIAS_LEVELS:
            for arm, ntr, defense, temporal in (("base", 0, False, False),
                                                ("off", k, False, False),
                                                ("temporal", k, True, True),
                                                ("nh", 0, True, True)):
                index[(sg, b, arm)] = len(conds)
                conds.append(_cfg(f"s{sg}_b{b}_{arm}", sg, ntr, defense,
                                  ROBUST_K_SIGMA, ROBUST_ALPHA, ROBUST_TAU, attack_mode,
                                  temporal=temporal, eps=TEMPORAL_EPS, min_k=TEMPORAL_MIN_K,
                                  randomize=True, sensor_bias=b))
    tasks = [(ci, mi) for ci in range(len(conds)) for mi in range(n_maps)]

    print(f"\n{'='*100}")
    print(f"SENSOR-BIAS x NOISE SWEEP (assumption vi) | {os.path.basename(model_path)} | {attack_mode} | "
          f"k={k} | {n_maps} maps/cond | {len(conds)} conds | {n_workers}w")
    print(f"  bias(m) in {BIAS_LEVELS} | sigma in {SIGMA_LEVELS} | temporal eps={TEMPORAL_EPS}, min_k={TEMPORAL_MIN_K}")
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

    def raw(sg, b, arm):
        return rates[index[(sg, b, arm)]]

    print(f"\n{'='*100}")
    print(f"RESULTS - temporal defense vs (noise sigma x per-agent bias) ({attack_mode}, k={k})")
    print(f"  recovery = temporal - off ; no-harm = temporal_nh - base ; P/R = detection precision/recall")
    print(f"{'='*100}")
    for sg in SIGMA_LEVELS:
        print(f"\n  --- sigma = {sg:.1f} ---")
        print(f"  bias(m) |   base    off  temporal  temp.nh | recovery  no-harm |   P/R")
        for b in BIAS_LEVELS:
            base = 100.0 * float(np.mean(raw(sg, b, "base")))
            off = 100.0 * float(np.mean(raw(sg, b, "off")))
            tmp = 100.0 * float(np.mean(raw(sg, b, "temporal")))
            nh = 100.0 * float(np.mean(raw(sg, b, "nh")))
            ci = index[(sg, b, "temporal")]
            sTP, sFP, sFN = detTP[ci].sum(), detFP[ci].sum(), detFN[ci].sum()
            P = sTP / (sTP + sFP) if (sTP + sFP) else 0.0
            R = sTP / (sTP + sFN) if (sTP + sFN) else 0.0
            print(f"    {b:.1f}  | {base:5.1f}  {off:5.1f}   {tmp:5.1f}    {nh:5.1f} | "
                  f"  {tmp-off:+5.1f}   {nh-base:+5.1f}  | {P:.2f}/{R:.2f}")

    print(f"\n{'='*100}")
    print(f"95% CONFIDENCE INTERVALS - no-harm (temporal_nh - base) per (sigma, bias) (paired bootstrap)")
    print(f"  -- the decisive column: does bias make the DEFENSE harm honest swarms? --")
    print(f"{'='*100}")
    for sg in SIGMA_LEVELS:
        for b in BIAS_LEVELS:
            nhm, nlo, nhi = diff_ci(raw(sg, b, "nh"), raw(sg, b, "base"))
            ci = index[(sg, b, "temporal")]
            pp, plo, phi, rr, rrlo, rrhi = pr_ci(detTP[ci], detFP[ci], detFN[ci])
            print(f"  sigma={sg:.1f} bias={b:.1f}: no-harm {nhm:+5.1f} [{nlo:+5.1f},{nhi:+5.1f}]pp  "
                  f"det P {pp:.2f}[{plo:.2f},{phi:.2f}] R {rr:.2f}")
    print(f"{'='*100}")
    print("[INTERPRETATION] bias=0 (every sigma) is the paper's unbiased default. As bias grows, IF the")
    print("  zero-mean assumption breaks we expect PRECISION to fall (honest neighbours flagged) and NO-HARM")
    print("  to go negative. If no-harm stays ~0, the own-sensing cushion absorbs the false flags (limitation")
    print("  bounded). Watch the sigma x bias interaction: at low sigma the single-frame tolerance is tight,")
    print("  so bias should bite harder; at high sigma the wide tolerance may mask it. QUANTIFIES assumption (vi).")


if __name__ == "__main__":
    main()
