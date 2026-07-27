"""databuilder-016 (B5b) red->green: the prep / quality-report surface for Signal-Processing OFF.
Self-contained so the whole file can be copied over the parent tree for the P0.2 red run."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

import numpy as np

import _helpers as H
from data_builder import cli, pipeline, quality
from data_builder.profile import DatasetProfile
from data_builder.center import center_per_class
from data_builder.quality import SOURCE_COL


def _csv(df, d, name):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _gesture(label, n=240, peaks=6):
    rng = np.random.RandomState(label + 1)
    z = 0.01 * rng.randn(n)
    step = n // (peaks + 1)
    for k in range(1, peaks + 1):
        z[k * step - 1:k * step + 2] += 6.0
    df = H.pd.DataFrame({"acc_x": 0.01 * rng.randn(n), "acc_y": 0.01 * rng.randn(n), "acc_z": z})
    df["class"] = label
    return df


def _gesture_profile(**over):
    # BASE_PROFILE carries gesture_classes [1, 2] -> centering-would-engage.
    return DatasetProfile.from_dict(dict(H.BASE_PROFILE, sampling_rate_hz=100, **over))


def _tabular_profile(**over):
    # No class_encoding -> gesture_classes == [], so no contradiction; labels 0/1/2 stay contiguous.
    raw = {"dataset_name": "tab", "label_column": "class",
           "sensor_columns": ["acc_x", "acc_y", "acc_z"], "separator": "comma",
           "task_type": "multiclass_classification", "sampling_rate_hz": 100,
           "signal_processing": False}
    raw.update(over)
    return DatasetProfile.from_dict(raw)


def _write_profile(d, name, prof_raw):
    p = os.path.join(d, name)
    with open(p, "w") as fh:
        json.dump(prof_raw, fh)
    return p


def _run(argv):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            code = cli.main(argv)
    except SystemExit as e:
        code = e.code
    return code, buf.getvalue()


class TestSpOffPrepQuality(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _gesture_inputs(self):
        a = _csv(H.block(0, 200), self.d, "idle.csv")
        b = _csv(H.concat(_gesture(1), _gesture(2)), self.d, "gest.csv")
        return a, b

    # --- 1: SP-off + gesture_classes refuses (was: PASS, centered away rows) --------------------------

    def test_prep_sp_off_gesture_refused(self):
        a, b = self._gesture_inputs()
        out = os.path.join(self.d, "out.csv")
        r = pipeline.prep([a, b], _gesture_profile(signal_processing=False), out, window=20, sp_on=False)
        self.assertEqual(r["report"].verdict, "FIX_REQUIRED", msg=[f.code for f in r["report"].findings])
        self.assertFalse(r["written"])
        self.assertFalse(os.path.exists(out))
        self.assertIn("sp_off_contradicts_profile", [f.code for f in r["report"].findings])

    def test_prep_sp_off_gesture_write_anyway_writes_raw_rows(self):
        # The adversary's key invariant: --write-anyway must write the RAW (un-centered) frame, never the
        # centered one -- centering is skipped under SP off, not merely un-blocked.
        a, b = self._gesture_inputs()
        out = os.path.join(self.d, "out.csv")
        r = pipeline.prep([a, b], _gesture_profile(signal_processing=False), out, window=20,
                          sp_on=False, write_anyway=True)
        self.assertTrue(r["written"])
        self.assertEqual(len(H.pd.read_csv(out)), 200 + 480)   # 680 raw rows, nothing centered away

    # --- 2: SP-off tabular writes (PASS, no centering) ----------------------------------------------

    def test_prep_sp_off_tabular_writes(self):
        src = _csv(H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60)), self.d, "tab.csv")
        out = os.path.join(self.d, "tab_out.csv")
        r = pipeline.prep([src], _tabular_profile(), out, window=None, sp_on=False)
        self.assertEqual(r["report"].verdict, "PASS", msg=[f.code for f in r["report"].findings])
        self.assertTrue(r["written"])
        self.assertIn("sp_off_unverified", [f.code for f in r["report"].findings])
        self.assertEqual(len(H.pd.read_csv(out)), 180)          # unchanged (no centering)

    # --- 3: SP-off + --resample refuses (was: PASS, fabricated rows) --------------------------------

    def test_prep_sp_off_resample_refused(self):
        src = _csv(H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60)), self.d, "tab.csv")
        out = os.path.join(self.d, "rs_out.csv")
        r = pipeline.prep([src], _tabular_profile(time_column="t"), out, window=None,
                          sp_on=False, target_rate=200.0)
        self.assertEqual(r["report"].verdict, "FIX_REQUIRED")
        self.assertFalse(r["written"])
        self.assertIn("sp_off_resample_refused", [f.code for f in r["report"].findings])

    # --- 4: center_per_class(None) raises ValueError, not TypeError ---------------------------------

    def test_center_per_class_none_window_valueerror(self):
        df = H.concat(H.block(0, 60), H.block(1, 60, peak_at=30))
        with self.assertRaises(ValueError):
            center_per_class(df, _gesture_profile(), None)

    # --- 5: quality_report(window=None) with >=2 sources does not crash ----------------------------

    def test_quality_report_window_none_no_crash(self):
        def src(name):
            df = H.concat(H.block(0, 120), H.block(1, 120, peak_at=30))
            df[SOURCE_COL] = name
            return df
        df = H.concat(src("c1"), src("c2"))
        rep = quality.quality_report(df, _gesture_profile(), None, SOURCE_COL)   # was TypeError
        self.assertFalse(rep["comparison_ran"])
        self.assertTrue(rep["sources"])                          # per-source profiling still produced

    # --- 6: prep --window 0 on an SP-on profile is a loud usage error (was: silent substitution) ----

    def test_prep_window_zero_exit_4(self):
        src = _csv(H.concat(H.block(0, 60), H.block(1, 60, 30), H.block(2, 60, 30)), self.d, "s.csv")
        pj = _write_profile(self.d, "p.json", dict(H.BASE_PROFILE, sampling_rate_hz=100))
        out = os.path.join(self.d, "o.csv")
        code, _ = _run(["prep", src, "--profile", pj, "--out", out, "--window", "0"])
        self.assertEqual(code, 4)
        self.assertFalse(os.path.exists(out))

    # --- 7: SP-off + a supplied window -> sp_off_window_ignored advisory (json AND text) -------------

    def test_prep_sp_off_window_ignored_tell(self):
        src = _csv(H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60)), self.d, "s.csv")
        pj = _write_profile(self.d, "tab.json", {
            "dataset_name": "tab", "label_column": "class",
            "sensor_columns": ["acc_x", "acc_y", "acc_z"], "separator": "comma",
            "task_type": "multiclass_classification", "sampling_rate_hz": 100, "signal_processing": False})
        out = os.path.join(self.d, "o.csv")
        code, txt = _run(["prep", src, "--profile", pj, "--out", out, "--window", "20"])
        self.assertIn("the window from --window is ignored", txt)   # text mode (prep renders all groups)
        code, js = _run(["prep", src, "--profile", pj, "--out", out, "--window", "20", "--json"])
        self.assertIn("sp_off_window_ignored", [f["code"] for f in json.loads(js)["findings"]])

    def test_quality_sp_off_window_ignored_tell_text(self):
        s1 = _csv(H.concat(H.block(0, 120), H.block(1, 120, 30)), self.d, "a.csv")
        s2 = _csv(H.concat(H.block(0, 120), H.block(1, 120, 30)), self.d, "b.csv")
        pj = _write_profile(self.d, "tab.json", {
            "dataset_name": "tab", "label_column": "class",
            "sensor_columns": ["acc_x", "acc_y", "acc_z"], "separator": "comma",
            "task_type": "multiclass_classification", "sampling_rate_hz": 100, "signal_processing": False})
        code, txt = _run(["quality-report", s1, s2, "--profile", pj, "--window", "20"])
        self.assertEqual(code, 0)
        self.assertIn("the window from --window is ignored", txt)  # visible in TEXT mode (not just --json)
        self.assertIn("Source comparison not run", txt)

    # --- 8: the shipped skill brackets --window ----------------------------------------------------

    def test_skill_brackets_window(self):
        skill = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             ".claude", "skills", "nrf-prep-dataset", "SKILL.md")
        with open(skill, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("[--window <N>]", body)
        self.assertNotIn("--out output/<name>_upload_ready.csv --window <N>", body)  # old unbracketed form


if __name__ == "__main__":
    unittest.main()
