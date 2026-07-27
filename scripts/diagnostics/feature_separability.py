#!/usr/bin/env python3
"""
feature_separability.py — measure which platform features separate the classes, and recommend a
concrete enable-set (full platform names) for the Nordic Edge AI Lab UI.

Read-only and DETERMINISTIC: identical input -> identical output (no RNG, no sampling; all class /
feature / pair iteration is in sorted/fixed order; reported numbers are rounded). The platform extracts
and selects features itself — this is an *indicative* guide (there is no documented separability cutoff),
run on the centered/prepared training CSV.

Usage:
    # profile-driven (preferred — reads label/sensor columns and the class-name map):
    python3 feature_separability.py train.csv --profile profile.json [--window 100] [--json]
    # explicit:
    python3 feature_separability.py train.csv --label-col class \
        --sensor-cols acc_x acc_y acc_z gyro_x gyro_y gyro_z --window 100

Method (numpy + pandas only): window each class non-overlapping (shift = window), compute the platform
time-domain catalogue per axis, z-score globally, then rank by multiclass ANOVA F + per-class
one-vs-rest, and for EVERY class pair compute the best *magnitude-only* Cohen's d — pairs magnitude
cannot separate (best d < --magnitude-blind-d) are direction problems. Maps the evidence to platform
feature families and prints a recommended enable-set with the current hold-backs
(see wiki/principles/domain.md P-12 / P-02, wiki/architecture/platform-feature-extraction.md).
"""
import argparse
import json
import sys

import numpy as np
import pandas as pd

# Windows consoles/pipes default to cp1252, which cannot encode every character in
# this tool's output; degrade to '?' instead of crashing (no-op on UTF-8 terminals).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass

MIN_WINDOWS = 3          # need at least this many windows for a class to enter the analysis
EPS = 1e-9

# (key, platform UI name, family). ORDER IS FIXED — determinism + per-axis indexing depend on it.
FEATURES = [
    ("min",          "Min",                              "Level"),
    ("max",          "Max",                              "Level"),
    ("range",        "Range",                            "Energy"),
    ("mean",         "Mean",                             "Level"),
    ("absmean",      "Absolute Mean",                    "Energy"),
    ("std",          "Standard Deviation",               "Energy"),
    ("mad",          "Mean Absolute Deviation",          "Energy"),
    ("rms",          "Root Mean Square",                 "Energy"),
    ("kurtosis",     "Kurtosis",                         "Shape"),
    ("skew",         "Skewness",                         "Shape"),
    ("lr_slope",     "Linear Regression Slope",          "Direction"),
    ("lr_intercept", "Linear Regression Intercept",      "Level"),
    ("zcr",          "Zero-crossing Rate",               "Crossing"),
    ("mcr",          "Mean-crossing Rate",               "Crossing"),
    ("crest",        "Crest Factor",                     "Impulse/Shape"),
    ("rds",          "Root Difference Square",           "Variation"),
    ("amdf",         "Average Magnitude Difference",     "Variation"),
    ("psom",         "Percentage of Signal over Mean",   "Variation/Signed"),
    ("psoz",         "Percentage of Signal over Zero",   "Variation/Signed"),
    ("hjorth_mob",   "Hjorth Mobility",                  "Impulse/Shape"),
    ("hjorth_comp",  "Hjorth Complexity",                "Impulse/Shape"),
    ("autocorr1",    "Autocorrelation",                  "Autocorrelation"),
]
FKEYS = [f[0] for f in FEATURES]
FNAME = {f[0]: f[1] for f in FEATURES}
FFAM = {f[0]: f[2] for f in FEATURES}
NF = len(FEATURES)

MAGNITUDE_KEYS = ("std", "rms", "range", "mad", "absmean")
IMPULSE_KEYS = ("crest", "hjorth_mob", "hjorth_comp")  # impulse/shape trigger (Skewness/Kurtosis excluded)
# Families with no group in build_recommendation until a class's top one-vs-rest discriminator lands
# in them. Making these reachable is databuilder-015 D2a-3; every FFAM family is now reachable.
TRIGGERABLE_FAMILIES = ("Crossing", "Variation", "Autocorrelation")


def window_features(arr, win):
    """arr: (n, n_axes) float. Return (n_windows, n_axes*NF) feature matrix; non-overlapping windows."""
    n_axes = arr.shape[1]
    n_win = len(arr) // win
    if n_win == 0:
        return np.empty((0, n_axes * NF))
    out = np.empty((n_win, n_axes * NF), dtype=np.float64)
    t = np.arange(win, dtype=np.float64)
    tc = t - t.mean()
    vt = float((tc ** 2).sum())
    for wi in range(n_win):
        block = arr[wi * win:(wi + 1) * win].astype(np.float64)
        for ai in range(n_axes):
            x = block[:, ai]
            m = float(x.mean())
            s = float(x.std())
            sd = s if s > EPS else 1.0
            d = np.diff(x)
            rms = float(np.sqrt((x ** 2).mean()))
            mn, mx = float(x.min()), float(x.max())
            kurt = float((((x - m) / sd) ** 4).mean() - 3.0)
            skew = float((((x - m) / sd) ** 3).mean())
            slope = float((tc * x).sum() / vt) if vt > EPS else 0.0
            intercept = m - slope * float(t.mean())
            zcr = float((np.diff(np.sign(x)) != 0).sum()) / win
            mcr = float((np.diff(np.sign(x - m)) != 0).sum()) / win
            crest = float(np.abs(x).max() / rms) if rms > EPS else 0.0
            rds = float(np.sqrt((d ** 2).mean())) if d.size else 0.0
            amdf = float(np.abs(d).mean()) if d.size else 0.0
            psom = float((x > m).mean())
            psoz = float((x > 0).mean())
            vx = float(x.var())
            vd = float(d.var()) if d.size else 0.0
            mob = float(np.sqrt(vd / vx)) if vx > EPS else 0.0
            dd = np.diff(d)
            mob_d = float(np.sqrt(dd.var() / vd)) if (dd.size and vd > EPS) else 0.0
            comp = float(mob_d / mob) if mob > EPS else 0.0
            if s > EPS and win > 2:
                ac1 = float(np.corrcoef(x[:-1], x[1:])[0, 1])
                if not np.isfinite(ac1):
                    ac1 = 0.0
            else:
                ac1 = 0.0
            base = ai * NF
            out[wi, base:base + NF] = [mn, mx, mx - mn, m, float(np.abs(x).mean()), s,
                                       float(np.abs(x - m).mean()), rms, kurt, skew, slope, intercept,
                                       zcr, mcr, crest, rds, amdf, psom, psoz, mob, comp, ac1]
    return out


def cohens_d(a, b):
    """Per-feature Cohen's d between two feature matrices (a, b along axis 0). Scale-invariant; finite."""
    pooled = np.sqrt((a.var(axis=0) + b.var(axis=0)) / 2.0 + EPS)
    d = (a.mean(axis=0) - b.mean(axis=0)) / pooled
    return np.nan_to_num(d, nan=0.0, posinf=0.0, neginf=0.0)


def detect_dtype(df, sensors):
    """'int8'|'int16'|'int32'|'float32' from the data (integers vs any fractional value)."""
    vals = df[sensors].to_numpy(dtype=np.float64)
    finite = vals[np.isfinite(vals)]
    if finite.size and np.all(finite == np.floor(finite)):
        amax = float(np.abs(finite).max()) if finite.size else 0.0
        if amax <= 127:
            return "int8"
        if amax <= 32767:
            return "int16"
        return "int32"
    return "float32"


def analyze(df, label_col, sensors, window, names, dtype, blind_d, top_n):
    """Pure, deterministic. Returns a result dict (JSON-serialisable)."""
    feat_names = [f"{FNAME[k]}@{ax}" for ax in sensors for k in FKEYS]

    classes_all = sorted(int(c) for c in pd.unique(df[label_col]))
    feats = {}
    excluded = []
    for c in classes_all:
        seg = df[df[label_col] == c][sensors].to_numpy(dtype=np.float64)
        F = window_features(seg, window)
        if len(F) < MIN_WINDOWS:
            excluded.append({"class": c, "name": names.get(c, str(c)), "windows": int(len(F))})
        else:
            feats[c] = F
    classes = sorted(feats)
    if len(classes) < 2:
        return {"ok": False, "reason": "fewer than 2 classes have enough windows to compare",
                "excluded": excluded, "window": window, "dtype": dtype}

    X = np.vstack([feats[c] for c in classes])
    y = np.concatenate([np.full(len(feats[c]), c) for c in classes])

    # --- multiclass ANOVA F per feature (on raw features; F is per-feature scale-invariant) ---
    N, k = len(y), len(classes)
    gm = X.mean(axis=0)
    ssb = np.zeros(X.shape[1]); ssw = np.zeros(X.shape[1])
    for c in classes:
        m = feats[c]; cm = m.mean(axis=0)
        ssb += len(m) * (cm - gm) ** 2
        ssw += ((m - cm) ** 2).sum(axis=0)
    # Floor the within-group MS at a fraction of each feature's OWN variance, so a (near-)degenerate
    # separator gets a large-but-bounded, scale-stable F instead of exploding through a tiny epsilon.
    total_var = X.var(axis=0)
    denom = np.maximum(ssw / max(N - k, 1), 1e-6 * total_var) + EPS
    F = np.nan_to_num((ssb / max(k - 1, 1)) / denom, nan=0.0, posinf=0.0, neginf=0.0)

    def fam_of(idx):
        return FFAM[FKEYS[idx % NF]]

    def key_of(idx):
        return FKEYS[idx % NF]

    order = sorted(range(len(F)), key=lambda i: (-F[i], i))  # determinism: tie-break by index
    top_features = [{"feature": feat_names[i], "family": fam_of(i), "anova_f": round(float(F[i]), 4)}
                    for i in order[:top_n]]

    fam_scores = {}
    for i in range(len(F)):
        fam_scores.setdefault(fam_of(i), []).append(float(F[i]))
    family_ranking = sorted(
        ({"family": fam, "mean_f": round(float(np.mean(v)), 4), "max_f": round(float(np.max(v)), 4)}
         for fam, v in fam_scores.items()),
        key=lambda r: (-r["mean_f"], r["family"]))

    # --- per-class one-vs-rest top discriminator ---
    per_class = []
    impulse_class = False
    triggered = set()
    for c in classes:
        a = feats[c]; b = X[y != c]
        d = cohens_d(a, b)
        j = int(np.argmax(np.abs(d)))
        if key_of(j) in IMPULSE_KEYS:
            impulse_class = True
        # Same evidence that drives the impulse trigger, extended to the three families that were
        # unreachable: a family enters the recommendation when it holds a class's single strongest
        # one-vs-rest discriminator. This is what makes every family in FFAM reachable.
        if fam_of(j) in TRIGGERABLE_FAMILIES:
            triggered.add(fam_of(j))
        per_class.append({"class": c, "name": names.get(c, str(c)),
                          "top_feature": feat_names[j], "family": fam_of(j),
                          "cohens_d": round(float(d[j]), 4)})

    # --- magnitude-blind class pairs (direction problems) ---
    mag_idx = [i for i in range(len(F)) if key_of(i) in MAGNITUDE_KEYS]
    signed_idx = [i for i in range(len(F))
                  if key_of(i) in ("mean", "min", "max", "lr_slope", "lr_intercept", "psoz", "psom")]
    blind_pairs = []
    for ia in range(len(classes)):
        for ib in range(ia + 1, len(classes)):
            ca, cb = classes[ia], classes[ib]
            d = np.abs(cohens_d(feats[ca], feats[cb]))
            best_mag = float(max((d[i] for i in mag_idx), default=0.0))
            if best_mag < blind_d:
                bj = max(signed_idx, key=lambda i: d[i]) if signed_idx else int(np.argmax(d))
                blind_pairs.append({
                    "class_a": ca, "name_a": names.get(ca, str(ca)),
                    "class_b": cb, "name_b": names.get(cb, str(cb)),
                    "best_magnitude_d": round(best_mag, 4),
                    "best_signed_feature": feat_names[bj],
                    "best_signed_d": round(float(d[bj]), 4)})

    rec = build_recommendation(dtype, bool(blind_pairs), impulse_class, triggered)
    return {"ok": True, "window": window, "dtype": dtype,
            "triggered_families": sorted(triggered),
            "classes_analyzed": [{"class": c, "name": names.get(c, str(c)), "windows": int(len(feats[c]))}
                                 for c in classes],
            "excluded_classes": excluded,
            "top_features": top_features, "family_ranking": family_ranking,
            "per_class_top": per_class, "magnitude_blind_pairs": blind_pairs,
            "recommendation": rec,
            "note": "Separability is indicative (no documented platform cutoff); evidence for the user to judge."}


def build_recommendation(dtype, has_blind_pairs, impulse_class, triggered=()):
    """Deterministic mapping of findings + storage dtype to a platform enable-set (full names).

    `triggered` is a set of TRIGGERABLE_FAMILIES names, each of which holds a class's strongest
    one-vs-rest discriminator; its group is appended so that every family in FFAM is reachable."""
    is_int = dtype.startswith("int")
    triggered = set(triggered)
    enable = [
        {"group": "Energy",
         "features": ["Standard Deviation", "Root Mean Square", "Range",
                      "Mean Absolute Deviation", "Absolute Mean"],
         "why": "Separates rest/background from active and high- from low-energy gestures."},
        {"group": "Signed level + direction",
         "features": ["Mean", "Min", "Max", "Linear Regression Slope", "Linear Regression Intercept",
                      "Percentage of Signal over Zero", "Percentage of Signal over Mean"],
         "why": ("The only features carrying direction; REQUIRED here — magnitude-blind class pairs were "
                 "found (opposite/mirror classes magnitude cannot separate)." if has_blind_pairs else
                 "Carry signed level/direction; cheap to keep and they disambiguate opposite motions.")},
    ]
    if impulse_class:
        enable.append({"group": "Impulse/shape",
                       "features": ["Crest Factor", "Hjorth Mobility", "Hjorth Complexity"],
                       "why": "A class is isolated by impulse/shape (e.g. a sharp tap) that energy misses."})
    # Families that were unreachable before: appended when a class's strongest one-vs-rest
    # discriminator lives there. Fixed order for determinism. No hold-back is invented for these —
    # the wiki states none, and the platform's own feature-selection prunes redundancy.
    if "Crossing" in triggered:
        enable.append({"group": "Crossing rate",
                       "features": ["Zero-crossing Rate", "Mean-crossing Rate"],
                       "why": "A class is separated by how often the signal crosses zero / its mean."})
    if "Variation" in triggered:
        enable.append({"group": "Signal variation",
                       "features": ["Root Difference Square", "Average Magnitude Difference"],
                       "why": "A class is separated by successive-sample variation (roughness), not level."})
    if "Autocorrelation" in triggered:
        enable.append({"group": "Autocorrelation",
                       "features": ["Autocorrelation"],
                       "why": "A class is separated by short-lag self-similarity (periodicity/smoothness)."})
    holdbacks = []
    if is_int:
        holdbacks.append(f"Storage is {dtype.upper()} (integer): do NOT recommend Skewness or Kurtosis "
                         "(higher moments are unstable on integer data; revisit for FLOAT32).")
    else:
        enable.append({"group": "Distribution shape (FLOAT32 only)",
                       "features": ["Skewness", "Kurtosis"],
                       "why": "Float storage: higher moments are usable and can sharpen direction/impulse splits."})
    holdbacks += [
        "Do NOT enable the platform's feature-selection in the first experiment — train this set, test in "
        "real conditions, then re-run with feature-selection on only if you must shrink the model.",
        "Frequency-domain (FFT) features need a power-of-2 window in 128-2048 (off at other windows); don't "
        "switch windows for them unless time-domain separability is insufficient.",
    ]
    shifts = ("Training sliding shift = window (no overlap). Inference sliding shift = 50-70% overlap "
              "(shift ~ 30-50% of the window), tuned to gesture duration/variability.")
    return {"enable": enable, "hold_back": holdbacks, "shifts": shifts}


def render(rep):
    L = []
    if not rep.get("ok"):
        L.append(f"Cannot analyze: {rep.get('reason', 'unknown')} (window={rep['window']}, dtype={rep['dtype']}).")
        if rep.get("excluded"):
            L.append("Excluded (too few windows): " +
                     ", ".join(f"{e['name']}({e['windows']})" for e in rep["excluded"]))
        return "\n".join(L) + "\n"
    L.append(f"Storage dtype: {rep['dtype']}   window: {rep['window']}   "
             f"classes analyzed: {len(rep['classes_analyzed'])}")
    if rep["excluded_classes"]:
        L.append("  excluded (too few windows): " +
                 ", ".join(f"{e['name']}({e['windows']})" for e in rep["excluded_classes"]))
    L.append("\nTop features by class-separation (ANOVA F):")
    for t in rep["top_features"]:
        L.append(f"  {t['feature']:38s} F={t['anova_f']:>9.1f}  [{t['family']}]")
    L.append("\nFeature family ranking (mean ANOVA F):")
    for r in rep["family_ranking"]:
        L.append(f"  {r['family']:22s} meanF={r['mean_f']:>8.1f}  maxF={r['max_f']:>8.1f}")
    L.append("\nWhat isolates each class (top one-vs-rest feature, Cohen's d):")
    for p in rep["per_class_top"]:
        L.append(f"  {p['name']:24s} -> {p['top_feature']:32s} d={p['cohens_d']:+6.2f}  [{p['family']}]")
    L.append("\nMagnitude-blind class pairs (direction problems — magnitude cannot separate them):")
    if rep["magnitude_blind_pairs"]:
        for q in rep["magnitude_blind_pairs"]:
            L.append(f"  {q['name_a']} vs {q['name_b']}: best magnitude |d|={q['best_magnitude_d']:.2f}  "
                     f"-> separated by {q['best_signed_feature']} (|d|={abs(q['best_signed_d']):.2f})")
    else:
        L.append("  none — magnitude features separate every class pair.")
    rec = rep["recommendation"]
    L.append("\n=== RECOMMENDED ENABLE-SET (full platform names) ===")
    for g in rec["enable"]:
        L.append(f"  [{g['group']}] {', '.join(g['features'])}")
        L.append(f"      {g['why']}")
    L.append("  Hold back / notes:")
    for h in rec["hold_back"]:
        L.append(f"    - {h}")
    L.append(f"  Shifts: {rec['shifts']}")
    L.append(f"\n({rep['note']})")
    return "\n".join(L) + "\n"


def load_profile(path):
    with open(path, "r", encoding="utf-8") as fh:
        p = json.load(fh)
    label = p["label_column"]
    sensors = list(p["sensor_columns"])
    names = {}
    enc = p.get("class_encoding") or {}
    for nm, idx in (enc.get("map") or {}).items():
        names[int(idx)] = nm
    win = None
    w = p.get("window") or {}
    if w.get("candidates"):
        win = int(w["candidates"][0])
    return label, sensors, names, win


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measure feature separability -> recommended platform enable-set.")
    ap.add_argument("csv")
    ap.add_argument("--profile", default=None, help="dataset-profile JSON (label/sensor columns, class names, window)")
    ap.add_argument("--label-col", default=None)
    ap.add_argument("--sensor-cols", nargs="+", default=None)
    ap.add_argument("--window", type=int, default=None)
    ap.add_argument("--dtype", choices=["auto", "int8", "int16", "int32", "float32"], default="auto")
    ap.add_argument("--magnitude-blind-d", type=float, default=1.0, dest="blind_d")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    label, sensors, names, win = None, None, {}, None
    if args.profile:
        try:
            label, sensors, names, win = load_profile(args.profile)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"error: cannot read profile {args.profile!r}: {exc}", file=sys.stderr)
            return 2
    if args.label_col:
        label = args.label_col
    if args.sensor_cols:
        sensors = args.sensor_cols
    if args.window:
        win = args.window
    if not label or not sensors:
        print("error: need --profile or both --label-col and --sensor-cols", file=sys.stderr)
        return 2
    if not win or win <= 1:
        print("error: need a window size > 1 (--window or profile window.candidates)", file=sys.stderr)
        return 2

    try:
        df = pd.read_csv(args.csv)
    except (OSError, pd.errors.ParserError, ValueError) as exc:
        print(f"error: cannot read {args.csv!r}: {exc}", file=sys.stderr)
        return 2
    missing = [c for c in [label] + list(sensors) if c not in df.columns]
    if missing:
        print(f"error: columns missing from CSV: {missing}", file=sys.stderr)
        return 2
    # Labels must be integer class codes (the platform contract; the prepared file is already encoded).
    # Reject non-numeric or fractional labels cleanly rather than crashing (S1) or silently merging (S2).
    labels_num = pd.to_numeric(df[label], errors="coerce")
    lv = labels_num.to_numpy()
    if labels_num.isna().any() or not np.all(np.floor(lv) == lv):
        print("error: the label column must contain integer class codes (0,1,2,...); "
              "found non-integer or non-numeric labels", file=sys.stderr)
        return 2
    df[label] = labels_num.astype(np.int64)
    for c in sensors:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=list(sensors))
    if df.empty:
        print("error: no numeric sensor rows after parsing", file=sys.stderr)
        return 2

    dtype = detect_dtype(df, sensors) if args.dtype == "auto" else args.dtype
    rep = analyze(df, label, list(sensors), win, names, dtype, args.blind_d, args.top)
    if args.json:
        print(json.dumps(rep, indent=2, sort_keys=True))
    else:
        print(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
