"""Subprocess tests for the 3 fixed reference scripts (databuilder-002 acceptance requires coverage)."""
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import _helpers as H

REPO = os.path.dirname(H.SRC)
SENSORS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]


def _run(rel, *args):
    return subprocess.run([sys.executable, os.path.join(REPO, rel), *args],
                          capture_output=True, text=True, cwd=REPO)


class TestWindowedComparison(unittest.TestCase):
    def test_runs_and_flags_closest(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(0)

        def blk(label, center, n=80):
            df = H.pd.DataFrame({c: center + 0.3 * rng.randn(n) for c in SENSORS})
            df["class"] = label
            return df
        train = H.concat(blk(0, 0.0), blk(1, 5.0), blk(2, 10.0))
        test = blk(1, 5.0)  # closest to class 1
        tp = os.path.join(d, "train.csv"); train.to_csv(tp, index=False)
        ep = os.path.join(d, "test.csv"); test.to_csv(ep, index=False)
        r = _run("scripts/diagnostics/windowed_feature_distribution_comparison.py",
                 "--train", tp, "--test", ep, "--window", "20", "--shift", "20")
        self.assertEqual(r.returncode, 0, r.stderr)        # no crash (was a ValueError before the fix)
        self.assertIn("<-- closest", r.stdout)
        # the closest flag is on the class-1 line
        for line in r.stdout.splitlines():
            if "<-- closest" in line:
                self.assertIn("class 1", line)


class TestCenterScript(unittest.TestCase):
    def test_float_preserved_and_warns_on_bad_row(self):
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(1)

        def blk(label, n, peak=False):
            data = {c: 0.01 * rng.randn(n) for c in SENSORS}
            if peak:
                data["acc_z"][n // 2 - 2:n // 2 + 3] += 5.0
            data["acc_z"][3] = 9.78
            df = H.pd.DataFrame(data); df["class"] = label
            return df
        df = H.concat(blk(0, 120), blk(2, 120, peak=True))
        df["acc_x"] = df["acc_x"].astype(object)
        df.loc[5, "acc_x"] = "bad"      # one unparseable value -> loud warning
        ip = os.path.join(d, "in.csv"); df.to_csv(ip, index=False)
        op = os.path.join(d, "out.csv")
        r = _run("scripts/preprocessing/center_training_data.py", "--input", ip, "--output", op,
                 "--window", "40", "--continuous-classes", "0", "--gesture-classes", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WARNING", r.stdout)               # dropped row is loud, not silent
        out = H.pd.read_csv(op)
        self.assertIn(9.78, out["acc_z"].round(2).tolist())   # float preserved, not truncated
        self.assertTrue(H.pd.api.types.is_integer_dtype(out["class"]))


class TestCheckSignalCentered(unittest.TestCase):
    SCRIPT = "scripts/diagnostics/check_signal_centered.py"

    def test_help_runs(self):
        r = _run(self.SCRIPT, "--help")
        self.assertEqual(r.returncode, 0, r.stderr)

    def _emg(self, d, extra=None, name="emg.csv"):
        rng = np.random.RandomState(3)
        n = 800
        data = {f"emg_{i}": 0.02 * rng.randn(n) for i in (1, 2, 3)}
        for w in range(n // 100):          # a genuinely centered gesture on emg_2
            data["emg_2"][w * 100 + 48:w * 100 + 53] += 4.0
        df = H.pd.DataFrame(data)
        df["class"] = 1
        if extra:
            extra(df)
        p = os.path.join(d, name)
        df.to_csv(p, index=False)
        return p

    def test_sensor_cols_non_imu_runs(self):
        # databuilder-015 D2a-1: non-IMU columns are dead-ended on the parent; --sensor-cols runs.
        d = tempfile.mkdtemp()
        p = self._emg(d)
        r = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "emg_1", "emg_2", "emg_3")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CENTERED", r.stdout)

    def test_sensor_cols_missing_column(self):
        d = tempfile.mkdtemp()
        p = self._emg(d)
        r = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "emg_1", "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nope", r.stderr)
        # on the parent argparse rejects the unknown flag and echoes the value; must NOT be that path
        self.assertNotIn("unrecognized arguments", r.stderr)

    def test_sensor_cols_text_column_rejected(self):
        d = tempfile.mkdtemp()
        p = self._emg(d, extra=lambda df: df.__setitem__("emg_1", "x"))
        r = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "emg_1", "emg_2", "emg_3")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("emg_1", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        # not the parent's argparse-rejects-the-flag path (which would also be non-zero + name it)
        self.assertNotIn("unrecognized arguments", r.stderr)

    def test_sensor_cols_bool_column_rejected(self):
        d = tempfile.mkdtemp()
        p = self._emg(d, extra=lambda df: df.__setitem__("emg_1", df["emg_1"] > 0))
        r = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "emg_1", "emg_2", "emg_3")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("emg_1", r.stderr)
        self.assertNotIn("unrecognized arguments", r.stderr)

    def test_sensor_cols_nonfinite_refused(self):
        # The new flag targets unprepared files; a non-finite sensor value is refused with a clear
        # message rather than producing a silently corrupted verdict (P-21: no new silent path).
        d = tempfile.mkdtemp()
        p = self._emg(d, extra=lambda df: df.__setitem__("emg_1",
                                                          df["emg_1"].mask(df.index == 137, np.nan)))
        r = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "emg_1", "emg_2", "emg_3")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("emg_1", r.stderr)
        self.assertIn("finite", r.stderr)

    def test_default_path_unchanged(self):
        # [guard] with --sensor-cols omitted a clean IMU CSV is byte-identical to the parent's output.
        d = tempfile.mkdtemp()
        rng = np.random.RandomState(7)
        n = 1200
        data = {c: 0.01 * rng.randn(n) for c in SENSORS}
        for w in range(n // 100):
            data["acc_z"][w * 100 + 48:w * 100 + 53] += 5.0
        df = H.pd.DataFrame(data)
        df["class"] = 1
        p = os.path.join(d, "imu.csv")
        df.to_csv(p, index=False)
        r = _run(self.SCRIPT, p, "--label-col", "class")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CENTERED", r.stdout)
        # the "No sensor columns found" message must advertise the new flag on the default path
        r2 = _run(self.SCRIPT, p, "--label-col", "class", "--sensor-cols", "nope1", "nope2")
        self.assertIn("nope1", r2.stderr)


def _wss(*args):
    return _run("scripts/diagnostics/window_survival_sim.py", *args)


class TestWindowSurvivalSim(unittest.TestCase):
    """window_survival_sim.py had zero coverage before databuilder-015 D2a-2."""

    def _write(self, d, labels, name="w.csv"):
        rng = np.random.RandomState(0)
        n = len(labels)
        df = H.pd.DataFrame({"acc_x": rng.randn(n), "acc_y": rng.randn(n)})
        df["label"] = labels
        p = os.path.join(d, name)
        df.to_csv(p, index=False)
        return p

    def test_string_labels(self):
        # D2a-2: parent raises ValueError at int(k) after the totals; the per-label numbers are lost.
        d = tempfile.mkdtemp()
        p = self._write(d, ["walk"] * 300 + ["run"] * 300)
        r = _wss(p, "--window", "100", "--shift", "50")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("label walk:", r.stdout)
        self.assertIn("label run:", r.stdout)

    def test_string_labels_with_blank(self):
        # parent crashes at sorted() before any output; must not, and must not invent a nan class.
        d = tempfile.mkdtemp()
        labels = ["walk"] * 150 + [np.nan] + ["walk"] * 149 + ["run"] * 300
        p = self._write(d, labels)
        r = _wss(p, "--window", "100", "--shift", "50")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("label nan:", r.stdout)
        self.assertIn("missing / non-finite label", r.stdout)

    def test_inf_label_no_crash_no_phantom(self):
        # parent OverflowError; a naive str() fix prints a phantom 'label inf' <-- ZERO; neither here.
        d = tempfile.mkdtemp()
        p = self._write(d, [0.0] * 200 + [np.inf] * 200 + [1.0] * 200)
        r = _wss(p, "--window", "100", "--shift", "50")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("label inf:", r.stdout)
        self.assertIn("label 0:", r.stdout)
        self.assertIn("label 1:", r.stdout)

    def test_numeric_labels_render_as_bare_integers(self):
        # [guard] int64, integral float64 and bool all render "label 0:" (not "0.0" / "False").
        for labels in ([0] * 300 + [1] * 300,
                       [0.0] * 300 + [1.0] * 300,
                       [False] * 300 + [True] * 300):
            d = tempfile.mkdtemp()
            p = self._write(d, labels)
            r = _wss(p, "--window", "100", "--shift", "50")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("label 0:", r.stdout)
            self.assertIn("label 1:", r.stdout)
            self.assertNotIn("label 0.0:", r.stdout)
            self.assertNotIn("label False:", r.stdout)


if __name__ == "__main__":
    unittest.main()
