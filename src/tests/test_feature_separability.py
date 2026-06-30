"""Subprocess tests for scripts/diagnostics/feature_separability.py (databuilder-005).

Covers: determinism, magnitude-blind mirror-pair detection, INT vs FLOAT moment hold-back,
short-class exclusion, --help, and profile vs explicit modes.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

import _helpers as H

REPO = os.path.dirname(H.SRC)
SCRIPT = "scripts/diagnostics/feature_separability.py"
SENSORS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]


def _run(*args):
    return subprocess.run([sys.executable, os.path.join(REPO, SCRIPT), *args],
                          capture_output=True, text=True, cwd=REPO)


def _write(df, d, name="t.csv"):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _noise(n, rng, scale=0.01):
    return {s: scale * rng.randn(n) for s in SENSORS}


class TestFeatureSeparability(unittest.TestCase):
    def test_help_runs(self):
        self.assertEqual(_run("--help").returncode, 0)

    def test_deterministic(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(0)
        frames = []
        for c in (0, 1, 2):
            data = _noise(120, rng)
            data["acc_x"] = data["acc_x"] + c * 3.0
            df = pd.DataFrame(data); df["class"] = c
            frames.append(df)
        p = _write(pd.concat(frames, ignore_index=True), d)
        a = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        b = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)            # identical input -> identical output

    def test_magnitude_blind_mirror_pair(self):
        # Two classes that differ ONLY in the sign of a ramp on one axis: magnitude features (std, rms,
        # range, ...) are sign-invariant -> identical -> magnitude Cohen's d == 0 (deterministic by
        # construction); only signed features (Linear Regression Slope/Intercept) separate them.
        d = tempfile.mkdtemp()
        W, nwin = 20, 6
        ramp = np.linspace(-1.0, 1.0, W)
        frames = []
        for c, sign in ((0, +1.0), (1, -1.0)):
            data = {s: np.zeros(W * nwin) for s in SENSORS}
            data["acc_x"] = np.tile(sign * ramp, nwin)
            df = pd.DataFrame(data); df["class"] = c
            frames.append(df)
        p = _write(pd.concat(frames, ignore_index=True), d)
        r = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", str(W), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = json.loads(r.stdout)
        pairs = rep["magnitude_blind_pairs"]
        self.assertEqual(len(pairs), 1)                 # the only pair, and it IS magnitude-blind
        q = pairs[0]
        self.assertLess(q["best_magnitude_d"], 1.0)     # magnitude can't tell them apart
        self.assertGreater(abs(q["best_signed_d"]), 1.5)
        self.assertIn("Linear Regression", q["best_signed_feature"])  # a signed feature separates them
        self.assertIn("@acc_x", q["best_signed_feature"])

    def test_int_holds_back_moments_float_allows(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(2)
        frames = []
        for c in (0, 1, 2):
            data = _noise(120, rng, scale=0.5)
            data["acc_x"] = data["acc_x"] + c * 50.0
            df = pd.DataFrame(data); df["class"] = c
            frames.append(df)
        base = pd.concat(frames, ignore_index=True)

        # INT: round sensor columns to integers -> dtype int -> Skewness/Kurtosis must NOT be recommended.
        di = base.copy()
        for s in SENSORS:
            di[s] = (di[s] * 100).round().astype(int)
        pi = _write(di, d, "int.csv")
        ri = _run(pi, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        self.assertEqual(ri.returncode, 0, ri.stderr)
        repi = json.loads(ri.stdout)
        self.assertTrue(repi["dtype"].startswith("int"))
        rec_feats = [f for g in repi["recommendation"]["enable"] for f in g["features"]]
        self.assertNotIn("Skewness", rec_feats)
        self.assertNotIn("Kurtosis", rec_feats)

        # FLOAT: keep fractional values -> dtype float32 -> Skewness/Kurtosis allowed.
        pf = _write(base, d, "float.csv")
        rf = _run(pf, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        self.assertEqual(rf.returncode, 0, rf.stderr)
        repf = json.loads(rf.stdout)
        self.assertEqual(repf["dtype"], "float32")
        rec_feats_f = [f for g in repf["recommendation"]["enable"] for f in g["features"]]
        self.assertIn("Skewness", rec_feats_f)

    def test_excludes_short_class(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(3)
        frames = []
        for c in (0, 1):
            data = _noise(120, rng); data["acc_x"] = data["acc_x"] + c * 3.0
            df = pd.DataFrame(data); df["class"] = c; frames.append(df)
        short = pd.DataFrame(_noise(10, rng)); short["class"] = 2     # 10 rows < window 20 -> 0 windows
        frames.append(short)
        p = _write(pd.concat(frames, ignore_index=True), d)
        r = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = json.loads(r.stdout)
        excluded = [e["class"] for e in rep["excluded_classes"]]
        analyzed = [c["class"] for c in rep["classes_analyzed"]]
        self.assertIn(2, excluded)
        self.assertNotIn(2, analyzed)

    def test_profile_mode(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(4)
        frames = []
        for c in (0, 1):
            data = _noise(120, rng); data["acc_x"] = data["acc_x"] + c * 3.0
            df = pd.DataFrame(data); df["class"] = c; frames.append(df)
        p = _write(pd.concat(frames, ignore_index=True), d)
        profile = {
            "dataset_name": "t", "label_column": "class", "sensor_columns": SENSORS,
            "separator": "comma", "task_type": "multiclass_classification",
            "class_encoding": {"map": {"idle": 0, "wave": 1}, "continuous_classes": [0],
                               "gesture_classes": [1]},
            "window": {"candidates": [20]},
        }
        pp = os.path.join(d, "profile.json")
        with open(pp, "w") as fh:
            json.dump(profile, fh)
        r = _run(p, "--profile", pp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("wave", r.stdout)                 # class name from the map is used

    def test_usage_error_without_columns(self):
        d = tempfile.mkdtemp()
        p = _write(pd.DataFrame({**_noise(40, np.random.RandomState(5)), "class": [0] * 20 + [1] * 20}), d)
        r = _run(p, "--window", "20")                   # no profile, no --label-col/--sensor-cols
        self.assertEqual(r.returncode, 2)

    def test_string_labels_rejected(self):
        # Non-integer (string) labels must error cleanly, not crash with a traceback.
        d = tempfile.mkdtemp()
        df = pd.DataFrame({**_noise(60, np.random.RandomState(6)), "class": ["walk"] * 30 + ["run"] * 30})
        p = _write(df, d)
        r = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20")
        self.assertEqual(r.returncode, 2)
        self.assertIn("integer class codes", r.stderr)

    def test_fractional_labels_rejected(self):
        # Fractional labels would silently merge (int(1.2)==int(1.8)); must be rejected.
        d = tempfile.mkdtemp()
        df = pd.DataFrame({**_noise(60, np.random.RandomState(7)), "class": [0.0] * 30 + [1.5] * 30})
        p = _write(df, d)
        r = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20")
        self.assertEqual(r.returncode, 2)

    def test_extreme_values_emit_valid_json(self):
        # Absurd sensor magnitudes must not produce a bare NaN token (invalid JSON).
        d = tempfile.mkdtemp()
        frames = []
        for c in (0, 1):
            data = {s: np.full(80, 1e160) for s in SENSORS}
            data["acc_x"] = np.full(80, 1e160 * (1 + c))
            df = pd.DataFrame(data); df["class"] = c; frames.append(df)
        p = _write(pd.concat(frames, ignore_index=True), d)
        r = _run(p, "--label-col", "class", "--sensor-cols", *SENSORS, "--window", "20", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        json.loads(r.stdout)                            # must parse — no bare NaN tokens


if __name__ == "__main__":
    unittest.main()
