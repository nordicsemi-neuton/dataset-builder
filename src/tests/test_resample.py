import unittest

import numpy as np

import _helpers as H
from data_builder.resample import resample_to_rate


def _timed(label, t0, n, hz):
    t = t0 + np.arange(n) / hz
    df = H.pd.DataFrame({"acc_x": 0.01 * np.random.RandomState(1).randn(n),
                         "acc_y": np.zeros(n), "acc_z": np.full(n, 9.78)})
    df["t"] = t
    df["class"] = label
    return df


class TestResample(unittest.TestCase):
    def setUp(self):
        self.profile = H.prof(time_column="t")
        self.sensors = ["acc_x", "acc_y", "acc_z"]

    def test_uniform_grid_and_minority_survives(self):
        df = H.concat(_timed(0, 0.0, 50, 50), _timed(1, 1.0, 30, 50))
        out, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        # class 1 (minority) still present after resampling
        self.assertIn(1, out["class"].tolist())
        # spacing within the class-0 run is ~0.01s (100 Hz)
        c0 = out[out["class"] == 0]["t"].to_numpy()
        self.assertTrue(np.allclose(np.diff(c0), 0.01, atol=1e-6))

    def test_duplicate_timestamp_flagged(self):
        df = _timed(0, 0.0, 20, 50)
        df.loc[5, "t"] = df.loc[4, "t"]  # duplicate -> non-monotonic
        _, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        self.assertTrue(any(f.code == "nonmonotonic_timestamps" for f in findings))

    def test_no_time_column_is_noop_finding(self):
        df = H.block(0, 20)
        out, findings = resample_to_rate(df, None, 100, self.sensors, "class", None, "s")
        self.assertEqual(len(out), len(df))
        self.assertTrue(any(f.code == "no_time_column_for_resample" for f in findings))


if __name__ == "__main__":
    unittest.main()
