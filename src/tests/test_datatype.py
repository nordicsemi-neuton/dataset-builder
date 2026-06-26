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


if __name__ == "__main__":
    unittest.main()
