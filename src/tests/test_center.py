import unittest

import numpy as np

import _helpers as H
from data_builder.center import center_per_class, PEAK_TOLERANCE


class TestCenter(unittest.TestCase):
    def test_continuous_trimmed_to_window_multiple(self):
        # only class 0 (continuous); 53 rows, window 20 -> keep 40
        df = H.block(0, 53)
        df["acc_z"] = [9.78] * len(df)  # all float
        out, findings = center_per_class(df, H.prof(), window=20)
        self.assertEqual(len(out), 40)
        self.assertTrue(H.pd.api.types.is_float_dtype(out["acc_z"]) or out["acc_z"].iloc[0] == 9.78)

    def test_float_preserved_in_gesture_window(self):
        # class 1 is a gesture with several repetitions (realistic); a float marker sits AT a peak,
        # so it lands inside a kept window and must survive un-truncated.
        n = 240
        rng = np.random.RandomState(2)
        z = 0.01 * rng.randn(n)
        for p in (40, 90, 140, 190):
            z[p - 1:p + 2] += 6.0
        z[90] = 9.78  # marker at a peak
        g = H.pd.DataFrame({"acc_x": 0.01 * rng.randn(n), "acc_y": 0.01 * rng.randn(n), "acc_z": z})
        g["class"] = 1
        out, findings = center_per_class(g, H.prof(), window=20)
        self.assertIn(9.78, out["acc_z"].tolist())  # the float survived, not truncated to 9
        self.assertEqual(len(out) % 20, 0)

    def test_centering_drops_time_and_session_columns(self):
        # A time column would be scrambled by the row reorder; centering must drop it (+ session).
        n = 240
        rng = np.random.RandomState(9)
        z = 0.01 * rng.randn(n)
        for p in (40, 90, 140, 190):
            z[p - 1:p + 2] += 6.0
        df = H.pd.DataFrame({"acc_x": 0.01 * rng.randn(n), "acc_y": 0.01 * rng.randn(n), "acc_z": z,
                             "t": np.arange(n) / 100.0, "session_id": 0})
        df["class"] = 1
        profile = H.prof(time_column="t", session_column="session_id")
        out, findings = center_per_class(df, profile, window=20)
        self.assertNotIn("t", out.columns)
        self.assertNotIn("session_id", out.columns)
        self.assertEqual(list(out.columns), ["acc_x", "acc_y", "acc_z", "class"])
        self.assertTrue(any(f.code == "centering_dropped_columns" for f in findings))

    def test_class_in_neither_list_is_flagged(self):
        # profile partitions 0(continuous),1,2(gesture); class 3 is in neither.
        df = H.concat(H.block(0, 25), H.block(3, 25))
        out, findings = center_per_class(df, H.prof(), window=20)
        self.assertTrue(any(f.code == "class_not_partitioned" for f in findings))

    def test_gesture_peak_lands_mid_window(self):
        # class 1 (gesture) with clear peaks -> each kept window's peak is within tolerance of the middle.
        window = 20
        n = 240
        rng = np.random.RandomState(7)
        z = 0.01 * rng.randn(n)
        for p in (40, 90, 140, 190):
            z[p - 1:p + 2] += 6.0
        df = H.pd.DataFrame({"acc_x": 0.01 * rng.randn(n), "acc_y": 0.01 * rng.randn(n), "acc_z": z})
        df["class"] = 1
        out, findings = center_per_class(df, H.prof(), window=window)
        self.assertGreater(len(out), 0)
        self.assertEqual(len(out) % window == 0, True)
        half = window // 2
        for s in range(0, len(out), window):
            seg = out["acc_z"].to_numpy()[s:s + window]
            peak_pos = int(np.argmax(np.abs(seg - seg.mean())))
            self.assertLessEqual(abs(peak_pos - half), PEAK_TOLERANCE)


if __name__ == "__main__":
    unittest.main()
