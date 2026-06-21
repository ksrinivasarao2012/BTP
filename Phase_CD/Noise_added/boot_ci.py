"""
Paired-bootstrap 95% confidence intervals over the per-map result vectors.

Every eval stores per-map arrays (success rate, and per-map TP/FP/FN). These helpers resample MAP INDICES
(with replacement) to produce CIs that respect map-level correlation, and — for differences — resample the
SAME indices across both conditions so the comparison is PAIRED (the same maps are compared each resample).
A fixed default seed makes the CIs reproducible.

  mean_ci(x)            -> (mean, lo, hi)   single condition's success (scale=100 -> percent)
  diff_ci(a, b)         -> (mean, lo, hi)   PAIRED a-b (e.g. recovery = temporal - off, no-harm = nh - base)
  pr_ci(tp, fp, fn)     -> (P, Plo, Phi, R, Rlo, Rhi)  detection precision/recall, bootstrap over maps
"""
import numpy as np

_N_BOOT = 2000
_SEED = 12345
_ALPHA = (2.5, 97.5)   # 95% CI


def mean_ci(x, n_boot=_N_BOOT, seed=_SEED, scale=100.0):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    bs = x[idx].mean(axis=1) * scale
    lo, hi = np.percentile(bs, _ALPHA)
    return float(x.mean() * scale), float(lo), float(hi)


def diff_ci(a, b, n_boot=_N_BOOT, seed=_SEED, scale=100.0):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    n = len(a)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))          # SAME indices for a and b -> paired
    bs = (a[idx].mean(axis=1) - b[idx].mean(axis=1)) * scale
    lo, hi = np.percentile(bs, _ALPHA)
    return float((a.mean() - b.mean()) * scale), float(lo), float(hi)


def pr_ci(tp, fp, fn, n_boot=_N_BOOT, seed=_SEED):
    tp = np.asarray(tp, dtype=float); fp = np.asarray(fp, dtype=float); fn = np.asarray(fn, dtype=float)
    n = len(tp)
    sTP, sFP, sFN = tp.sum(), fp.sum(), fn.sum()
    p_pt = sTP / (sTP + sFP) if (sTP + sFP) > 0 else 0.0
    r_pt = sTP / (sTP + sFN) if (sTP + sFN) > 0 else 0.0
    if n == 0:
        return p_pt, float("nan"), float("nan"), r_pt, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    TP = tp[idx].sum(axis=1); FP = fp[idx].sum(axis=1); FN = fn[idx].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        P = np.where((TP + FP) > 0, TP / (TP + FP), 0.0)
        R = np.where((TP + FN) > 0, TP / (TP + FN), 0.0)
    Plo, Phi = np.percentile(P, _ALPHA)
    Rlo, Rhi = np.percentile(R, _ALPHA)
    return p_pt, float(Plo), float(Phi), r_pt, float(Rlo), float(Rhi)
