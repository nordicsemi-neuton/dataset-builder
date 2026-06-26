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
    def test_help_runs(self):
        r = _run("scripts/diagnostics/check_signal_centered.py", "--help")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
