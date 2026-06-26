"""csv_io — raw-byte sniffing + DataFrame read/write.

The raw-byte split exists because pandas hides exactly what the platform contract cares about: it
opens in universal-newline mode (collapsing CR/LF/CRLF) and dies on a comma-delimited file with
comma-decimals. So line-endings / encoding / header / delimiter are detected on bytes BEFORE pandas
(databuilder-001 [gate]).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"

CANDIDATE_SEPS = {",": "comma", ";": "semicolon", "|": "pipe", "^": "caret", "\t": "tab"}


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


def sniff_raw(path: str) -> RawScan:
    """Inspect the file as bytes: encoding, line endings, delimiter, header presence."""
    findings: list[Finding] = []
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

    # --- delimiter + header (decode the first two lines) ------------------
    dec_enc = "utf-8" if encoding == "utf-8" else "latin-1"
    text_head = data[:65536].decode(dec_enc, errors="replace")
    lines = text_head.replace("\r\n", "\n").replace("\r", "\n").split("\n")
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
    ParserError -> returned as a HARD-REJECT finding rather than crashing.
    """
    enc = "utf-8" if encoding == "utf-8" else "latin-1"
    try:
        # index_col=False stops pandas silently using an extra (e.g. comma-decimal) field as the row
        # index; a ragged row then raises ParserError, which we surface as a finding.
        df = pd.read_csv(path, sep=sep_char, dtype=str, na_filter=False, keep_default_na=False,
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
