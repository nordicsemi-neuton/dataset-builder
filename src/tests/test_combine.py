import os
import tempfile
import unittest

import _helpers as H
from data_builder.combine import combine_recordings, CombineError


def _write_csv(df, d, name):
    path = os.path.join(d, name)
    df.to_csv(path, index=False)
    return path


class TestCombine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.profile = H.prof()

    def test_single_header_concat(self):
        a = H.block(0, 30)
        b = H.block(1, 30)
        pa = _write_csv(a, self.d, "a.csv")
        pb = _write_csv(b, self.d, "b.csv")
        df, _ = combine_recordings([pa, pb], ",", "utf-8", self.profile)
        self.assertEqual(len(df), 60)
        self.assertEqual(list(df.columns), list(a.columns))

    def test_column_mismatch_aborts(self):
        a = H.block(0, 10)
        b = H.block(1, 10).rename(columns={"acc_y": "gyro_y"})
        pa = _write_csv(a, self.d, "a.csv")
        pb = _write_csv(b, self.d, "b.csv")
        with self.assertRaises(CombineError):
            combine_recordings([pa, pb], ",", "utf-8", self.profile)

    def test_per_file_index_dropped(self):
        a = H.block(0, 20)
        a.insert(0, "idx", range(len(a)))
        pa = _write_csv(a, self.d, "a.csv")
        df, findings = combine_recordings([pa], ",", "utf-8", self.profile)
        self.assertNotIn("idx", df.columns)
        self.assertTrue(any(f.code == "index_column_present" for f in findings))

    def test_bounded_trim(self):
        a = H.block(0, 50)
        pa = _write_csv(a, self.d, "a.csv")
        df, _ = combine_recordings([pa], ",", "utf-8", self.profile, trim_head=5, trim_tail=5)
        self.assertEqual(len(df), 40)


if __name__ == "__main__":
    unittest.main()
