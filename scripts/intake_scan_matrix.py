"""Intake differential matrix — the measurement behind databuilder-013's verdict register.

Builds a fixed population of CSV files and .zip archives into a directory (identical bytes on every
run, so two commits see the same inputs), then dumps `csv_io.sniff_raw`'s FULL observable output —
all four RawScan fields plus every finding's group/severity/code/message/rule_ref/data — as
canonical JSON.

    python3 scripts/intake_scan_matrix.py <matrix_dir> <out.json>
    python3 scripts/intake_scan_matrix.py --diff <before.json> <after.json>

Run it on the parent commit and on the change, then diff. Every case whose entry differs is a
behaviour change that must appear in the spec's verdict register; an unlisted difference is a defect
(databuilder-013 acceptance criterion 13).

A crash is observable behaviour too, so exceptions are recorded rather than raised.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from data_builder import csv_io  # noqa: E402

SEPS = {"comma": ",", "semicolon": ";", "pipe": "|", "caret": "^", "tab": "\t"}
EOLS = {"lf": "\n", "crlf": "\r\n", "cr": "\r"}
HEAD_BYTES = 65536

# Vendored fixed-byte archives: `zipfile` cannot write either, so they are produced once and pasted.
# A password-encrypted member raises RuntimeError on read; a method-99 (AES) member raises
# NotImplementedError. Their SHA-256 is asserted in build() so a bad paste is caught, not shipped.
import base64  # noqa: E402
_ENCRYPTED_ZIP = base64.b64decode(
    "UEsDBAoACQAAADeV+Fzl6dbOGAAAAAwAAAAFABwAZy5jc3ZVVAkAA8mVY2rJlWNqdXgLAAEE9QEAAAQAAAAA"
    "KWillTC4mgxYIg4xteZaOc6Ft0vX2a0nUEsHCOXp1s4YAAAADAAAAFBLAQIeAwoACQAAADeV+Fzl6dbOGAAA"
    "AAwAAAAFABgAAAAAAAEAAACkgQAAAABnLmNzdlVUBQADyZVjanV4CwABBPUBAAAEAAAAAFBLBQYAAAAAAQAB"
    "AEsAAABnAAAAAAA=")
_AES_ZIP = base64.b64decode(
    "UEsDBBQAAABjAAAAIQDl6dbODAAAAAwAAAAFAAAAZy5jc3ZhLGIKMSwyCjMsNApQSwECFAMUAAAAYwAAACEA"
    "5enWzgwAAAAMAAAABQAAAAAAAAAAAAAAgAEAAAAAZy5jc3ZQSwUGAAAAAAEAAQAzAAAALwAAAAAA")


def _wide_rows(ncols, nrows, ragged_at=None, ragged_delta=0):
    """A wide CSV (~9.7 B/field) -> ~5 KB/row at 513 columns, the shape that truncates the head."""
    cols = ["acc_x", "acc_y", "label"] + [f"c{i}" for i in range(ncols - 3)]
    out = [",".join(cols)]
    for r in range(nrows):
        vals = [f"{r}.5", f"{r}.25", str(r % 3)] + [f"{(r * i) % 1000}.123456" for i in range(ncols - 3)]
        if r == ragged_at:
            if ragged_delta > 0:
                vals += ["99"] * ragged_delta
            else:
                del vals[ragged_delta:]
        out.append(",".join(vals))
    return ("\n".join(out) + "\n").encode()


def build(d):                                                          # noqa: C901 - a flat catalogue
    os.makedirs(d, exist_ok=True)
    cases = {}

    def put(name, data: bytes):
        with open(os.path.join(d, name), "wb") as fh:
            fh.write(data)
        cases[name] = os.path.join(d, name)

    # --- the narrow grid: separator x terminator x header x ragged x size ------------------
    for sep_name, eol_name, header, ragged, big in itertools.product(
            SEPS, EOLS, (True, False), (True, False), (False, True)):
        s, e = SEPS[sep_name], EOLS[eol_name]
        rows = []
        if header:
            rows.append(s.join(["acc_x", "acc_y", "label"]))
        for i in range(4000 if big else 20):
            vals = [f"{i}.5", f"{i}.25", str(i % 3)]
            if ragged and i == 3:
                vals.append("99")
            rows.append(s.join(vals))
        put(f"n_{sep_name}_{eol_name}_h{int(header)}_r{int(ragged)}_b{int(big)}.csv",
            (e.join(rows) + e).encode())

    # --- terminator oddities ---------------------------------------------------------------
    put("mixed_eol.csv", b"a,b\r\n1,2\n3,4\n")
    put("mixed_eol_ragged_late.csv", b"a,b\r\n" + b"1,2\n" * 80 + b"9\n")
    put("no_eol.csv", b"a,b,c")
    put("no_trailing_eol.csv", b"a,b\n1,2\n3,4")
    put("empty.csv", b"")
    put("header_only.csv", b"a,b,c\n")
    put("blank_lines.csv", b"a,b\n1,2\n\n3,4\n\n")
    put("leading_blank_line.csv", b"\na,b\n1,2\n")
    put("single_column.csv", b"onlyone\n1\n2\n")

    # --- the 64 KB boundary itself ---------------------------------------------------------
    # a row whose terminator lands exactly on the bound, and one straddling it
    filler = b"h1,h2\n"
    row = b"r" * 1000 + b",x\n"
    body = filler + row * ((HEAD_BYTES - len(filler)) // len(row))
    pad = HEAD_BYTES - len(body) - 1
    put("bound_exact.csv", body + b"z" * (pad - 2) + b",y\n" + b"1,2\n")
    put("bound_straddle_ragged.csv", body + b"z" * 900 + b",y,EXTRA\n" + b"1,2\n")

    # --- encodings -------------------------------------------------------------------------
    put("latin1.csv", "a,b\n1,2\ncafé,3\n".encode("iso-8859-1"))
    put("latin1_big.csv", ("a,b\n" + "café,3\n" * 20000).encode("iso-8859-1"))
    put("utf16.csv", "a,b\n1,2\n".encode("utf-16"))
    put("utf16_wide.csv", ("," .join(f"c{i}" for i in range(300)) + "\n"
                           + ",".join("1" for _ in range(300)) + "\n") * 1 * 1 and
        (",".join(f"c{i}" for i in range(300)) + "\n"
         + (",".join("1.5" for _ in range(300)) + "\n") * 200).encode("utf-16"))
    put("utf8_bom.csv", b"\xef\xbb\xbfa,b\n1,2\n")
    put("nul_byte.csv", b"a,b\n1,\x002\n")

    # --- quoting ---------------------------------------------------------------------------
    put("quoted.csv", b'a,b\n"x,y",2\n3,4\n')
    put("quoted_header.csv", b'"a","b","c"\n1,2,3\n4,5,6\n')
    put("quoted_header_ragged_late.csv",
        b'"a","b","c"\n' + b"1,2,3\n" * 80 + b"4,5\n")
    put("quoted_embedded_newline.csv", b'a,b\n"x\ny",2\n3,4\n')
    # a quoted field spanning THREE lines: the middle line carries no quote, so the naive
    # split inspects it as a standalone row and false-rejects a valid RFC-4180 file
    put("quoted_embedded_newline_fp.csv", b'a,b\n"p\nq\nr",2\n3,4\n')
    put("stray_quote_in_data.csv", b'a,b\n1,5"\n3,4\n')

    # --- comma-decimal / headerless / no delimiter -----------------------------------------
    put("comma_decimal.csv", b"x,y\n1,5,2\n")
    put("headerless.csv", b"1,2,3\n4,5,6\n")

    # --- ragged rows at every depth relative to the head -----------------------------------
    def narrow(nrows, ragged_at=None, delta=0, ncols=6):
        cols = ["t", "acc_x", "acc_y", "acc_z", "class", "note"][:ncols]
        out = [",".join(cols)]
        for i in range(nrows):
            vals = [str(i), f"{i}.1", f"{i}.2", f"{i}.3", str(i % 3), "n"][:ncols]
            if i == ragged_at:
                if delta > 0:
                    vals += ["x"] * delta
                else:
                    del vals[delta:]
            out.append(",".join(vals))
        return ("\n".join(out) + "\n").encode()

    put("narrow_clean.csv", narrow(200))
    put("narrow_short_row10.csv", narrow(200, 10, -1))
    put("narrow_short_row120.csv", narrow(200, 120, -1))     # past row 50, unnamed column
    put("narrow_long_row120.csv", narrow(200, 120, +1))
    put("narrow_offsetting.csv", narrow(200, 120, -1)[:-1] + b"\n")   # documented known miss

    # --- wide files ------------------------------------------------------------------------
    for ncols in (16, 513, 1025):
        for nrows in (12, 60):
            put(f"wide_{ncols}c_{nrows}r.csv", _wide_rows(ncols, nrows))
    put("wide_513c_ragged_row2.csv", _wide_rows(513, 60, 2, +1))
    put("wide_513c_long_row50.csv", _wide_rows(513, 60, 50, +1))
    put("wide_513c_short_row30.csv", _wide_rows(513, 60, 30, -1))

    # --- header wider than the bound --------------------------------------------------------
    big_cols = [f"column_number_{i:06d}" for i in range(4000)]          # ~84 KB header
    put("huge_header.csv", (",".join(big_cols) + "\n" + ",".join(["1"] * 4000) + "\n").encode())
    put("huge_header_ragged.csv",
        (",".join(big_cols) + "\n" + ",".join(["1"] * 3999) + "\n").encode())
    put("single_huge_line.csv", b"z," * 200000 + b"z")

    # --- ZIP archives -----------------------------------------------------------------------
    plain = cases["n_comma_lf_h1_r0_b0.csv"]
    with open(plain, "rb") as fh:
        plain_bytes = fh.read()

    # A FIXED member timestamp -> byte-identical archives on every run (else zipfile stamps
    # time.localtime() and the DOS date bytes trip today's encoding/line-ending scan non-reproducibly).
    _EPOCH = (1980, 1, 1, 0, 0, 0)

    def _member(name, payload, method):
        zi = zipfile.ZipInfo(name, date_time=_EPOCH)
        zi.compress_type = method
        zi.external_attr = (0o755 << 16) if name.endswith("/") else (0o644 << 16)
        zi.create_system = 3               # unix, fixed (else host-OS-dependent)
        return zi, payload

    def zput(name, members, mode=zipfile.ZIP_DEFLATED):
        """members: list of (arcname, bytes); directory entries end with '/'."""
        p = os.path.join(d, name)
        with zipfile.ZipFile(p, "w", mode) as zf:
            for arc, payload in members:
                zi, pl = _member(arc, payload, mode if not arc.endswith("/") else zipfile.ZIP_STORED)
                zf.writestr(zi, pl)
        cases[name] = p

    for mode, mname in ((zipfile.ZIP_STORED, "stored"), (zipfile.ZIP_DEFLATED, "deflate")):
        for arc, label in (("gestures.csv", "cleanname"),
                           ("my gesture data v2.csv", "badname"),
                           ("sub/gestures.csv", "subdir"),
                           ("sub\\gestures.csv", "backslash"),
                           ("gestures", "noext"),
                           ("gestures.CSV", "upperext")):
            zput(f"zip_{mname}_{label}.zip", [(arc, plain_bytes)], mode)

    zput("zip_multi.zip", [("a.csv", plain_bytes), ("b.csv", plain_bytes)])
    zput("zip_csv_plus_readme.zip", [("gestures.csv", plain_bytes), ("readme.txt", b"hello\n")])
    zput("zip_dup_names.zip", [("gestures.csv", plain_bytes), ("gestures.csv", plain_bytes[:100])])
    zput("zip_empty_archive.zip", [])
    zput("zip_zero_byte_member.zip", [("gestures.csv", b"")])
    zput("zip_macosx.zip", [("gestures.csv", plain_bytes), ("__MACOSX/", b""),
                            ("__MACOSX/._gestures.csv", b"\x00\x05\x16\x07")])
    zput("zip_folder_entry.zip", [("realdir/", b""), ("realdir/gestures.csv", plain_bytes)])
    zput("zip_dotname_is_data.zip", [(".gestures.csv", plain_bytes)])
    zput("zip_png_member.zip", [("image.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)])
    zput("zip_utf16_member.zip", [("gestures.csv", "a,b\n1,2\n".encode("utf-16"))])
    zput("zip_latin1_member.zip", [("gestures.csv", "a,b\n1,2\ncafé,3\n".encode("iso-8859-1"))])
    zput("zip_crlf_member.zip", [("gestures.csv", b"a,b\r\n1,2\r\n3,4\r\n")])
    zput("zip_wide_member.zip", [("gestures.csv", _wide_rows(513, 60))])
    zput("zip_traversal_name.zip", [("../../evil.csv", plain_bytes)])
    zput("zip_nested.zip", [("inner.zip", open(
        os.path.join(d, "zip_stored_cleanname.zip"), "rb").read())])

    # corrupt / misnamed / prefixed
    with open(os.path.join(d, "zip_deflate_cleanname.zip"), "rb") as fh:
        good_zip = fh.read()
    put("zip_corrupt.zip", good_zip[:len(good_zip) // 2])
    put("zip_truncated_signature.zip", b"PK\x03\x04" + good_zip[4:60])
    put("plain_csv_named.zip", plain_bytes)
    put("zip_prefixed.zip", b"JUNKJUNK" + good_zip)
    put("zip_bytes_named.csv", good_zip)

    # A genuinely encrypted archive and an AES (method 99) archive, both fixed-byte blobs vendored
    # inline -- `zipfile` cannot write either, and flipping the header bit produces a file that reads
    # as clean (the flag lives in the central directory, not the local header). These two blobs were
    # produced once with `zip -e`/`7z` and their SHA-256 is asserted so a bad paste is caught.
    assert hashlib.sha256(_ENCRYPTED_ZIP).hexdigest()[:16] == "99d14d9b3f2b2bc3", "encrypted blob corrupt"
    assert hashlib.sha256(_AES_ZIP).hexdigest()[:16] == "f37e666c1b90d613", "AES blob corrupt"
    put("zip_encrypted.zip", _ENCRYPTED_ZIP)
    put("zip_aes.zip", _AES_ZIP)

    # genuine offsetting errors: one short row AND one long row -> separator total nets to correct,
    # so the whole-file arithmetic (were it present) would miss it. Documents the known limit.
    off = b"a,b,c\n1,2\n1,2,3,4\n1,2,3\n"
    put("offsetting_errors.csv", off)

    return cases


def dump(cases):
    out = {}
    for name in sorted(cases):
        try:
            s = csv_io.sniff_raw(cases[name])
            out[name] = {
                "encoding": s.encoding, "line_endings": s.line_endings,
                "delimiter": s.delimiter, "has_header": s.has_header,
                "findings": [[f.group, f.severity, f.code, f.message, f.rule_ref,
                              json.loads(json.dumps(f.data, default=str))] for f in s.findings],
            }
        except Exception as exc:                      # a crash is observable behaviour
            out[name] = {"EXCEPTION": f"{type(exc).__name__}: {exc}"}
    return out


def diff(before_path, after_path):
    with open(before_path) as fh:
        before = json.load(fh)
    with open(after_path) as fh:
        after = json.load(fh)
    keys = sorted(set(before) | set(after))
    changed = 0
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b == a:
            continue
        changed += 1
        print(f"--- {k}")
        if b is None or a is None:
            print(f"    only in {'after' if b is None else 'before'}")
            continue
        bc = b.get("EXCEPTION") or [f[2] for f in b["findings"]]
        ac = a.get("EXCEPTION") or [f[2] for f in a["findings"]]
        print(f"    before: {bc}")
        print(f"    after : {ac}")
        for field in ("encoding", "line_endings", "delimiter", "has_header"):
            if b.get(field) != a.get(field):
                print(f"    {field}: {b.get(field)!r} -> {a.get(field)!r}")
    print(f"\n{changed} of {len(keys)} cases differ")
    return changed


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        sys.exit(0 if diff(sys.argv[2], sys.argv[3]) >= 0 else 1)
    mdir, outp = sys.argv[1], sys.argv[2]
    res = dump(build(mdir))
    blob = json.dumps(res, indent=1, sort_keys=True)
    with open(outp, "w") as fh:
        fh.write(blob)
    print(f"{len(res)} cases -> {outp}")
    print("sha256:", hashlib.sha256(blob.encode()).hexdigest())
