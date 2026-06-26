import os
import tempfile
import unittest

import _helpers as H
from data_builder import csv_io


def _write_bytes(data: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path


class TestSniff(unittest.TestCase):
    def test_crlf(self):
        p = _write_bytes(b"acc_x,acc_y\r\n1,2\r\n3,4\r\n")
        self.assertEqual(csv_io.sniff_raw(p).line_endings, "crlf")

    def test_lf(self):
        p = _write_bytes(b"acc_x,acc_y\n1,2\n3,4\n")
        self.assertEqual(csv_io.sniff_raw(p).line_endings, "lf")

    def test_mixed_flagged(self):
        p = _write_bytes(b"acc_x,acc_y\r\n1,2\n3,4\n")
        scan = csv_io.sniff_raw(p)
        self.assertEqual(scan.line_endings, "mixed")
        self.assertTrue(any(f.code == "mixed_line_endings" for f in scan.findings))

    def test_missing_header(self):
        p = _write_bytes(b"1,2,3\n4,5,6\n")
        scan = csv_io.sniff_raw(p)
        self.assertFalse(scan.has_header)
        self.assertTrue(any(f.code == "missing_header" for f in scan.findings))

    def test_delimiter_detected(self):
        p = _write_bytes(b"a;b;c\n1;2;3\n")
        self.assertEqual(csv_io.sniff_raw(p).delimiter, "semicolon")


class TestReadTable(unittest.TestCase):
    def test_comma_decimal_with_comma_sep_is_finding(self):
        # 2-column header but a comma-decimal makes a row have 3 fields. pandas silently truncates,
        # so sniff_raw catches it deterministically on the raw bytes.
        p = _write_bytes(b"x,y\n1,5,2\n")
        scan = csv_io.sniff_raw(p)
        self.assertTrue(any(f.code == "field_count_mismatch" for f in scan.findings))


class TestWriteTable(unittest.TestCase):
    def test_exact_line_ending_and_plain_decimal(self):
        df = H.pd.DataFrame({"acc_z": [9.78, 0.00001], "class": [1, 2]})
        path = os.path.join(tempfile.mkdtemp(), "out.csv")
        csv_io.write_table(df, path, sep_char=",", line_ending="\r\n")
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertIn(b"9.78", raw)
        self.assertIn(b"\r\n", raw)
        self.assertNotIn(b"1e-05", raw)        # no scientific notation
        self.assertEqual(raw.count(b"acc_z"), 1)  # single header


if __name__ == "__main__":
    unittest.main()
