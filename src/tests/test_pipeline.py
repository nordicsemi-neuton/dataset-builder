import os
import tempfile
import unittest

import _helpers as H
from data_builder.profile import DatasetProfile
from data_builder import pipeline


def _rb(path):
    with open(path, "rb") as fh:
        return fh.read()


def _csv(df, d, name):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _profile():
    raw = dict(H.BASE_PROFILE)
    raw["sampling_rate_hz"] = 100
    return DatasetProfile.from_dict(raw)


def _timed_profile():
    raw = dict(H.BASE_PROFILE)
    raw["sampling_rate_hz"] = 50
    raw["time_column"] = "t"
    return DatasetProfile.from_dict(raw)


def _int_run(label, t0, n, hz=50):
    t = t0 + H.np.arange(n) / hz
    return H.pd.DataFrame({"acc_x": (150 + (H.np.arange(n) * 7) % 200).astype(H.np.int64),
                           "acc_y": (200 + (H.np.arange(n) * 3) % 100).astype(H.np.int64),
                           "acc_z": (300 - (H.np.arange(n) * 5) % 150).astype(H.np.int64),
                           "t": t, "class": label})


def _int_timed_multiclass():
    # 3 contiguous classes, all-integral sensors in the INT16 band, monotone time across the file.
    return H.concat(_int_run(0, 0.0, 80), _int_run(1, 2.0, 80), _int_run(2, 4.0, 80))


def _int_gesture_run(label, t0, n, hz=50, peak=False):
    t = t0 + H.np.arange(n) / hz
    z = (200 + (H.np.arange(n) * 2) % 20).astype(H.np.int64)
    if peak:  # integral spikes so centering detects gesture windows
        for k in range(1, 4):
            idx = k * (n // 4)
            z[max(0, idx - 1):idx + 2] += 800
    return H.pd.DataFrame({"acc_x": (150 + (H.np.arange(n) * 2) % 20).astype(H.np.int64),
                           "acc_y": (200 + (H.np.arange(n) * 2) % 20).astype(H.np.int64),
                           "acc_z": z, "t": t, "class": label})


def _int_timed_gestures():
    return H.concat(_int_gesture_run(0, 0.0, 120, peak=False),
                    _int_gesture_run(1, 3.0, 120, peak=True),
                    _int_gesture_run(2, 6.0, 120, peak=True))


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

    def test_prep_resample_preserves_integers(self):
        # databuilder-021 / B4: prep --resample (do_center=False) on an all-integral timed set writes
        # whole-number sensor values, discloses resample_integer_preserved, and recovers INT16.
        prof = _timed_profile()
        p = _csv(_int_timed_multiclass(), self.d, "activity.csv")
        out = os.path.join(self.d, "resampled.csv")
        result = pipeline.prep([p], prof, out, window=20, do_center=False, target_rate=100.0)
        codes = [f.code for f in result["report"].findings]
        self.assertTrue(result["written"], msg=codes)
        self.assertIn("resample_integer_preserved", codes)
        reloaded = H.pd.read_csv(out)
        for c in ["acc_x", "acc_y", "acc_z"]:
            self.assertTrue((reloaded[c] % 1 == 0).all(), msg=f"{c} not whole")
        dt = next(f for f in result["report"].findings if f.code == "recommended_dtype")
        self.assertEqual(dt.data["dtype"], "INT16")

    def test_prep_resample_center_valid_output(self):
        # databuilder-021 / B4 (gate D-3): re-quantizing before centering must still yield a valid,
        # non-lossy output -- byte identity is NOT claimed on this path, but no class may vanish.
        prof = _timed_profile()
        p = _csv(_int_timed_gestures(), self.d, "gestures.csv")
        out = os.path.join(self.d, "centered.csv")
        result = pipeline.prep([p], prof, out, window=20, target_rate=100.0)  # centering default-on
        self.assertTrue(result["written"], msg=[f.code for f in result["report"].findings])
        self.assertNotEqual(result["report"].verdict, "WILL_LOSE_DATA")
        reloaded = H.pd.read_csv(out)
        self.assertEqual(set(reloaded["class"].unique()), {0, 1, 2})  # every input class survives
        for c in ["acc_x", "acc_y", "acc_z"]:
            self.assertTrue(H.pd.api.types.is_numeric_dtype(reloaded[c]))
            self.assertTrue(H.np.isfinite(reloaded[c].to_numpy()).all())

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
        self.assertEqual(result["report"].verdict, "PASS")  # centering's row-delta INFO is verdict-neutral (databuilder-014)
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

    def test_regression_survives_prep(self):
        # databuilder-018 (B1a): a short-run REGRESSION target must not trip class_run_below_window
        # (parent: is_numeric_dtype guard runs min_run_ok -> WILL_LOSE_DATA -> not written). The target
        # must round-trip its values, not be rank-encoded. Rate set so it is the ONLY parent blocker.
        import numpy as np
        tgt = [60] * 15 + [90] * 15 + [120] * 15          # the 15-row frame from test 1 (red on parent)
        n = len(tgt)
        frame = H.pd.DataFrame({"acc_x": 0.01 * np.arange(n), "acc_y": np.zeros(n),
                                "acc_z": np.zeros(n), "class": tgt})
        csvp = _csv(frame, self.d, "reg.csv")
        prof = DatasetProfile.from_dict({**H.BASE_PROFILE, "sampling_rate_hz": 100,
                                         "task_type": "regression"})
        out = os.path.join(self.d, "reg_out.csv")
        result = pipeline.prep([csvp], prof, out, window=20, do_center=False)
        self.assertTrue(result["written"], msg=[f.code for f in result["report"].findings])
        self.assertEqual(result["report"].verdict, "PASS")
        self.assertEqual(H.pd.read_csv(out)["class"].tolist(), tgt)   # target preserved

    def test_combine_seam_time_order_ok(self):
        # databuilder-019: two files, each monotone but restarting at DIFFERENT origins (0.00 and 0.02).
        # combine checks each file alone, so the concatenation seam is never seen -> NOT flagged, writes.
        import numpy as np

        def rec(name, t0):
            df = H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60))
            df["t"] = t0 + np.arange(180) / 100.0
            return _csv(df, self.d, name)

        a, b = rec("a.csv", 0.0), rec("b.csv", 0.02)
        out = os.path.join(self.d, "combined.csv")
        prof = DatasetProfile.from_dict({**H.BASE_PROFILE, "sampling_rate_hz": 100, "time_column": "t"})
        result = pipeline.prep([a, b], prof, out, window=20, do_center=False)
        codes = {f.code for f in result["report"].findings}
        self.assertNotIn("timestamps_out_of_order", codes)
        self.assertTrue(result["written"], msg=list(codes))

    def test_prep_refuses_shuffled_single_file(self):
        # databuilder-019: a shuffled input recording is caught by combine's per-file order check.
        import numpy as np
        df = H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60))
        t = np.arange(180) / 100.0
        t[90] = t[20]                          # big backward jump
        df["t"] = t
        p = _csv(df, self.d, "shuf.csv")
        out = os.path.join(self.d, "out.csv")
        prof = DatasetProfile.from_dict({**H.BASE_PROFILE, "sampling_rate_hz": 100, "time_column": "t"})
        result = pipeline.prep([p], prof, out, window=20, do_center=False)
        self.assertIn("timestamps_out_of_order", {f.code for f in result["report"].findings})
        self.assertFalse(result["written"])
        self.assertFalse(os.path.exists(out))


class TestOutputGuard(unittest.TestCase):
    """databuilder-013 C.2: prep must never destroy an input, and never write a .zip-named CSV."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.profile = _profile()

    def _inputs(self):
        a = _csv(H.block(0, 60), self.d, "idle.csv")
        b = _csv(H.concat(H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30)), self.d, "gest.csv")
        return a, b

    def _zip_input(self):
        import zipfile
        a, _b = self._inputs()
        z = os.path.join(self.d, "user.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(a, arcname="gestures.csv")
        return z

    def test_refuses_out_equals_input_zip(self):
        z = self._zip_input()
        before = _rb(z)
        r = pipeline.prep([z], self.profile, z, window=20)
        self.assertFalse(r["written"])
        self.assertIn("output_overwrites_input", [f.code for f in r["report"].findings])
        self.assertEqual(_rb(z), before)   # archive intact

    def test_write_anyway_does_not_override_guard(self):
        z = self._zip_input()
        before = _rb(z)
        pipeline.prep([z], self.profile, z, window=20, write_anyway=True)
        self.assertEqual(_rb(z), before)   # still intact — not forceable

    def test_refuses_out_symlink_to_input(self):
        a, b = self._inputs()
        before = _rb(a)
        link = os.path.join(self.d, "alias.csv")
        os.symlink(a, link)
        r = pipeline.prep([a, b], self.profile, link, window=20)
        self.assertFalse(r["written"])
        self.assertEqual(_rb(a), before)

    def test_refuses_out_dot_zip(self):
        a, b = self._inputs()
        r = pipeline.prep([a, b], self.profile, os.path.join(self.d, "out.zip"), window=20)
        self.assertFalse(r["written"])
        self.assertIn("output_not_csv", [f.code for f in r["report"].findings])

    def test_refuses_csv_out_equals_csv_input(self):
        a, b = self._inputs()
        before = _rb(a)
        r = pipeline.prep([a, b], self.profile, a, window=20)
        self.assertFalse(r["written"])
        self.assertEqual(_rb(a), before)

    def test_clean_zip_prep_matches_plain_csv(self):
        import zipfile
        a, b = self._inputs()
        z = os.path.join(self.d, "clean.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(a, arcname="idle.csv")
        o_csv = os.path.join(self.d, "o_csv.csv")
        o_zip = os.path.join(self.d, "o_zip.csv")
        r1 = pipeline.prep([a], self.profile, o_csv, window=20, write_anyway=True)
        r2 = pipeline.prep([z], self.profile, o_zip, window=20, write_anyway=True)
        self.assertTrue(r1["written"] and r2["written"])
        self.assertEqual(_rb(o_csv), _rb(o_zip))


if __name__ == "__main__":
    unittest.main()
