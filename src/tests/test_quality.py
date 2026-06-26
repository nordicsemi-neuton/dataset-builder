import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import numpy as np

import _helpers as H
from data_builder.quality import quality_report, SOURCE_COL
from data_builder import cli


def _src(source, label, n, scale, seed):
    rng = np.random.RandomState(seed)
    df = H.pd.DataFrame({c: scale * rng.randn(n) for c in ["acc_x", "acc_y", "acc_z"]})
    df["class"] = label
    df[SOURCE_COL] = source
    return df


def _qprofile():
    # no class_encoding (single synthetic class, non-contiguous label) — quality groups by raw label
    raw = {"dataset_name": "q", "label_column": "class", "sensor_columns": ["acc_x", "acc_y", "acc_z"],
           "separator": "comma", "task_type": "multiclass_classification"}
    from data_builder.profile import DatasetProfile
    return DatasetProfile.from_dict(raw)


class TestQuality(unittest.TestCase):
    def setUp(self):
        self.profile = _qprofile()

    def test_flags_outlier_source(self):
        # sources A,B normal; C records the class at 10x amplitude (a different feature regime)
        df = H.concat(_src("A", 1, 120, 1.0, 1), _src("B", 1, 120, 1.0, 2), _src("C", 1, 120, 10.0, 3))
        rep = quality_report(df, self.profile, window=20, source_col=SOURCE_COL)
        outlier_sources = {o["source"] for o in rep["outliers"]}
        self.assertIn("C", outlier_sources)
        self.assertNotIn("A", outlier_sources)
        self.assertNotIn("B", outlier_sources)

    def test_homogeneous_no_outlier(self):
        df = H.concat(_src("A", 1, 120, 1.0, 1), _src("B", 1, 120, 1.0, 2), _src("C", 1, 120, 1.0, 3))
        rep = quality_report(df, self.profile, window=20, source_col=SOURCE_COL)
        self.assertEqual(rep["outliers"], [])

    def test_insufficient_windows_reported(self):
        df = H.concat(_src("A", 1, 25, 1.0, 1), _src("B", 1, 25, 1.0, 2))  # ~1 window each < MIN_WINDOWS
        rep = quality_report(df, self.profile, window=20, source_col=SOURCE_COL)
        self.assertTrue(len(rep["insufficient"]) > 0)
        self.assertEqual(rep["outliers"], [])


class TestQualityCli(unittest.TestCase):
    def test_cli_multi_file_flags_outlier(self):
        d = tempfile.mkdtemp()

        def csv(name, scale, seed):
            rng = np.random.RandomState(seed)
            df = H.pd.DataFrame({c: scale * rng.randn(120) for c in ["acc_x", "acc_y", "acc_z"]})
            df["class"] = 1
            p = os.path.join(d, name)
            df.to_csv(p, index=False)
            return p
        fa, fb, fc = csv("a.csv", 1.0, 1), csv("b.csv", 1.0, 2), csv("c.csv", 10.0, 3)
        pj = os.path.join(d, "p.json")
        with open(pj, "w") as fh:
            json.dump({"dataset_name": "q", "label_column": "class",
                       "sensor_columns": ["acc_x", "acc_y", "acc_z"], "separator": "comma",
                       "task_type": "multiclass_classification"}, fh)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["quality-report", fa, fb, fc, "--profile", pj, "--window", "20", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(any(o["source"] == "c.csv" for o in payload["outliers"]))


if __name__ == "__main__":
    unittest.main()
