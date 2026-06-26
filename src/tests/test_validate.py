import unittest

import _helpers as H
from data_builder import validate
from data_builder.findings import Severity


def _passing_df():
    return H.concat(H.block(0, 60), H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30))


class TestFilename(unittest.TestCase):
    def test_space_rejected(self):
        self.assertIsNotNone(validate.check_filename("swipe data.csv"))

    def test_dot_in_stem_rejected(self):
        self.assertIsNotNone(validate.check_filename("dataset.v2.csv"))

    def test_clean_name_ok(self):
        self.assertIsNone(validate.check_filename("gesture_set-1.csv"))


class TestCheckDataframe(unittest.TestCase):
    def setUp(self):
        self.profile = H.prof(sampling_rate_hz=100)

    def _has(self, findings, code):
        return any(f.code == code for f in findings)

    def test_passing_dataset(self):
        findings = validate.check_dataframe(_passing_df(), self.profile, window=20)
        blocking = [f for f in findings if f.severity in (Severity.HARD_REJECT, Severity.FIX_REQUIRED,
                                                           Severity.WILL_LOSE_DATA)]
        self.assertEqual(blocking, [], msg=[f.code for f in blocking])

    def test_too_few_classes(self):
        df = H.block(0, 60)
        findings = validate.check_dataframe(df, self.profile, window=20)
        self.assertTrue(self._has(findings, "too_few_classes"))

    def test_class_below_min_samples(self):
        df = H.concat(H.block(0, 60), H.block(1, 10))
        findings = validate.check_dataframe(df, self.profile, window=5)
        self.assertTrue(self._has(findings, "class_below_min_samples"))

    def test_window_out_of_range(self):
        findings = validate.check_dataframe(_passing_df(), self.profile, window=5)
        self.assertTrue(self._has(findings, "window_out_of_range"))

    def test_shift_exceeds_window(self):
        profile = H.prof(sampling_rate_hz=100, window={"candidates": [20], "shift": 50,
                                                       "frequency_domain_features": False})
        findings = validate.check_dataframe(_passing_df(), profile, window=20)
        self.assertTrue(self._has(findings, "shift_exceeds_window"))

    def test_will_lose_data_on_short_run(self):
        df = H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 30), H.block(1, 12), H.block(2, 60))
        findings = validate.check_dataframe(df, self.profile, window=20)
        self.assertTrue(self._has(findings, "class_run_below_window"))

    def test_holdout_column_order(self):
        df = _passing_df()
        holdout = df.rename(columns={"acc_x": "AAA"})
        findings = validate.check_dataframe(df, self.profile, window=20, holdout_df=holdout)
        self.assertTrue(self._has(findings, "holdout_column_order"))

    def test_axon_recommends_float32(self):
        profile = H.prof(sampling_rate_hz=100, target_technology="axon")
        findings = validate.check_dataframe(_passing_df(), profile, window=20)
        rec = [f for f in findings if f.code == "recommended_dtype"][0]
        self.assertEqual(rec.data["dtype"], "FLOAT32")


if __name__ == "__main__":
    unittest.main()
