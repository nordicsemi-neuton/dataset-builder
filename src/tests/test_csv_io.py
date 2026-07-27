import io
import os
import tempfile
import time
import unittest
import zipfile

import _helpers as H
from data_builder import csv_io, validate


def _write_bytes(data: bytes, suffix: str = ".csv") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path


def _rb(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _zip(members, mode=zipfile.ZIP_DEFLATED, suffix=".zip") -> str:
    """members: list of (arcname, bytes)."""
    path = _write_bytes(b"", suffix)
    with zipfile.ZipFile(path, "w", mode) as zf:
        for arc, payload in members:
            zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = mode if not arc.endswith("/") else zipfile.ZIP_STORED
            zf.writestr(zi, payload)
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


_CLEAN = b"acc_x,acc_y,label\n" + b"".join(f"{i}.5,{i}.25,{i%3}\n".encode() for i in range(300))


def _wide(ncols, nrows, ragged_at=None, delta=0):
    cols = ["acc_x", "acc_y", "label"] + [f"c{i}" for i in range(ncols - 3)]
    out = [",".join(cols)]
    for r in range(nrows):
        vals = [f"{r}.5", f"{r}.25", str(r % 3)] + [f"{(r*i)%1000}.123456" for i in range(ncols - 3)]
        if r == ragged_at:
            if delta > 0:
                vals += ["9"] * delta
            else:
                del vals[delta:]
        out.append(",".join(vals))
    return ("\n".join(out) + "\n").encode()


class TestHeadTruncation(unittest.TestCase):
    """databuilder-013 defect A: the 64 KB head truncated wide files mid-row."""

    def test_valid_wide_file_not_rejected(self):
        # RED on 7c48e79: 64 KB holds ~12 of a 513-col file's rows and the partial trips this.
        p = _write_bytes(_wide(513, 60))
        codes = [f.code for f in csv_io.sniff_raw(p).findings]
        self.assertNotIn("field_count_mismatch", codes)

    def test_valid_wide_file_1025_cols(self):
        p = _write_bytes(_wide(1025, 60))
        self.assertNotIn("field_count_mismatch", [f.code for f in csv_io.sniff_raw(p).findings])

    def test_ragged_row_hidden_by_huge_header_is_reported(self):
        # RED on 7c48e79: an >64 KB header truncated away every data row, so [] was returned.
        cols = [f"column_number_{i:06d}" for i in range(4000)]        # ~84 KB header
        data = (",".join(cols) + "\n" + ",".join(["1"] * 3999) + "\n").encode()
        codes = [f.code for f in csv_io.sniff_raw(_write_bytes(data)).findings]
        self.assertIn("field_count_mismatch", codes)

    def test_narrow_ragged_row_still_reported(self):
        # non-regression: a genuine ragged row inside the sample must still fire.
        p = _write_bytes(b"a,b,c\n1,2,3\n4,5\n6,7,8\n")
        self.assertIn("field_count_mismatch", [f.code for f in csv_io.sniff_raw(p).findings])

    def test_head_bounded_runtime(self):
        # RED-adjacent: a per-line whole-file scan would blow up here; the bound keeps it fast.
        big = b"acc_x,acc_y,acc_z,label\n" + b"1.1,2.2,3.3,1\n" * 800000   # ~13 MB LF
        p = _write_bytes(big)
        t = time.time()
        csv_io.sniff_raw(p)
        self.assertLess(time.time() - t, 1.0)

    def test_single_line_over_bound_no_crash(self):
        p = _write_bytes(b"z," * 700000 + b"z")                      # one line > 1 MiB
        csv_io.sniff_raw(p)   # must not raise

    def test_empty_and_no_terminator(self):
        self.assertEqual(csv_io.sniff_raw(_write_bytes(b"")).line_endings, "none")
        self.assertEqual(csv_io.sniff_raw(_write_bytes(b"a,b,c")).line_endings, "none")


class TestZipContainer(unittest.TestCase):
    """databuilder-013 defect B: .zip is an accepted upload form."""

    def test_clean_zip_no_findings(self):
        # RED on 7c48e79: sniff scanned compressed bytes -> encoding_not_supported (+more).
        scan = csv_io.sniff_raw(_zip([("gestures.csv", _CLEAN)]))
        self.assertEqual([f.code for f in scan.findings], [])
        self.assertEqual(scan.encoding, "utf-8")
        self.assertEqual(scan.line_endings, "lf")
        self.assertEqual(scan.delimiter, "comma")

    def test_clean_zip_stored(self):
        scan = csv_io.sniff_raw(_zip([("gestures.csv", _CLEAN)], mode=zipfile.ZIP_STORED))
        self.assertEqual([f.code for f in scan.findings], [])

    def test_illegal_inner_name(self):
        # RED on 7c48e79: the inner name was never checked.
        scan = csv_io.sniff_raw(_zip([("my gesture data v2.csv", _CLEAN)]))
        self.assertIn("zip_inner_file_name", [f.code for f in scan.findings])

    def test_multiple_members(self):
        scan = csv_io.sniff_raw(_zip([("a.csv", _CLEAN), ("b.csv", _CLEAN)]))
        self.assertIn("zip_multiple_files", [f.code for f in scan.findings])

    def test_one_csv_among_extras_is_used(self):
        scan = csv_io.sniff_raw(_zip([("gestures.csv", _CLEAN), ("readme.txt", b"hi\n")]))
        codes = [f.code for f in scan.findings]
        self.assertIn("zip_extra_members", codes)
        self.assertNotIn("zip_multiple_files", codes)

    def test_macosx_sidecar_ignored(self):
        scan = csv_io.sniff_raw(_zip([("gestures.csv", _CLEAN), ("__MACOSX/", b""),
                                      ("__MACOSX/._gestures.csv", b"\x00\x05")]))
        codes = [f.code for f in scan.findings]
        self.assertNotIn("zip_multiple_files", codes)
        self.assertIn("zip_extra_members", codes)

    def test_folder_zip_readable(self):
        scan = csv_io.sniff_raw(_zip([("realdir/", b""), ("realdir/gestures.csv", _CLEAN)]))
        self.assertNotIn("zip_multiple_files", [f.code for f in scan.findings])

    def test_empty_archive(self):
        self.assertIn("zip_empty", [f.code for f in csv_io.sniff_raw(_zip([])).findings])

    def test_zero_byte_member(self):
        scan = csv_io.sniff_raw(_zip([("gestures.csv", b"")]))
        self.assertIn("zip_member_empty", [f.code for f in scan.findings])

    def test_corrupt_zip_no_crash(self):
        good = _zip([("gestures.csv", _CLEAN)])
        p = _write_bytes(_rb(good)[:120], ".zip")
        scan = csv_io.sniff_raw(p)   # RED on 7c48e79 (via read_table): BadZipFile traceback
        self.assertIn("zip_unreadable", [f.code for f in scan.findings])

    def test_plain_csv_misnamed_zip(self):
        p = _write_bytes(_CLEAN, ".zip")
        self.assertIn("zip_unreadable", [f.code for f in csv_io.sniff_raw(p).findings])

    def test_zip_named_csv_unchanged(self):
        # a zip whose extension is .csv keeps today's encoding rejection (bytes are not text).
        p = _write_bytes(_rb(_zip([("g.csv", _CLEAN)])), ".csv")
        self.assertIn("encoding_not_supported", [f.code for f in csv_io.sniff_raw(p).findings])

    def test_read_table_streams_zip_member(self):
        df, fnd = csv_io.read_table(_zip([("gestures.csv", _CLEAN)]), ",", "utf-8")
        self.assertIsNotNone(df)
        self.assertEqual(df.shape, (300, 3))
        self.assertEqual(fnd, [])

    def test_read_table_matches_path_read(self):
        p = _write_bytes(_CLEAN)
        df_path, _ = csv_io.read_table(p, ",", "utf-8")
        df_zip, _ = csv_io.read_table(_zip([("gestures.csv", _CLEAN)]), ",", "utf-8")
        self.assertTrue(df_path.equals(df_zip))

    def test_read_table_corrupt_zip_no_crash(self):
        good = _zip([("gestures.csv", _CLEAN)])
        p = _write_bytes(_rb(good)[:120], ".zip")
        df, fnd = csv_io.read_table(p, ",", "utf-8")     # must not raise
        self.assertIsNone(df)
        self.assertIn("zip_unreadable", [f.code for f in fnd])

    def test_member_size_bound_fires(self):
        # With the bound lowered, a member above it is reported without being decompressed.
        z = _zip([("gestures.csv", _CLEAN)])
        real = csv_io._ZIP_MEMBER_MAX
        try:
            csv_io._ZIP_MEMBER_MAX = 100          # _CLEAN is a few KB, so it now exceeds the bound
            codes = [f.code for f in csv_io.sniff_raw(z).findings]
            self.assertIn("zip_member_too_large", codes)
        finally:
            csv_io._ZIP_MEMBER_MAX = real
        # and at the real bound a normal member is fine
        self.assertNotIn("zip_member_too_large", [f.code for f in csv_io.sniff_raw(z).findings])


class TestNameParity(unittest.TestCase):
    """zip_inner_file_name must match validate.check_filename, except the documented backslash case."""

    def _fires(self, member):
        f = csv_io._bad_inner_name(member)
        return f is not None

    def test_parity_with_check_filename(self):
        for name in ("gestures.csv", "sub/gestures.csv", "gestures.CSV", ".gestures.csv",
                     "image.png", "archive.tar.gz", "my gesture data v2.csv", "__MACOSX/._g.csv"):
            self.assertEqual(self._fires(name),
                             validate.check_filename(name) is not None,
                             f"divergence on {name!r}")

    def test_backslash_documented_divergence(self):
        # A backslash is a Windows-tool path separator. Our zip helper normalizes '\' -> '/' before
        # basename, so it never fires (both platforms). check_filename uses os.path.basename, which is
        # platform-aware: on POSIX the '\' stays in the name and is flagged; on Windows it is a path
        # separator and stripped, leaving a clean 'gestures.csv'. A backslash cannot be part of a real
        # Windows filename anyway, so both outcomes are correct -- the divergence is POSIX-only.
        self.assertFalse(self._fires("sub\\gestures.csv"))   # holds on both platforms
        if os.name == "nt":
            self.assertIsNone(validate.check_filename("sub\\gestures.csv"))
        else:
            self.assertIsNotNone(validate.check_filename("sub\\gestures.csv"))

    def test_forbidden_set_matches_validate(self):
        self.assertEqual(csv_io._FORBIDDEN_FILENAME_CHARS, validate.FORBIDDEN_FILENAME_CHARS)


if __name__ == "__main__":
    unittest.main()
