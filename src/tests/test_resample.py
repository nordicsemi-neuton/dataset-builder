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


def _int_timed(label, t0, n, hz):
    """A varying all-integral sensor set in the INT16 band (>127, so recommend_dtype -> INT16), with a
    monotone time column. Integer step is odd so linear interpolation lands off the integers (fractional
    on the parent commit -> the red half of the red->green)."""
    t = t0 + np.arange(n) / hz
    x = (150 + (np.arange(n) * 7) % 200).astype(np.int64)
    y = (200 + (np.arange(n) * 3) % 100).astype(np.int64)
    z = (300 - (np.arange(n) * 5) % 150).astype(np.int64)
    df = H.pd.DataFrame({"acc_x": x, "acc_y": y, "acc_z": z, "t": t, "class": label})
    return df


def _float_timed(label, t0, n, hz):
    """Every sensor axis genuinely fractional (must NOT reuse _timed, which sets acc_y=zeros -- an
    integral axis that would fire resample_integer_preserved)."""
    t = t0 + np.arange(n) / hz
    df = H.pd.DataFrame({"acc_x": 9.78 + 0.01 * np.arange(n),
                         "acc_y": 1.50 - 0.002 * np.arange(n),
                         "acc_z": 0.30 + 0.001 * np.arange(n),
                         "t": t, "class": label})
    return df


class TestResampleIntegerPreservation(unittest.TestCase):
    """databuilder-021 / B4 -- ADR-0004."""
    sensors = ["acc_x", "acc_y", "acc_z"]

    def _finding(self, findings):
        return next((f for f in findings if f.code == "resample_integer_preserved"), None)

    def test_integral_column_rounded_back_upsample(self):
        df = _int_timed(0, 0.0, 60, 50)
        out, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        for c in self.sensors:
            self.assertTrue(np.all(np.mod(out[c].to_numpy(), 1) == 0), msg=f"{c} not whole after upsample")
        f = self._finding(findings)
        self.assertIsNotNone(f, "resample_integer_preserved missing on upsample of integral data")
        self.assertCountEqual(f.data["columns"], self.sensors)

    def test_integral_column_rounded_back_downsample(self):
        # 200-row run so the 100->50 anti-alias downsample has enough samples (needs >=123).
        df = _int_timed(0, 0.0, 200, 100)
        out, findings = resample_to_rate(df, "t", 50, self.sensors, "class", None, "s")
        for c in self.sensors:
            self.assertTrue(np.all(np.mod(out[c].to_numpy(), 1) == 0), msg=f"{c} not whole after downsample")
        self.assertIsNotNone(self._finding(findings), "finding missing on downsample of integral data")

    def test_float_columns_not_rounded(self):
        df = _float_timed(0, 0.0, 60, 50)
        _, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        f = self._finding(findings)
        cols = f.data["columns"] if f else []
        for c in self.sensors:
            self.assertNotIn(c, cols, f"{c} is genuinely fractional and must not be rounded")

    def test_all_refused_does_not_claim_rounding(self):
        # Every run refused (duplicate timestamp -> nonmonotonic): nothing is resampled, so the
        # preservation finding must be ABSENT (it would otherwise claim a change that never happened).
        df = _int_timed(0, 0.0, 30, 50)
        df.loc[5, "t"] = df.loc[4, "t"]
        out, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        self.assertTrue(any(f.code == "nonmonotonic_timestamps" for f in findings))
        self.assertIsNone(self._finding(findings), "finding fired though no run was resampled")
        # integral columns pass through byte-unchanged (values equal the source ints)
        self.assertTrue(np.array_equal(out["acc_x"].to_numpy().astype(np.int64),
                                       df["acc_x"].to_numpy()))

    def test_string_input_refused_run_no_crash(self):
        # Direct caller passes string-typed integral sensor columns; one run resamples, one is refused ->
        # the concatenated column is object dtype. The round-site coercion must not raise (guards the
        # object-dtype np.round TypeError the spec gate found).
        a = _int_timed(0, 0.0, 30, 50)
        b = _int_timed(1, 1.0, 30, 50)
        b.loc[b.index[3], "t"] = b["t"].iloc[2]   # refuse run 1
        df = H.concat(a, b)
        for c in self.sensors:
            df[c] = df[c].astype(str)
        out, findings = resample_to_rate(df, "t", 100, self.sensors, "class", None, "s")
        self.assertTrue(np.all(np.mod(H.pd.to_numeric(out["acc_x"]).to_numpy(), 1) == 0))


if __name__ == "__main__":
    unittest.main()
