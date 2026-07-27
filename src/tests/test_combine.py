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

    def test_flags_shuffled_input_file(self):
        # databuilder-019: combine checks each input file's time order and names the file in the finding.
        import numpy as np
        prof = H.prof(sampling_rate_hz=100, time_column="t")
        df = H.concat(H.block(0, 30), H.block(1, 30))
        t = np.arange(60) / 100.0
        t[40] = t[10]                          # big backward jump within the recording
        df["t"] = t
        p = _write_csv(df, self.d, "shuf.csv")
        _, findings = combine_recordings([p], ",", "utf-8", prof)
        flagged = [f for f in findings if f.code == "timestamps_out_of_order"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0].data["source"], "shuf.csv")

    def test_clean_multifile_not_flagged(self):
        # Two clean recordings, different origins -> per-file check passes, no false flag on the seam.
        import numpy as np
        prof = H.prof(sampling_rate_hz=100, time_column="t")
        frames = []
        for t0, name in ((0.0, "a.csv"), (0.02, "b.csv")):
            df = H.concat(H.block(0, 30), H.block(1, 30))
            df["t"] = t0 + np.arange(60) / 100.0
            frames.append(_write_csv(df, self.d, name))
        _, findings = combine_recordings(frames, ",", "utf-8", prof)
        self.assertNotIn("timestamps_out_of_order", [f.code for f in findings])


if __name__ == "__main__":
    unittest.main()
