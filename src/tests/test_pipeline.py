import os
import tempfile
import unittest

import _helpers as H
from data_builder.profile import DatasetProfile
from data_builder import pipeline


def _csv(df, d, name):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _profile():
    raw = dict(H.BASE_PROFILE)
    raw["sampling_rate_hz"] = 100
    return DatasetProfile.from_dict(raw)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.profile = _profile()

    def test_passing_end_to_end(self):
        a = _csv(H.block(0, 60), self.d, "idle.csv")
        b = _csv(H.concat(H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30)), self.d, "gest.csv")
        out = os.path.join(self.d, "upload_ready.csv")
        result = pipeline.prep([a, b], self.profile, out, window=20, do_center=False)  # raw assembly
        self.assertEqual(result["report"].verdict, "PASS", msg=[f.code for f in result["report"].findings])
        self.assertTrue(result["written"])
        reloaded = H.pd.read_csv(out)
        self.assertEqual(list(reloaded.columns), ["acc_x", "acc_y", "acc_z", "class"])
        self.assertTrue(all(H.pd.api.types.is_numeric_dtype(reloaded[c]) for c in reloaded.columns))
        self.assertTrue(os.path.exists(result["dictionary_path"]))

    def test_refuses_on_will_lose_data(self):
        bad = _csv(H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 30), H.block(1, 12),
                            H.block(2, 60)), self.d, "bad.csv")
        out = os.path.join(self.d, "out.csv")
        result = pipeline.prep([bad], self.profile, out, window=20, do_center=False)
        self.assertEqual(result["report"].verdict, "WILL_LOSE_DATA")
        self.assertFalse(result["written"])
        self.assertFalse(os.path.exists(out))

    def test_write_anyway_overrides(self):
        bad = _csv(H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 30), H.block(1, 12),
                            H.block(2, 60)), self.d, "bad.csv")
        out = os.path.join(self.d, "out.csv")
        result = pipeline.prep([bad], self.profile, out, window=20, write_anyway=True, do_center=False)
        self.assertTrue(result["written"])
        self.assertTrue(os.path.exists(out))

    def test_empty_input(self):
        empty = os.path.join(self.d, "empty.csv")
        H.pd.DataFrame(columns=["acc_x", "acc_y", "acc_z", "class"]).to_csv(empty, index=False)
        out = os.path.join(self.d, "out.csv")
        result = pipeline.prep([empty], self.profile, out, window=20)
        self.assertFalse(result["written"])
        self.assertTrue(any(f.code == "empty_input" for f in result["report"].findings))

    def test_default_centers_gesture_dataset(self):
        import numpy as np

        def gesture(label, n=240, peaks=6):
            rng = np.random.RandomState(label + 1)
            z = 0.01 * rng.randn(n)
            step = n // (peaks + 1)
            for k in range(1, peaks + 1):
                p = k * step
                z[p - 1:p + 2] += 6.0
            df = H.pd.DataFrame({"acc_x": 0.01 * rng.randn(n), "acc_y": 0.01 * rng.randn(n), "acc_z": z})
            df["class"] = label
            return df

        a = _csv(H.block(0, 200), self.d, "idle.csv")
        b = _csv(H.concat(gesture(1), gesture(2)), self.d, "gest.csv")
        raw_rows = 200 + 240 + 240
        out = os.path.join(self.d, "centered.csv")
        result = pipeline.prep([a, b], self.profile, out, window=20)   # no do_center -> auto-center on
        self.assertTrue(result["written"], msg=[f.code for f in result["report"].findings])
        reloaded = H.pd.read_csv(out)
        self.assertLess(len(reloaded), raw_rows)        # centering reduced the gesture rows to clean windows
        self.assertEqual(len(reloaded) % 20, 0)         # whole windows only

    def test_no_center_skips_centering(self):
        a = _csv(H.block(0, 60), self.d, "idle.csv")
        b = _csv(H.concat(H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30)), self.d, "g.csv")
        out = os.path.join(self.d, "raw.csv")
        result = pipeline.prep([a, b], self.profile, out, window=20, do_center=False)
        self.assertEqual(len(H.pd.read_csv(out)), 180)   # untouched row count

    def test_float_not_truncated_through_pipeline(self):
        rec = H.block(0, 60)
        rec.loc[5, "acc_z"] = 9.78
        a = _csv(rec, self.d, "a.csv")
        b = _csv(H.concat(H.block(1, 60), H.block(2, 60)), self.d, "b.csv")
        out = os.path.join(self.d, "out.csv")
        pipeline.prep([a, b], self.profile, out, window=20, write_anyway=True)
        reloaded = H.pd.read_csv(out)
        self.assertIn(9.78, reloaded["acc_z"].tolist())


if __name__ == "__main__":
    unittest.main()
