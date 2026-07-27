import os
import tempfile
import unittest

import _helpers as H
from data_builder import validate
from data_builder.findings import Severity, make_report


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


# databuilder-012 (B5a): with Signal Processing off, the window-based checks do not apply and are
# skipped; the mode is disclosed, never silently trusted. A tabular profile carries no gesture_classes.
_TAB = dict(sampling_rate_hz=100, class_encoding={"map": {"a": 0, "b": 1, "c": 2},
            "continuous_classes": [], "gesture_classes": []})

# The nine SP-only codes B5a gates. class_run_below_window / session_below_window are already dead on
# the check_dataframe(str-typed label) path, so they are not asserted here (they would pass regardless).
_SP_ONLY_ON_VALIDATE = ["window_out_of_range", "window_out_of_range_fft", "shift_exceeds_window",
                        "training_shift_not_window", "shift_unspecified", "enable_lr_features",
                        "mixed_sampling_rate", "window_class_yield"]   # window_class_yield: B8, SP-gated


class TestSignalProcessingGate(unittest.TestCase):
    def _codes(self, df, profile, window, sp_on):
        return {f.code for f in validate.check_dataframe(df, profile, window, sp_on=sp_on)}

    def test_legacy_sp_on_none_is_todays_behaviour(self):
        # sp_on omitted (every existing caller) == SP on: identical finding set to sp_on=True.
        df, prof = _passing_df(), H.prof(sampling_rate_hz=100)
        self.assertEqual(self._codes(df, prof, 20, None), self._codes(df, prof, 20, True))

    def test_sp_off_suppresses_every_window_only_code(self):
        # A nonsense window (5) and an over-window shift would fire under SP on; off, none of them do.
        prof = H.prof(window={"candidates": [5], "shift": 80, "frequency_domain_features": False}, **_TAB)
        off = self._codes(_passing_df(), prof, None, False)
        for code in _SP_ONLY_ON_VALIDATE:
            self.assertNotIn(code, off, msg=f"{code} should be suppressed with SP off")

    def test_sp_on_same_window_still_flags(self):
        # The contrast: the same bad window flags under SP on -> proves suppression is the field's doing.
        prof = H.prof(window={"candidates": [5], "shift": 80, "frequency_domain_features": False}, **_TAB)
        on = self._codes(_passing_df(), prof, 5, True)
        self.assertIn("window_out_of_range", on)

    def test_sp_off_emits_unverified_advisory(self):
        prof = H.prof(window=None, **_TAB)
        findings = validate.check_dataframe(_passing_df(), prof, None, sp_on=False)
        adv = [f for f in findings if f.code == "sp_off_unverified"]
        self.assertEqual(len(adv), 1)
        self.assertEqual(adv[0].severity, Severity.ADVISORY)

    def test_sp_off_with_gesture_classes_contradiction(self):
        prof = H.prof(sampling_rate_hz=100)  # BASE has gesture_classes [1, 2]
        findings = validate.check_dataframe(_passing_df(), prof, None, sp_on=False)
        c = [f for f in findings if f.code == "sp_off_contradicts_profile"]
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].severity, Severity.FIX_REQUIRED)

    def test_sp_off_still_flags_platform_rules(self):
        # Mode-independent rules must survive SP off. A missing label column is a HARD_REJECT either way.
        df = _passing_df().rename(columns={"class": "other"})
        findings = validate.check_dataframe(df, H.prof(window=None, **_TAB), None, sp_on=False)
        self.assertTrue(any(f.code == "label_column_missing" for f in findings))

    def test_no_mode_finding_when_sp_on_or_unspecified(self):
        # sp_off_* findings must never appear when the mode is on or unstated (byte-identity for all).
        df = _passing_df()
        for sp_on in (True, None):
            codes = self._codes(df, H.prof(sampling_rate_hz=100), 20, sp_on)
            self.assertNotIn("sp_off_unverified", codes)
            self.assertNotIn("sp_off_contradicts_profile", codes)


# databuilder-018 (B1a): the survival gate stops lying — a regression/anomaly target does not trip
# class-run findings, a blank label does not manufacture a false one, rate_unknown is mode-conditional,
# short_session is label-independent (but still SP-gated), and validate can reach exit 3.
class TestSurvivalGateB1a(unittest.TestCase):
    def _reg_frame(self, tgt):
        n = len(tgt)
        return H.pd.DataFrame({"acc_x": 0.01 * H.np.arange(n), "acc_y": H.np.zeros(n),
                               "acc_z": H.np.zeros(n), "class": tgt})

    def test_regression_target_no_class_run(self):
        # A regression target is a VALUE, not a class: min_run_ok must not run on it, even though a
        # short-run numeric column trips class_run_below_window under the old is_numeric_dtype guard.
        prof = H.prof(sampling_rate_hz=100, task_type="regression")
        for tgt in ([60] * 15 + [90] * 15 + [120] * 15,            # int64, integral (still coercible)
                    [60.5] * 15 + [90.5] * 15 + [120.5] * 15):     # float64, non-integral
            df = self._reg_frame(tgt)
            codes = {f.code for f in validate.check_dataframe(df, prof, window=20)}
            self.assertNotIn("class_run_below_window", codes, msg=f"dtype {df['class'].dtype}")

    def test_blank_label_no_false_class_run(self):
        # float64 label with one NaN splitting a TRUE 81-row run of class 0 into 40+40. The old guard
        # ran min_run_ok and reported max_run 40 (false WILL_LOSE_DATA); now the NaN makes the labels
        # not fully int-coercible, so min_run_ok is skipped. The blank is still a HARD_REJECT.
        lab = [0.0] * 40 + [float("nan")] + [0.0] * 40 + [1.0] * 60 + [2.0] * 60
        df = self._reg_frame(lab)
        codes = {f.code for f in validate.check_dataframe(df, H.prof(sampling_rate_hz=100), window=50)}
        self.assertNotIn("class_run_below_window", codes)
        self.assertIn("empty_or_na_value", codes)   # the blank is still caught, independently

    def test_rate_unknown_mode_conditional(self):
        # A gesture-less, rate-less, time-less 2-class frame. SP off -> rate not load-bearing ->
        # ADVISORY + verdict PASS; SP on / legacy None -> FIX_REQUIRED (window math is in samples).
        prof = H.prof(sampling_rate_hz=None, time_column=None,
                      class_encoding={"map": {"a": 0, "b": 1}, "gesture_classes": [],
                                      "continuous_classes": []})
        df = H.concat(H.block(0, 30), H.block(1, 30))
        off = validate.check_dataframe(df, prof, None, sp_on=False)
        ru = [f for f in off if f.code == "rate_unknown"]
        self.assertEqual(len(ru), 1)
        self.assertEqual(ru[0].severity, Severity.ADVISORY)
        self.assertEqual(make_report(off).verdict, "PASS")
        for sp in (True, None):
            on = validate.check_dataframe(df, prof, 20, sp_on=sp)
            ru = [f for f in on if f.code == "rate_unknown"]
            self.assertEqual(ru[0].severity, Severity.FIX_REQUIRED, msg=f"sp_on={sp}")
            self.assertEqual(make_report(on).verdict, "FIX_REQUIRED", msg=f"sp_on={sp}")

    def test_short_session_independent_of_label_dtype(self):
        # short_session_findings is label-independent: it must run for OBJECT labels too (where the old
        # is_numeric_dtype guard skipped it), but only inside the SP gate.
        d = H.concat(H.block("0", 60), H.block("1", 60), H.block("2", 8))
        d["sess"] = ["s1"] * 120 + ["s2"] * 8
        d["class"] = d["class"].astype(object)
        prof = H.prof(sampling_rate_hz=100, session_column="sess")
        on = {f.code for f in validate.check_dataframe(d, prof, window=20, sp_on=True)}
        self.assertIn("session_below_window", on)                     # (a) activated on the object path
        off = {f.code for f in validate.check_dataframe(d, prof, None, sp_on=False)}
        self.assertNotIn("session_below_window", off)                 # (b) still gated by `if _win:`

    def test_validate_exit3_reachable(self):
        # The validate surface (str labels via read_table) can now reach WILL_LOSE_DATA / exit 3.
        # Rate set so rate_unknown (FIX_REQUIRED) does not outrank/mask the WILL_LOSE_DATA verdict.
        d = tempfile.mkdtemp()
        df = H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 30), H.block(1, 12), H.block(2, 60))
        p = os.path.join(d, "short_runs.csv")
        df.to_csv(p, index=False)
        report = validate.run_checks(p, H.prof(sampling_rate_hz=100), window=20)
        self.assertEqual(report.verdict, "WILL_LOSE_DATA",
                         msg=[f"{f.code}:{f.severity}" for f in report.findings])


# databuilder-019 (B1b): the validate surface no longer hides shuffled row order. check_time_order runs
# in run_checks on the single uploaded file, gated on the SP mode.
class TestTimeOrderB1b(unittest.TestCase):
    def _shuffled_csv(self, d, name="shuffled.csv"):
        df = H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60))
        t = H.np.arange(180) / 100.0
        t[90] = t[20]                          # a big backward jump mid-stream
        df["t"] = t
        p = os.path.join(d, name)
        df.to_csv(p, index=False)
        return p

    def test_shuffled_timestamps_flagged_via_run_checks(self):
        # The file->str read path end to end (read_table gives object columns; check_time_order coerces).
        p = self._shuffled_csv(tempfile.mkdtemp())
        prof = H.prof(sampling_rate_hz=100, time_column="t")
        report = validate.run_checks(p, prof, window=20)
        self.assertIn("timestamps_out_of_order", {f.code for f in report.findings})
        self.assertEqual(report.verdict, "FIX_REQUIRED")

    def test_sp_off_skips_time_order(self):
        p = self._shuffled_csv(tempfile.mkdtemp())
        prof = H.prof(sampling_rate_hz=100, time_column="t")
        on = {f.code for f in validate.run_checks(p, prof, window=20, sp_on=True).findings}
        self.assertIn("timestamps_out_of_order", on)                # SP on -> checked
        off = {f.code for f in validate.run_checks(p, prof, None, sp_on=False).findings}
        self.assertNotIn("timestamps_out_of_order", off)            # SP off -> row order irrelevant


# databuilder-020 (B8): the validator reports what the platform trains on — WINDOWS, not rows. A
# row-balanced dataset can be window-imbalanced; both findings are verdict-neutral and SP-gated.
class TestWindowYieldB8(unittest.TestCase):
    def _row_balanced_window_imbalanced(self):
        # rows 120/120/120; pure windows {0:6, 1:2, 2:5} at window 20 (measured)
        order = [H.block(0, 120)]
        for _ in range(6):
            order += [H.block(1, 20), H.block(2, 4)]
        order += [H.block(2, 96)]
        return H.concat(*order)

    def test_window_class_yield_reported(self):
        findings = validate.check_dataframe(_passing_df(), H.prof(sampling_rate_hz=100), window=20)
        y = [f for f in findings if f.code == "window_class_yield"]
        self.assertEqual(len(y), 1)
        self.assertIsInstance(y[0].data["pure_windows"], dict)
        self.assertEqual(sorted(y[0].data["pure_windows"]), [0, 1, 2])

    def test_window_imbalance_row_balanced(self):
        codes = {f.code for f in validate.check_dataframe(self._row_balanced_window_imbalanced(),
                                                          H.prof(sampling_rate_hz=100), window=20)}
        self.assertIn("window_class_imbalance", codes)
        self.assertNotIn("class_imbalance", codes)      # row view stays silent -> window view catches it

    def test_window_yield_sp_off_skipped(self):
        df = _passing_df()
        prof = H.prof(**_TAB)                            # tabular, gesture-less (_TAB carries the rate)
        on = {f.code for f in validate.check_dataframe(df, prof, 20, sp_on=True)}
        self.assertIn("window_class_yield", on)
        off = {f.code for f in validate.check_dataframe(df, prof, None, sp_on=False)}
        self.assertNotIn("window_class_yield", off)
        self.assertNotIn("window_class_imbalance", off)

    def test_window_yield_verdict_neutral(self):
        r1 = make_report(validate.check_dataframe(_passing_df(), H.prof(sampling_rate_hz=100), window=20))
        self.assertEqual(r1.verdict, "PASS")
        self.assertIn("window_class_yield", {f.code for f in r1.findings})
        imb = validate.check_dataframe(self._row_balanced_window_imbalanced(),
                                       H.prof(sampling_rate_hz=100), window=20)
        self.assertEqual(make_report(imb).verdict, "PASS")          # ADVISORY does not block
        self.assertIn("window_class_imbalance", {f.code for f in imb})
        # a frame with a zero-yield class ({0:5,1:0,2:2}) -> imbalance not misfired (survivor filter)
        z = H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 60), H.block(1, 12), H.block(2, 60))
        zc = {f.code for f in validate.check_dataframe(z, H.prof(sampling_rate_hz=100), window=20)}
        self.assertIn("window_class_yield", zc)
        self.assertNotIn("window_class_imbalance", zc)


if __name__ == "__main__":
    unittest.main()
