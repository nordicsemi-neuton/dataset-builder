"""Regression tests for the implementation-gate findings (overflow, inf, resample columns, label gating)."""
import unittest

import numpy as np

import _helpers as H
from data_builder.normalize import normalize_numeric
from data_builder.csv_io import _format_value
from data_builder.resample import resample_to_rate
from data_builder import validate
from data_builder.findings import Severity


class TestOverflow(unittest.TestCase):
    def test_huge_int_does_not_crash(self):
        df = H.pd.DataFrame({"t": ["99999999999999999999", "1", "2"]})
        out, findings = normalize_numeric(df, ["t"])      # must not raise OverflowError
        self.assertTrue(H.pd.api.types.is_float_dtype(out["t"]))


class TestFormatValue(unittest.TestCase):
    def test_inf_does_not_crash(self):
        self.assertEqual(_format_value(float("inf")), "")
        self.assertEqual(_format_value(float("-inf")), "")
        self.assertEqual(_format_value(float("nan")), "")

    def test_no_scientific_notation(self):
        self.assertNotIn("e", _format_value(0.00001).lower())


class TestResampleColumns(unittest.TestCase):
    def test_undeclared_column_dropped_not_nan_injected(self):
        n = 60
        t = np.arange(n) / 50.0
        df = H.pd.DataFrame({"acc_x": 0.01 * np.arange(n), "acc_y": np.zeros(n), "acc_z": np.full(n, 9.78),
                             "t": t, "class": [0] * 30 + [1] * 30, "extra": ["junk"] * n})
        profile = H.prof(time_column="t")
        out, findings = resample_to_rate(df, "t", 100, ["acc_x", "acc_y", "acc_z"], "class", None, "s")
        self.assertNotIn("extra", out.columns)          # dropped, not NaN-injected
        self.assertFalse(out.isna().any().any())        # no NaN anywhere
        self.assertTrue(any(f.code == "columns_dropped_on_resample" for f in findings))


class TestLabelGating(unittest.TestCase):
    def test_partial_numeric_labels_skip_structure_checks(self):
        # labels 0,1 numeric + 'x' non-numeric; structure checks must be skipped (bad rows flagged elsewhere)
        df = H.concat(H.block(0, 30), H.block(1, 30))
        df["class"] = df["class"].astype(object)
        df.loc[5, "class"] = "x"
        findings = validate.check_dataframe(df, H.prof(sampling_rate_hz=100), window=20)
        codes = {f.code for f in findings}
        self.assertIn("labels_not_numeric", codes)
        self.assertNotIn("noncontiguous_target", codes)  # not computed on the partial set
        self.assertTrue(any(f.code == "non_numeric_value" for f in findings))


class TestShiftSeverity(unittest.TestCase):
    def test_shift_exceeds_window_is_hard_reject(self):
        profile = H.prof(sampling_rate_hz=100, window={"candidates": [20], "shift": 50,
                                                       "frequency_domain_features": False})
        df = H.concat(H.block(0, 60), H.block(1, 60))
        findings = validate.check_dataframe(df, profile, window=20)
        f = [x for x in findings if x.code == "shift_exceeds_window"][0]
        self.assertEqual(f.severity, Severity.HARD_REJECT)


if __name__ == "__main__":
    unittest.main()
