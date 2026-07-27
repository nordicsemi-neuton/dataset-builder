"""databuilder-017 (B9) red->green: quality-report must not crash on a missing label column, and two
surfaces must stop dropping intake findings. Self-contained (inline zip fixtures, no _helpers import of
zip builders) so the whole file can be copied over the parent tree for the P0.2 red run."""
import io
import json
import os
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr

import _helpers as H
from data_builder import cli, quality
from data_builder.profile import DatasetProfile


def _csv(df, d, name):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _passing_df():
    return H.concat(H.block(0, 60), H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30))


def _profile_json(d, name, **over):
    raw = {"dataset_name": "q", "label_column": "class",
           "sensor_columns": ["acc_x", "acc_y", "acc_z"], "separator": "comma",
           "task_type": "multiclass_classification"}
    raw.update(over)
    p = os.path.join(d, name)
    with open(p, "w") as fh:
        json.dump(raw, fh)
    return p


def _run(argv):
    """Run cli.main, capturing stdout+stderr; never let a traceback escape as exit 1 undetected."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            code = cli.main(argv)
    except SystemExit as e:            # profile/usage errors raise SystemExit(4); keep that as the code
        code = e.code
    return code, buf.getvalue()


class TestQualityCrashB9(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    # --- Defect 1: crash on a missing label column ---------------------------------------------------

    def test_missing_label_no_traceback_exit_2(self):
        nolabel = _csv(H.pd.DataFrame({"acc_x": [1.0] * 30, "acc_y": [1.0] * 30, "acc_z": [1.0] * 30}),
                       self.d, "nolabel.csv")
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", nolabel, "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 2, msg=out)                       # was exit 1 (KeyError traceback)
        self.assertIn("label_column_missing", [f["code"] for f in json.loads(out)["findings"]])

    def test_missing_label_text_mode_does_not_crash(self):
        # The renderer read class_counts unconditionally; the no-label path must not KeyError in text mode.
        nolabel = _csv(H.pd.DataFrame({"acc_x": [1.0] * 30, "acc_y": [1.0] * 30, "acc_z": [1.0] * 30}),
                       self.d, "nolabel.csv")
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", nolabel, "--profile", pj, "--window", "20"])
        self.assertEqual(code, 2, msg=out)
        self.assertIn("target column", out)                      # the finding message rendered, no crash

    def test_missing_label_anomaly_detection_exempt(self):
        nolabel = _csv(H.pd.DataFrame({"acc_x": [1.0] * 30, "acc_y": [1.0] * 30, "acc_z": [1.0] * 30}),
                       self.d, "nolabel.csv")
        pj = _profile_json(self.d, "anom.json", task_type="anomaly_detection")
        code, out = _run(["quality-report", nolabel, "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 0, msg=out)                       # exempt: no finding, degenerate profile
        payload = json.loads(out)
        self.assertNotIn("label_column_missing", [f["code"] for f in payload["findings"]])
        self.assertEqual(payload["sources"][0]["rows"], 30)      # per-source ROW counts still produced
        self.assertEqual(payload["sources"][0]["class_counts"], {})

    # --- Defect 2/2b: dropped intake findings on quality-report ---------------------------------------

    def _bad_zip(self, name="bad.zip"):
        p = os.path.join(self.d, name)
        with open(p, "wb") as fh:
            fh.write(b"this is not a zip archive at all")
        return p

    def test_unreadable_zip_sole_input_surfaces_finding(self):
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", self._bad_zip(), "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 2, msg=out)                       # was exit 4, generic message
        self.assertIn("zip_unreadable", [f["code"] for f in json.loads(out)["findings"]])

    def test_unreadable_zip_among_readable_inputs(self):
        good = _csv(H.concat(H.block(0, 120), H.block(1, 120, peak_at=30)), self.d, "good.csv")
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", good, self._bad_zip(), "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 2, msg=out)                       # was exit 0, finding dropped
        payload = json.loads(out)
        self.assertIn("zip_unreadable", [f["code"] for f in payload["findings"]])
        self.assertTrue(payload["sources"])                      # the readable source is still profiled

    # --- Defect: false "no different feature regime" reassurance -------------------------------------

    def test_single_source_no_false_reassurance(self):
        one = _csv(H.concat(H.block(0, 120), H.block(1, 120, peak_at=30)), self.d, "one.csv")
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", one, "--profile", pj, "--window", "20"])
        self.assertEqual(code, 0, msg=out)
        self.assertNotIn("No source looks like a different feature regime", out)
        self.assertIn("Source comparison not run", out)

    # --- Defect 3: validate --holdout drops the holdout's raw-byte findings -------------------------

    def test_holdout_zip_illegal_inner_name_surfaced(self):
        train = _csv(_passing_df(), self.d, "train.csv")
        holdsrc = _csv(_passing_df(), self.d, "hold_src.csv")
        holdzip = os.path.join(self.d, "hold.zip")
        with zipfile.ZipFile(holdzip, "w") as zf:
            zf.write(holdsrc, arcname="bad name v2.csv")         # readable member, illegal inner name
        pj = _profile_json(self.d, "p.json", sampling_rate_hz=100)
        code, out = _run(["validate", train, "--profile", pj, "--window", "20",
                          "--holdout", holdzip, "--json"])
        self.assertIn("zip_inner_file_name", [f["code"] for f in json.loads(out)["findings"]])

    # --- Non-regression: clean multi-file quality-report unchanged (exit 0, backward-compatible JSON) -

    def test_clean_multi_file_exit_0_payload_compatible(self):
        import numpy as np

        def csv(name, scale, seed):
            rng = np.random.RandomState(seed)
            df = H.pd.DataFrame({c: scale * rng.randn(120) for c in ["acc_x", "acc_y", "acc_z"]})
            df["class"] = 1
            return _csv(df, self.d, name)
        fa, fb, fc = csv("a.csv", 1.0, 1), csv("b.csv", 1.0, 2), csv("c.csv", 10.0, 3)
        pj = _profile_json(self.d, "p.json")
        code, out = _run(["quality-report", fa, fb, fc, "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 0, msg=out)
        payload = json.loads(out)
        self.assertTrue(any(o["source"] == "c.csv" for o in payload["outliers"]))   # existing key intact
        for k in ("source_col", "sources", "outliers", "insufficient", "threshold_d", "note"):
            self.assertIn(k, payload)


if __name__ == "__main__":
    unittest.main()
