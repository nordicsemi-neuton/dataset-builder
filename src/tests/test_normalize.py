import unittest

import _helpers as H
from data_builder.normalize import try_parse_number, normalize_numeric, check_timestamps, find_index_column


class TestParse(unittest.TestCase):
    def test_comma_decimal(self):
        self.assertEqual(try_parse_number("9,78", True), (9.78, None))

    def test_thousands_grouping(self):
        self.assertEqual(try_parse_number("1,234", True), (1234, None))

    def test_thousands_and_decimal(self):
        self.assertEqual(try_parse_number("20,000.00", True), (20000, None))

    def test_currency_unit_stripped(self):
        self.assertEqual(try_parse_number("$20,000.00", True), (20000, None))

    def test_trailing_unit(self):
        self.assertEqual(try_parse_number("9.78g", True), (9.78, None))

    def test_na_tokens(self):
        for tok in ("", "NA", "NAN", "N/A", "null"):
            self.assertEqual(try_parse_number(tok, True)[1], "empty_or_na")

    def test_unrepairable(self):
        self.assertEqual(try_parse_number("abc", True)[1], "unrepairable")
        self.assertEqual(try_parse_number("1 2", True)[1], "unrepairable")  # two numbers


class TestNormalizeNumeric(unittest.TestCase):
    def test_float_preserved_not_truncated(self):
        df = H.pd.DataFrame({"acc_z": ["9.78", "9.79", "9.80"]})
        out, findings = normalize_numeric(df, ["acc_z"])
        self.assertFalse(findings)
        self.assertTrue(H.pd.api.types.is_float_dtype(out["acc_z"]))
        self.assertAlmostEqual(float(out["acc_z"].iloc[0]), 9.78)

    def test_integral_stays_int(self):
        df = H.pd.DataFrame({"n": ["1", "2", "3"]})
        out, _ = normalize_numeric(df, ["n"])
        self.assertTrue(H.pd.api.types.is_integer_dtype(out["n"]))

    def test_na_is_a_finding_not_a_drop(self):
        df = H.pd.DataFrame({"acc_z": ["9.78", "", "9.80"]})
        out, findings = normalize_numeric(df, ["acc_z"])
        self.assertEqual(len(out), 3)  # row NOT dropped
        self.assertTrue(any(f.code == "empty_or_na_value" for f in findings))

    def test_unrepairable_is_a_finding(self):
        df = H.pd.DataFrame({"acc_z": ["9.78", "oops", "9.80"]})
        _, findings = normalize_numeric(df, ["acc_z"])
        self.assertTrue(any(f.code == "unrepairable_value" for f in findings))


class TestTimestamps(unittest.TestCase):
    def test_numeric_ok(self):
        self.assertEqual(check_timestamps(H.pd.Series(["1508284800", "1508284801"]), "t"), [])

    def test_calendar_flagged(self):
        f = check_timestamps(H.pd.Series(["10/18/2017", "10/19/2017"]), "t")
        self.assertTrue(f and f[0].code == "calendar_timestamp")


class TestIndexColumn(unittest.TestCase):
    def test_strict_index_detected(self):
        df = H.pd.DataFrame({"idx": ["0", "1", "2", "3"], "acc_x": ["1", "2", "3", "4"]})
        col, findings = find_index_column(df, {"acc_x"})
        self.assertEqual(col, "idx")
        self.assertTrue(any(f.code == "index_column_present" for f in findings))

    def test_profile_named_column_not_dropped(self):
        df = H.pd.DataFrame({"acc_x": ["0", "1", "2", "3"]})
        col, _ = find_index_column(df, {"acc_x"})
        self.assertIsNone(col)


# databuilder-019 (B1b): timestamp-order check (import inside the body so the RED on the parent commit,
# where check_time_order does not exist, is a clean per-test failure, not a module-collection crash).
class TestTimeOrder(unittest.TestCase):
    def _n(self, seq, session=None):
        from data_builder.normalize import check_time_order
        df = H.pd.DataFrame({"t": list(seq)})
        if session is not None:
            df["sess"] = session
        return check_time_order(df, "t", "sess" if session is not None else None)

    def test_check_time_order_unit(self):
        self.assertEqual(len(self._n([0, 1, 2, 3, 1.5, 4])), 1)                 # (a) interior shuffle
        self.assertEqual(self._n([0, 1, 2, 3, 1.5, 4])[0].data["out_of_order_rows"], 1)
        self.assertEqual(self._n([0, 1, 2, 3, 4, 5]), [])                       # (b) monotone
        self.assertEqual(len(self._n([5, 4, 3, 2, 1])), 1)                      # (c) reverse-sorted
        self.assertEqual(self._n([0, 0.02, 0.0199, 0.04, 0.06, 0.0599, 0.08]), [])  # (d) sub-step jitter
        f = self._n([0, 1, 2, 3, 1.5, 4] + [0, 1, 2, 3, 4, 5], session=["a"] * 6 + ["b"] * 6)
        self.assertEqual([x.data["session"] for x in f], ["a"])                 # (e) per-session
        self.assertEqual(self._n([0, 1, 1, 2, 3]), [])                          # (f) duplicate/flat
        self.assertEqual(len(self._n(["0", "1", "2", "0.5", "3"])), 1)          # (g) numeric strings


if __name__ == "__main__":
    unittest.main()
