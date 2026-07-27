"""csv_io — raw-byte sniffing + DataFrame read/write.

The raw-byte split exists because pandas hides exactly what the platform contract cares about: it
opens in universal-newline mode (collapsing CR/LF/CRLF) and dies on a comma-delimited file with
comma-decimals. So line-endings / encoding / header / delimiter are detected on bytes BEFORE pandas
(databuilder-001 [gate]).
"""
from __future__ import annotations

import io
import os
import zlib
import zipfile
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"

CANDIDATE_SEPS = {",": "comma", ";": "semicolon", "|": "pipe", "^": "caret", "\t": "tab"}

# The field-count check samples the first _HEAD_ROWS data rows; _HEAD_BYTES bounds how much of the
# file we decode to find them. 1 MiB covers 50 rows of a ~1800-column file and is always >= the
# original 64 KB, so the sample only ever GROWS versus reading data[:65536] -- it cannot hide a
# ragged row the old bound caught (databuilder-013).
_HEAD_BYTES = 1 << 20

# Forbidden characters in the platform's FILE NAME, duplicated from validate.FORBIDDEN_FILENAME_CHARS
# (validate imports csv_io, so importing it back would be a cycle). A test asserts the two stay equal.
_FORBIDDEN_FILENAME_CHARS = set(" !@#$%^&*,.?\":{}\\/|<>()[]+'`")

# Errors zipfile/zlib raise for a .zip we cannot use. Bare OSError is DELIBERATELY excluded:
# FileNotFoundError / PermissionError are OSError, and swallowing them here would report "corrupt
# archive" (exit 2) for a missing file that must stay an IO error (exit 4) (databuilder-013).
_ZIP_ERRORS = (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError,
               zlib.error, EOFError)

# A single archive member above this is not inspected -- unzip and validate the CSV directly. Bounds
# sniff_raw's own decompression (it holds the whole member in memory); checked against the declared
# size BEFORE opening, then re-checked on the actual read because a declared size can lie.
_ZIP_MEMBER_MAX = 256 * 1024 * 1024


@dataclass
class RawScan:
    encoding: str                 # "utf-8" | "iso-8859-1" | "unknown"
    line_endings: str             # "crlf" | "lf" | "cr" | "mixed" | "none"
    delimiter: str | None         # keyword: comma/semicolon/pipe/caret/tab, or None if ambiguous
    has_header: bool
    findings: list[Finding]


def _looks_numeric(token: str) -> bool:
    t = token.strip().strip('"').replace(",", ".")  # tolerate comma-decimal for the heuristic
    try:
        float(t)
        return True
    except ValueError:
        return False


def _head_lines(data: bytes, dec_enc: str) -> list[str]:
    """Decode a line-aligned head, bounded by _HEAD_BYTES, for the delimiter/header/field-count sample.

    A row cut by the byte bound is dropped, never inspected -- its field count is an artefact of where
    the bound fell, and reporting it as a ragged row false-rejected valid wide files. The bound only
    ever GROWS the sample versus reading data[:65536] (databuilder-013). Single-pass: one slice, one
    rfind, one decode -- cost is bounded by _HEAD_BYTES, not by file size.
    """
    head = data[:_HEAD_BYTES]
    if len(head) < len(data):                    # the file continues past the bound
        cut = max(head.rfind(b"\n"), head.rfind(b"\r"))
        if cut >= 0:                             # keep only complete lines
            head = head[:cut + 1]
        # cut < 0: a single line longer than _HEAD_BYTES -> decode as-is; delimiter/header sniff only
    text = head.decode(dec_enc, errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _bad_inner_name(member_name: str):
    """A zip member's name against the platform file-name rule, matching validate.check_filename's
    stem derivation. Backslashes (Windows-tool archives) are path separators inside the archive, so
    they are normalised before the basename -- a documented divergence from check_filename, which on
    POSIX would treat the '\\' as a forbidden character (databuilder-013)."""
    name = os.path.basename(member_name.replace("\\", "/"))
    stem = name[:-4] if name.lower().endswith(".csv") else os.path.splitext(name)[0]
    bad = sorted({c for c in stem if c in _FORBIDDEN_FILENAME_CHARS})
    if bad:
        return Finding(
            Group.INTAKE, Severity.FIX_REQUIRED, "zip_inner_file_name",
            f"The file inside the archive is named '{name}', which contains characters the platform "
            f"forbids in a file name ({''.join(bad)} — note spaces and dots are not allowed). We "
            f"cannot tell from the docs whether the platform reads the name inside a .zip; rename the "
            f"member using only letters, digits, '-' and '_' to be safe.",
            f"{DATASET_REQ}#file-level-requirements", {"member": name, "bad": bad})
    return None


def _zip_member(path: str) -> tuple[bytes | None, str | None, list[Finding]]:
    """Resolve AND READ the single data member of a .zip. The read is INSIDE the guard because an
    encrypted member (RuntimeError) or a content-corrupt member (zlib.error / one BadZipFile flavour)
    raises at read time, not at open. Returns (member_bytes, member_name, findings); bytes is None on
    any bail-out. The caller sniffs the bytes; read_table wraps them in BytesIO (databuilder-013)."""
    def _reject(code, msg, sev=Severity.HARD_REJECT):
        return None, None, [Finding(Group.INTAKE, sev, code, msg,
                                    f"{DATASET_REQ}#file-level-requirements")]
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            ignored: list[str] = []
            # step 1: real files, not __MACOSX sidecars, deduped by (name, CRC, size)
            seen, candidates = set(), []
            for info in infos:
                if info.is_dir() or info.filename.startswith("__MACOSX/"):
                    ignored.append(info.filename)
                    continue
                key = (info.filename, info.CRC, info.file_size)
                if key in seen:
                    ignored.append(info.filename)
                    continue
                seen.add(key)
                candidates.append(info)
            # step 2: drop dot-prefixed basenames ONLY if that leaves >=1 candidate
            non_dot = [i for i in candidates if not os.path.basename(i.filename).startswith(".")]
            if non_dot and len(non_dot) < len(candidates):
                ignored += [i.filename for i in candidates if i not in non_dot]
                candidates = non_dot
            if not candidates:
                return _reject("zip_empty",
                               "The archive has no usable data file in it. Put a single CSV inside "
                               "the .zip and upload that.")
            # step 4: pick the member
            if len(candidates) == 1:
                chosen = candidates[0]
            else:
                csvs = [i for i in candidates if i.filename.lower().endswith(".csv")]
                if len(csvs) == 1:
                    chosen = csvs[0]
                    ignored += [i.filename for i in candidates if i is not chosen]
                else:
                    names = ", ".join(sorted(i.filename for i in candidates))
                    return _reject("zip_multiple_files",
                                   f"The archive holds more than one file ({names}) and we cannot tell "
                                   f"which is the dataset. Put exactly one CSV inside the .zip.")
            # size bound BEFORE opening (declared size can lie -> re-checked on read)
            if chosen.file_size > _ZIP_MEMBER_MAX:
                return _reject("zip_member_too_large",
                               f"The file inside the archive ('{chosen.filename}') is larger than "
                               f"256 MB uncompressed. Unzip it and validate the CSV directly.",
                               Severity.FIX_REQUIRED)
            with zf.open(chosen) as fh:
                blob = fh.read(_ZIP_MEMBER_MAX + 1)
            if len(blob) > _ZIP_MEMBER_MAX:
                return _reject("zip_member_too_large",
                               f"The file inside the archive ('{chosen.filename}') is larger than "
                               f"256 MB uncompressed. Unzip it and validate the CSV directly.",
                               Severity.FIX_REQUIRED)
            findings = []
            if ignored:
                findings.append(Finding(
                    Group.INFO, Severity.INFO, "zip_extra_members",
                    f"The archive held other entries; we used '{chosen.filename}' and ignored: "
                    f"{', '.join(sorted(ignored))}.",
                    f"{DATASET_REQ}#file-level-requirements", {"used": chosen.filename,
                                                               "ignored": sorted(ignored)}))
            if not blob:
                findings.append(Finding(
                    Group.INTAKE, Severity.HARD_REJECT, "zip_member_empty",
                    f"The file inside the archive ('{chosen.filename}') is empty.",
                    f"{DATASET_REQ}#file-level-requirements"))
                return None, chosen.filename, findings
            name_finding = _bad_inner_name(chosen.filename)
            if name_finding:
                findings.append(name_finding)
            return blob, chosen.filename, findings
    except _ZIP_ERRORS as exc:
        return _reject("zip_unreadable",
                       f"'{os.path.basename(path)}' could not be read as a .zip archive ({exc}). It "
                       f"may be corrupt, password-protected, or not actually an archive.")


def sniff_raw(path: str) -> RawScan:
    """Inspect the file as bytes: encoding, line endings, delimiter, header presence.

    A .zip (by extension) is unwrapped to its single member first, so every check below describes the
    CSV inside rather than the compressed stream (databuilder-013). read_table resolves the same
    member the same way, so the two layers cannot describe different files.
    """
    findings: list[Finding] = []
    if path.lower().endswith(".zip"):
        blob, _member, zfindings = _zip_member(path)
        findings.extend(zfindings)
        if blob is None:                          # bail-out: neutral scan, delimiter None
            return RawScan(encoding="unknown", line_endings="none", delimiter=None,
                           has_header=True, findings=findings)
        data = blob
    else:
        with open(path, "rb") as fh:
            data = fh.read()

    # --- encoding ---------------------------------------------------------
    encoding = "utf-8"
    head = data[:4]
    if head[:2] in (b"\xff\xfe", b"\xfe\xff") or head[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff") \
            or b"\x00" in data[:4096]:
        encoding = "unknown"
        findings.append(Finding(
            Group.INTAKE, Severity.HARD_REJECT, "encoding_not_supported",
            "The file does not look like UTF-8 or ISO-8859-1 (looks like UTF-16/binary). "
            "Convert it to UTF-8 before uploading.",
            f"{DATASET_REQ}#file-level-requirements"))
    else:
        try:
            data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "iso-8859-1"  # acceptable; maps all bytes, so this is best-effort

    # --- line endings -----------------------------------------------------
    crlf = data.count(b"\r\n")
    lf_total = data.count(b"\n")
    cr_total = data.count(b"\r")
    lone_lf = lf_total - crlf
    lone_cr = cr_total - crlf
    if (crlf and (lone_lf or lone_cr)) or (lone_lf and lone_cr):
        line_endings = "mixed"
        findings.append(Finding(
            Group.INTAKE, Severity.HARD_REJECT, "mixed_line_endings",
            "The file mixes line-ending styles (CRLF and LF). Use one consistently (CRLF or LF).",
            f"{DATASET_REQ}#file-level-requirements"))
    elif crlf:
        line_endings = "crlf"
    elif lone_lf:
        line_endings = "lf"
    elif lone_cr:
        line_endings = "cr"
        findings.append(Finding(
            Group.INTAKE, Severity.HARD_REJECT, "cr_only_line_endings",
            "The file uses bare CR line endings. Convert to CRLF or LF.",
            f"{DATASET_REQ}#file-level-requirements"))
    else:
        line_endings = "none"

    # --- delimiter + header (decode a line-aligned head) ------------------
    dec_enc = "utf-8" if encoding == "utf-8" else "latin-1"
    lines = _head_lines(data, dec_enc)
    first = lines[0] if lines else ""
    delimiter = None
    if first:
        counts = {sep: first.count(sep) for sep in CANDIDATE_SEPS}
        best = max(counts, key=counts.get)
        if counts[best] == 0:
            findings.append(Finding(
                Group.INTAKE, Severity.HARD_REJECT, "no_delimiter_found",
                "Could not find a supported delimiter (comma, semicolon, pipe, caret, tab) in the header.",
                f"{DATASET_REQ}#file-level-requirements"))
        else:
            delimiter = CANDIDATE_SEPS[best]

    has_header = True
    if delimiter is not None and first:
        sep_char = {v: k for k, v in CANDIDATE_SEPS.items()}[delimiter]
        header_count = len(first.split(sep_char))
        tokens = first.split(sep_char)
        if tokens and all(_looks_numeric(t) for t in tokens):
            has_header = False
            findings.append(Finding(
                Group.INTAKE, Severity.HARD_REJECT, "missing_header",
                "The first row looks like data, not column names. The platform requires a header row first.",
                f"{DATASET_REQ}#file-level-requirements"))
        # Field-count consistency (catches ragged rows / a comma-decimal value under a comma delimiter,
        # which pandas silently truncates rather than raising). Skip when quotes are present — a quoted
        # field may legitimately contain the delimiter, and naive split() would false-reject it.
        for ln in lines[1:51]:
            if ln == "" or '"' in ln or '"' in first:
                continue
            if len(ln.split(sep_char)) != header_count:
                findings.append(Finding(
                    Group.INTAKE, Severity.HARD_REJECT, "field_count_mismatch",
                    f"A data row has a different number of fields than the header ({header_count}); this is "
                    f"usually a stray delimiter or a comma-decimal value in a comma-separated file. Fix the "
                    f"delimiter / decimal format before uploading.",
                    f"{DATASET_REQ}#value-rules", {"header_fields": header_count}))
                break

    return RawScan(encoding=encoding, line_endings=line_endings, delimiter=delimiter,
                   has_header=has_header, findings=findings)


def read_table(path: str, sep_char: str, encoding: str):
    """Read into a DataFrame with EVERY column as a raw string (na_filter off) so locale repair can run.

    Returns (df_or_None, findings). A comma-delimited file containing comma-decimals makes pandas raise
    ParserError -> returned as a HARD-REJECT finding rather than crashing. A .zip is resolved to its
    single member via the SAME helper sniff_raw uses, so the two layers cannot disagree; the member's
    resolution findings are returned only on failure (df is None) -- on success sniff_raw already
    reported them, and returning them again would double-report in prep (databuilder-013).
    """
    enc = "utf-8" if encoding == "utf-8" else "latin-1"
    source = path
    if path.lower().endswith(".zip"):
        blob, _member, zfindings = _zip_member(path)
        if blob is None:
            return None, zfindings          # zip_unreadable / zip_empty / zip_multiple_files / ...
        source = io.BytesIO(blob)
    try:
        # index_col=False stops pandas silently using an extra (e.g. comma-decimal) field as the row
        # index; a ragged row then raises ParserError, which we surface as a finding.
        df = pd.read_csv(source, sep=sep_char, dtype=str, na_filter=False, keep_default_na=False,
                         encoding=enc, engine="c", index_col=False)
        return df, []
    except (pd.errors.ParserError, ValueError) as exc:
        finding = Finding(
            Group.INTAKE, Severity.HARD_REJECT, "parse_error",
            f"The file could not be parsed with the chosen delimiter (often a comma-decimal value in a "
            f"comma-separated file): {exc}",
            f"{DATASET_REQ}#value-rules")
        return None, [finding]


def _format_value(v) -> str:
    """Plain decimal, no scientific notation, no trailing-zero noise; integers stay integer-looking."""
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (np.integer, int)):
        return str(int(v))
    f = float(v)
    if not np.isfinite(f):        # +/-inf would crash int(f); render blank (an inf is not valid input)
        return ""
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return np.format_float_positional(f, trim="-")


def write_table(df: pd.DataFrame, path: str, sep_char: str = ",", line_ending: str = "\n") -> None:
    """Write with exact on-disk line endings (newline='') and plain-decimal numeric formatting."""
    out = pd.DataFrame({c: [_format_value(v) for v in df[c].to_numpy()] for c in df.columns})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out.to_csv(fh, sep=sep_char, index=False, lineterminator=line_ending)
