"""cli — the stable command surface the data-prep skills shell out to.

Subcommands: prep, validate, quality-report. --json prints machine-readable output. Exit codes:
0=PASS/OK, 2=FIX_REQUIRED, 3=WILL_LOSE_DATA, 4=IO/profile/usage error (databuilder-001 frozen contract).
"""
from __future__ import annotations

import argparse
import json
import sys

from .findings import EXIT_CODES, make_report, Severity, Finding, Group
from .profile import DatasetProfile, ProfileError
from . import report as report_mod
from . import validate as validate_mod
from . import pipeline as pipeline_mod
from . import quality as quality_mod

SP_APPLICABILITY = "wiki/architecture/platform-signal-processing-applicability.md"

# Windows consoles/pipes default to cp1252, which cannot encode every character in
# this tool's output; degrade to '?' instead of crashing (no-op on UTF-8 terminals).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def _load_profile(path: str) -> DatasetProfile:
    try:
        return DatasetProfile.load(path)
    except ProfileError as exc:
        print(f"profile error: {exc}", file=sys.stderr)
        raise SystemExit(4)


def _emit(report, as_json: bool) -> int:
    if as_json:
        print(json.dumps(report_mod.to_json(report), indent=2))
    else:
        print(report_mod.render(report))
    return EXIT_CODES.get(report.verdict, 4)


def _resolve_validate_mode(args, profile: DatasetProfile) -> tuple[bool, int | None]:
    """Resolve (sp_on, window) for `validate`.

    Signal Processing OFF (profile says so) needs no window -- the platform does not window a tabular
    dataset. Otherwise (declared on, or unstated) a window is required exactly as before; the only
    change to that path is a message that names the escape hatch. Scoped to `validate`: prep and
    quality-report resolve the mode with _resolve_mode (their tabular support is databuilder-016).
    """
    if profile.signal_processing is False:
        return False, None
    if args.window:
        return True, args.window
    if profile.window_candidates:
        w = profile.window_candidates[0]
        if not isinstance(w, int) or isinstance(w, bool):
            # A malformed candidate (null / string / float) would otherwise reach the window checks as
            # a non-int and be silently skipped. Fail loudly instead of hiding the checks.
            print(f"error: window.candidates[0] must be an integer, got {w!r}", file=sys.stderr)
            raise SystemExit(4)
        return True, w
    print("error: no --window given and no window.candidates in the profile. If each row is a "
          "complete independent observation (tabular data, no windowing), set "
          '"signal_processing": false in the profile — see '
          "wiki/architecture/platform-signal-processing-applicability.md", file=sys.stderr)
    raise SystemExit(4)


def _resolve_mode(args, profile: DatasetProfile) -> tuple[bool, int | None]:
    """Resolve (sp_on, window) for `prep`/`quality-report`.

    Signal Processing OFF -> (False, None): the platform does not window a tabular dataset, so no window
    is needed and prep/quality run in tabular mode. Otherwise a window is required. Unlike validate's
    resolver, a non-positive --window (or candidate) is a loud usage error rather than a silent fall-
    through to the candidate -- `--window 0` used to substitute the candidate silently (databuilder-016).
    """
    if profile.signal_processing is False:
        return False, None
    if args.window is not None:
        if args.window < 1:
            print(f"error: --window must be a positive integer, got {args.window}", file=sys.stderr)
            raise SystemExit(4)
        return True, args.window
    if profile.window_candidates:
        w = profile.window_candidates[0]
        if not isinstance(w, int) or isinstance(w, bool) or w < 1:
            print(f"error: window.candidates[0] must be a positive integer, got {w!r}", file=sys.stderr)
            raise SystemExit(4)
        return True, w
    print("error: no --window given and no window.candidates in the profile. If each row is a "
          "complete independent observation (tabular data, no windowing), set "
          '"signal_processing": false in the profile — see '
          "wiki/architecture/platform-signal-processing-applicability.md", file=sys.stderr)
    raise SystemExit(4)


def _mode_tells(args, sp_on, profile: DatasetProfile) -> list:
    """SP-off contradiction tells: a window supplied (via --window or the profile's window.candidates)
    is ignored for tabular data. ADVISORY -- disclosed, never blocking (ADR-0006 incentive gradient)."""
    if sp_on is not False:
        return []
    supplied = (["--window"] if args.window is not None else []) + \
               (["the profile's window.candidates"] if profile.window_candidates else [])
    if not supplied:
        return []
    return [Finding(
        Group.BAD_MODEL, Severity.ADVISORY, "sp_off_window_ignored",
        f"The profile declares Signal Processing OFF (tabular), so the window from "
        f"{' and '.join(supplied)} is ignored — the platform does not window a tabular dataset. Remove "
        f"it, or set \"signal_processing\": true if this is a windowed time series.",
        f"{SP_APPLICABILITY}#the-decision-rule", {"supplied": supplied})]


def cmd_validate(args) -> int:
    profile = _load_profile(args.profile)
    sp_on, window = _resolve_validate_mode(args, profile)
    try:
        report = validate_mod.run_checks(args.csv, profile, window, profile.frequency_domain,
                                         holdout_path=args.holdout, sp_on=sp_on)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    return _emit(report, args.json)


def cmd_prep(args) -> int:
    profile = _load_profile(args.profile)
    sp_on, window = _resolve_mode(args, profile)
    try:
        do_center = False if args.no_center else None   # None = auto (center gesture datasets)
        result = pipeline_mod.prep(args.inputs, profile, args.out, window, do_center=do_center,
                                   target_rate=args.resample, write_anyway=args.write_anyway,
                                   time_unit=args.time_unit, sp_on=sp_on)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    report = result["report"]
    # A supplied window is ignored under SP off; disclose it (ADVISORY -> verdict and the write decision
    # are unchanged; the tell is display/--json only) (databuilder-016).
    tells = _mode_tells(args, sp_on, profile)
    if tells:
        report = make_report(tells + report.findings)
    if not args.json:
        if result["written"]:
            # A continuous target has no class dictionary, so there is no second path to name.
            if result["dictionary_path"]:
                print(f"Wrote {result['out_path']} and {result['dictionary_path']}.\n")
            else:
                print(f"Wrote {result['out_path']}.\n")
        else:
            # The two filesystem guards are pre-flight and cannot be forced; only steer to
            # --write-anyway for data-contract refusals (databuilder-013).
            forceable = not any(f.code in ("output_overwrites_input", "output_not_csv")
                                for f in report.findings)
            if forceable:
                print("Did NOT write the output (problems below; pass --write-anyway to force).\n")
            else:
                print("Did NOT write the output (fix the output path below; this cannot be forced).\n")
    return _emit(report, args.json)


def _render_quality(rep, findings) -> str:
    """Single text renderer for quality-report: blocking problems first, then the per-source profile and
    the outlier comparison. `findings` = the intake findings + rep's own findings; the ADVISORY
    source_outlier items are NOT in the blocking filter, so they render exactly once, in their own
    section (databuilder-017)."""
    lines = []
    blocking = [f for f in findings if f.severity in (Severity.HARD_REJECT, Severity.FIX_REQUIRED,
                                                       Severity.WILL_LOSE_DATA)]
    if blocking:
        lines.append("Problems (the analysis below may be incomplete):")
        for f in blocking:
            ref = f"  [rule: {f.rule_ref}]" if f.rule_ref else ""
            lines.append(f"  - {f.message}{ref}")
        lines.append("")
    if rep is not None:
        lines.append(f"Sources (by {rep['source_col']}):")
        for s in rep["sources"]:
            lines.append(f"  {s['source']}: {s['rows']} rows  classes={s['class_counts']}")
        lines.append("")
        if not rep["comparison_ran"]:
            lines.append("Source comparison not run — the per-source profile above is all there is to compare.")
        elif rep["outliers"]:
            lines.append("Possible outlier sources (Cohen's d — indicative, not a platform pass/fail):")
            for f in rep["findings"]:
                if f.code == "source_outlier":
                    lines.append(f"  - {f.message}")
        else:
            lines.append(f"No source looks like a different feature regime (above d={rep['threshold_d']}).")
        if rep["insufficient"]:
            lines.append("")
            lines.append(f"({len(rep['insufficient'])} source/class combinations had too few windows to compare.)")
    # Mode advisories (e.g. sp_off_window_ignored). Unlike prep, quality-report has no group-based
    # renderer, so an ADVISORY tell would be invisible in text mode without this section (databuilder-016).
    advisories = [f for f in findings if f.severity == Severity.ADVISORY and f.code != "source_outlier"]
    if advisories:
        lines.append("")
        lines.append("Notes:")
        for f in advisories:
            lines.append(f"  - {f.message}")
    return "\n".join(lines) + "\n"


def _emit_quality(rep, findings, as_json: bool) -> int:
    """Print the quality report (findings + optional profile) and return the verdict's exit code.

    quality-report is an analysis surface: exit 0 when the analysis ran (advisories/notes do not block),
    exit 2 when a blocking finding (missing label, unreadable input, unrepairable value) means it could
    not (databuilder-017). Exit 4 stays for genuine IO/profile errors (raised by the caller)."""
    report = make_report(findings)
    if as_json:
        payload = {"verdict": report.verdict, "findings": [f.to_dict() for f in findings]}
        if rep is not None:
            payload.update({k: rep[k] for k in ("source_col", "sources", "outliers", "insufficient",
                                                 "threshold_d", "note", "comparison_ran")})
        print(json.dumps(payload, indent=2))
    else:
        print(_render_quality(rep, findings))
    return EXIT_CODES.get(report.verdict, 4)


def cmd_quality(args) -> int:
    profile = _load_profile(args.profile)
    sp_on, window = _resolve_mode(args, profile)
    tells = _mode_tells(args, sp_on, profile)     # SP-off: a supplied window is ignored (databuilder-016)
    try:
        df, source_col, intake = quality_mod.load_sources(args.inputs, profile)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    if df is None:
        # Nothing readable. If intake told us WHY (an unreadable/misnamed .zip, an unrepairable value),
        # surface it and use the verdict's exit code instead of dropping it behind a generic message.
        if intake or tells:
            return _emit_quality(None, tells + intake, args.json)
        print("error: no readable input files", file=sys.stderr)
        return 4
    rep = quality_mod.quality_report(df, profile, window, source_col)
    return _emit_quality(rep, tells + intake + rep["findings"], args.json)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="data_builder", description="Prepare/validate sensor CSVs for Nordic Edge AI Lab.")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="validate a CSV against the platform contract")
    v.add_argument("csv")
    v.add_argument("--profile", required=True, help="path to a dataset-profile JSON")
    v.add_argument("--window", type=int, default=None, help="window size in samples (else profile candidate)")
    v.add_argument("--holdout", default=None, help="optional holdout/test CSV")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_validate)

    pr = sub.add_parser("prep", help="assemble recordings into one upload-ready CSV")
    pr.add_argument("inputs", nargs="+", help="one or more recording CSVs")
    pr.add_argument("--profile", required=True)
    pr.add_argument("--out", required=True, help="output CSV path")
    pr.add_argument("--window", type=int, default=None)
    pr.add_argument("--no-center", action="store_true",
                    help="skip gesture centering (centering is default-on for gesture datasets)")
    pr.add_argument("--resample", type=float, default=None, metavar="HZ", help="resample to this rate")
    pr.add_argument("--time-unit", choices=["s", "ms", "us"], default="s", dest="time_unit")
    pr.add_argument("--write-anyway", action="store_true", help="write even on FIX_REQUIRED/WILL_LOSE_DATA")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_prep)

    q = sub.add_parser("quality-report", help="profile sources and flag an outlier recording/user")
    q.add_argument("inputs", nargs="+", help="one or more recording CSVs (each file = one source)")
    q.add_argument("--profile", required=True)
    q.add_argument("--window", type=int, default=None)
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_quality)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
