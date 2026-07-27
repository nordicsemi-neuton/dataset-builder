"""databuilder-010 (sprint B2) — regression must not be class-encoded; a missing label column blocks.

8 of the 9 tests here are red on 532ed98. The exception is
test_blocked_run_leaves_previous_artifacts_untouched, which is green on the parent (the parent never
deletes anything) — it guards the *placement* of the removal, after the blocking return.
Note the recipe below only works once the fix is COMMITTED; run on uncommitted work it reverts it.
Demonstrate with:
    git checkout 532ed98 -- src/data_builder/pipeline.py src/data_builder/validate.py \
                            src/data_builder/cli.py
    python3 -m unittest discover -s src/tests
    git checkout HEAD -- src/data_builder/pipeline.py src/data_builder/validate.py \
                         src/data_builder/cli.py
"""
import json
import os
import tempfile
import unittest

import pandas as pd

import _helpers as H
from data_builder.profile import DatasetProfile
from data_builder import pipeline


def _csv(df, d, name="in.csv"):
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _reg_profile(**over):
    raw = dict(H.BASE_PROFILE)
    raw["label_column"] = "hr"
    raw["task_type"] = "regression"
    raw.pop("class_encoding", None)
    raw["sampling_rate_hz"] = 100
    raw.update(over)
    return DatasetProfile.from_dict(raw)


def _reg_frame(values, n_each=60):
    """Block-structured continuous target: each value held for n_each contiguous rows."""
    parts = []
    for v in values:
        b = H.block(0, n_each)
        b = b.drop(columns=["class"])
        b["hr"] = v
        parts.append(b)
    return pd.concat(parts, ignore_index=True)


class TestRegressionTargetPreserved(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.out = os.path.join(self.d, "out.csv")

    def _run(self, df, profile=None, **kw):
        return pipeline.prep([_csv(df, self.d)], profile or _reg_profile(),
                             self.out, window=20, **kw)

    def test_block_target_values_preserved_and_no_dictionary(self):
        """Red on parent: target rank-encoded to [0,1,2] and a dictionary written."""
        res = self._run(_reg_frame([2.5, 10.1, 0.3]))
        self.assertTrue(res["written"], res["report"].verdict)
        got = sorted(pd.read_csv(self.out)["hr"].unique().tolist())
        self.assertEqual(got, [0.3, 2.5, 10.1])
        self.assertIsNone(res["dictionary_path"])
        self.assertFalse(os.path.exists(os.path.splitext(self.out)[0] + "_dictionary.json"))

    def test_integer_valued_target_is_not_a_noncontiguous_label_error(self):
        """Red on parent: [60,90,120] tripped noncontiguous_labels, FIX_REQUIRED."""
        res = self._run(_reg_frame([60, 90, 120]))
        codes = {f.code for f in res["report"].findings}
        self.assertNotIn("noncontiguous_labels", codes)
        self.assertNotIn("string_labels_encoded", codes)
        self.assertEqual(res["report"].verdict, "PASS")
        self.assertTrue(res["written"])
        self.assertEqual(sorted(pd.read_csv(self.out)["hr"].unique().tolist()), [60, 90, 120])

    def test_constant_target_is_not_a_label_error(self):
        res = self._run(_reg_frame([7.0], n_each=180))
        codes = {f.code for f in res["report"].findings}
        self.assertNotIn("noncontiguous_labels", codes)
        self.assertEqual(res["report"].verdict, "PASS")
        self.assertTrue(res["written"])
        self.assertEqual(pd.read_csv(self.out)["hr"].unique().tolist(), [7.0])

    def test_stale_dictionary_removed_on_regression_rebuild(self):
        """A classification run then a regression run to the same --out must not leave a class map."""
        dpath = os.path.splitext(self.out)[0] + "_dictionary.json"
        with open(dpath, "w", encoding="utf-8") as fh:
            json.dump({"idle": 0}, fh)
        res = self._run(_reg_frame([2.5, 10.1, 0.3]))
        self.assertTrue(res["written"])
        self.assertFalse(os.path.exists(dpath), "stale dictionary describing a different dataset")
        self.assertIn("stale_dictionary_removed", {f.code for f in res["report"].findings})

    def test_blocked_run_leaves_previous_artifacts_untouched(self):
        dpath = os.path.splitext(self.out)[0] + "_dictionary.json"
        with open(dpath, "w", encoding="utf-8") as fh:
            json.dump({"idle": 0}, fh)
        df = _reg_frame([2.5, 10.1, 0.3])
        df["hr"] = df["hr"].astype(object)
        df.loc[0, "hr"] = "abc"          # unrepairable -> blocking
        res = self._run(df)
        self.assertFalse(res["written"])
        self.assertTrue(os.path.exists(dpath), "a blocked run must not delete anything")


class TestMissingLabelColumn(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.out = os.path.join(self.d, "out.csv")

    def _frame_without_label(self):
        return _reg_frame([2.5, 10.1, 0.3]).drop(columns=["hr"])

    def _run(self, profile):
        return pipeline.prep([_csv(self._frame_without_label(), self.d)], profile,
                             self.out, window=20)

    def test_prep_regression_blocks(self):
        """Red on parent: KeyError -> exit 1."""
        res = self._run(_reg_profile())
        self.assertIn("label_column_missing", {f.code for f in res["report"].findings})
        self.assertFalse(res["written"])

    def test_prep_classification_blocks_without_crashing(self):
        """Red on parent: KeyError inside relabel_contiguous."""
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        res = self._run(DatasetProfile.from_dict(raw))
        self.assertIn("label_column_missing", {f.code for f in res["report"].findings})
        self.assertFalse(res["written"])

    def test_anomaly_detection_is_exempt(self):
        """The platform documents anomaly data as having no target column."""
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        raw["task_type"] = "anomaly_detection"
        raw.pop("class_encoding", None)
        res = self._run(DatasetProfile.from_dict(raw))
        self.assertNotIn("label_column_missing", {f.code for f in res["report"].findings})

    def test_anomaly_no_label_writes_no_dictionary_and_reconciles_a_stale_one(self):
        """Guard: this path once wrote a file containing `null`, clobbering a real class map."""
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        raw["task_type"] = "anomaly_detection"
        raw["sampling_rate_hz"] = 100          # else rate_unknown blocks the write
        raw.pop("class_encoding", None)
        dpath = os.path.splitext(self.out)[0] + "_dictionary.json"
        with open(dpath, "w", encoding="utf-8") as fh:
            json.dump({"idle": 0, "left": 1}, fh)          # a real map from an earlier run
        res = pipeline.prep([_csv(self._frame_without_label(), self.d)],
                            DatasetProfile.from_dict(raw), self.out, window=20)
        self.assertTrue(res["written"])
        self.assertIsNone(res["dictionary_path"], "must not write a `null` dictionary")
        # The earlier run's class map does not describe this dataset, which has no classes at all:
        # remove it and say so, rather than leaving it to travel with the upload.
        self.assertFalse(os.path.exists(dpath))
        self.assertIn("stale_dictionary_removed", {f.code for f in res["report"].findings})

    def test_unrecognised_file_at_dictionary_path_is_not_deleted(self):
        """A file we cannot identify is never removed — it is reported instead."""
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        raw["task_type"] = "regression"
        raw["sampling_rate_hz"] = 100
        raw.pop("class_encoding", None)
        dpath = os.path.splitext(self.out)[0] + "_dictionary.json"
        with open(dpath, "w", encoding="utf-8") as fh:
            fh.write("MY HAND-WRITTEN COLUMN NOTES\n")
        res = pipeline.prep([_csv(_reg_frame([2.5, 10.1, 0.3]), self.d)],
                            DatasetProfile.from_dict(raw), self.out, window=20)
        self.assertTrue(os.path.exists(dpath), "deleted a file it could not identify")
        codes = {f.code for f in res["report"].findings}
        self.assertIn("unrecognised_file_at_dictionary_path", codes)
        self.assertNotIn("stale_dictionary_removed", codes)
        self.assertEqual(res["report"].verdict, "FIX_REQUIRED")

    def test_undeletable_stale_dictionary_blocks_rather_than_passing(self):
        """A directory at the dictionary path used to end at PASS while telling the user to fix it."""
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        raw["task_type"] = "regression"
        raw["sampling_rate_hz"] = 100
        raw.pop("class_encoding", None)
        dpath = os.path.splitext(self.out)[0] + "_dictionary.json"
        os.makedirs(dpath, exist_ok=True)
        res = pipeline.prep([_csv(_reg_frame([2.5, 10.1, 0.3]), self.d)],
                            DatasetProfile.from_dict(raw), self.out, window=20)
        self.assertEqual(res["report"].verdict, "FIX_REQUIRED")
        self.assertIn("unrecognised_file_at_dictionary_path",
                      {f.code for f in res["report"].findings})

    def test_validate_blocks_for_classification_too(self):
        from data_builder import validate
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        findings = validate.check_dataframe(self._frame_without_label(),
                                            DatasetProfile.from_dict(raw), window=20)
        self.assertIn("label_column_missing", {f.code for f in findings})

    def test_validate_path_also_blocks(self):
        """Red on parent: standalone validate returned PASS on a label-less CSV."""
        from data_builder import validate
        df = self._frame_without_label()
        findings = validate.check_dataframe(df, _reg_profile(), window=20)
        self.assertIn("label_column_missing", {f.code for f in findings})


if __name__ == "__main__":
    unittest.main()


class TestCliDictionaryPrint(unittest.TestCase):
    def test_no_and_none_in_written_message(self):
        """Red on parent: printed 'Wrote out.csv and None.' for a regression run."""
        import io
        import json as _json
        from contextlib import redirect_stdout
        from data_builder import cli

        d = tempfile.mkdtemp()
        src = _csv(_reg_frame([2.5, 10.1, 0.3]), d)
        pj = os.path.join(d, "p.json")
        raw = dict(H.BASE_PROFILE)
        raw["label_column"] = "hr"
        raw["task_type"] = "regression"
        raw["sampling_rate_hz"] = 100          # else rate_unknown blocks the write
        raw.pop("class_encoding", None)
        with open(pj, "w", encoding="utf-8") as fh:
            _json.dump(raw, fh)
        out = os.path.join(d, "out.csv")
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["prep", src, "--profile", pj, "--out", out, "--window", "20"])
        text = buf.getvalue()
        self.assertIn("Wrote", text)
        self.assertNotIn("and None", text)
