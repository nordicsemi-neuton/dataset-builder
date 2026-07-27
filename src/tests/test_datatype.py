import unittest

import _helpers as H
from data_builder.datatype import recommend_dtype


def _df(vals):
    return H.pd.DataFrame({"acc_x": vals})


class TestDatatype(unittest.TestCase):
    def test_float_is_float32(self):
        self.assertEqual(recommend_dtype(_df([9.78, 1.0]), ["acc_x"])["dtype"], "FLOAT32")

    def test_int8_boundaries(self):
        self.assertEqual(recommend_dtype(_df([-128, 0, 127]), ["acc_x"])["dtype"], "INT8")

    def test_just_outside_int8_is_int16(self):
        self.assertEqual(recommend_dtype(_df([0, 128]), ["acc_x"])["dtype"], "INT16")
        self.assertEqual(recommend_dtype(_df([-129, 0]), ["acc_x"])["dtype"], "INT16")

    def test_int16_boundaries(self):
        self.assertEqual(recommend_dtype(_df([-32768, 32767]), ["acc_x"])["dtype"], "INT16")

    def test_just_outside_int16_is_float32(self):
        self.assertEqual(recommend_dtype(_df([0, 40000]), ["acc_x"])["dtype"], "FLOAT32")

    def test_axon_forces_float32(self):
        # Integers in INT8 range, but Axon accepts only FLOAT32.
        self.assertEqual(recommend_dtype(_df([1, 2, 3]), ["acc_x"], "axon")["dtype"], "FLOAT32")

    def test_resample_output_recovers_int(self):
        # databuilder-021 / B4: the OUTPUT of resample_to_rate on an all-integral set (INT16 band) is
        # integer-valued after the fix, so recommend_dtype recovers INT16 (on the parent commit the
        # output is fractional -> FLOAT32; this is the red->green for defect #10 part 2).
        from data_builder.resample import resample_to_rate
        n = 60
        df = H.pd.DataFrame({"acc_x": (150 + (H.np.arange(n) * 7) % 200).astype(H.np.int64),
                             "acc_y": (200 + (H.np.arange(n) * 3) % 100).astype(H.np.int64),
                             "acc_z": (300 - (H.np.arange(n) * 5) % 150).astype(H.np.int64),
                             "t": H.np.arange(n) / 50.0, "class": 0})
        out, _ = resample_to_rate(df, "t", 100, ["acc_x", "acc_y", "acc_z"], "class", None, "s")
        self.assertEqual(recommend_dtype(out, ["acc_x", "acc_y", "acc_z"])["dtype"], "INT16")

    def test_float_reason_names_column(self):
        # Evidence/provenance: the FLOAT32 reason names the first fractional column.
        rec = recommend_dtype(H.pd.DataFrame({"acc_x": [1, 2, 3], "gy": [0.5, 1.0, 2.0]}), ["acc_x", "gy"])
        self.assertEqual(rec["dtype"], "FLOAT32")
        self.assertIn("gy", rec["reason"])


if __name__ == "__main__":
    unittest.main()
