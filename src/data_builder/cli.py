"""cli — the stable command surface the data-prep skills shell out to.

Subcommands: prep, validate, quality-report. --json prints machine-readable output. Exit codes:
0=PASS/OK, 2=FIX_REQUIRED, 3=WILL_LOSE_DATA, 4=IO/profile/usage error (databuilder-001 frozen contract).
"""
from __future__ import annotations

import argparse
import json
import sys

from .findings import EXIT_CODES
from .profile import DatasetProfile, ProfileError
from . import report as report_mod
from . import validate as validate_mod
from . import pipeline as pipeline_mod
from . import quality as quality_mod

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


def _resolve_window(args, profile: DatasetProfile) -> int:
    if args.window:
        return args.window
    if profile.window_candidates:
        return profile.window_candidates[0]
    print("error: no --window given and no window.candidates in the profile", file=sys.stderr)
    raise SystemExit(4)


def cmd_validate(args) -> int:
    profile = _load_profile(args.profile)
    window = _resolve_window(args, profile)
    try:
        report = validate_mod.run_checks(args.csv, profile, window, profile.frequency_domain,
                                         holdout_path=args.holdout)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    return _emit(report, args.json)


def cmd_prep(args) -> int:
    profile = _load_profile(args.profile)
    window = _resolve_window(args, profile)
    try:
        do_center = False if args.no_center else None   # None = auto (center gesture datasets)
        result = pipeline_mod.prep(args.inputs, profile, args.out, window, do_center=do_center,
                                   target_rate=args.resample, write_anyway=args.write_anyway,
                                   time_unit=args.time_unit)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    report = result["report"]
    if not args.json:
        if result["written"]:
            print(f"Wrote {result['out_path']} and {result['dictionary_path']}.\n")
        else:
            print("Did NOT write the output (problems below; pass --write-anyway to force).\n")
    return _emit(report, args.json)


def _render_quality(rep) -> str:
    lines = [f"Sources (by {rep['source_col']}):"]
    for s in rep["sources"]:
        lines.append(f"  {s['source']}: {s['rows']} rows  classes={s['class_counts']}")
    lines.append("")
    if rep["outliers"]:
        lines.append("Possible outlier sources (Cohen's d — indicative, not a platform pass/fail):")
        for f in rep["findings"]:
            lines.append(f"  - {f.message}")
    else:
        lines.append(f"No source looks like a different feature regime (above d={rep['threshold_d']}).")
    if rep["insufficient"]:
        lines.append("")
        lines.append(f"({len(rep['insufficient'])} source/class combinations had too few windows to compare.)")
    return "\n".join(lines) + "\n"


def cmd_quality(args) -> int:
    profile = _load_profile(args.profile)
    window = _resolve_window(args, profile)
    try:
        df, source_col, _ = quality_mod.load_sources(args.inputs, profile)
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 4
    if df is None:
        print("error: no readable input files", file=sys.stderr)
        return 4
    rep = quality_mod.quality_report(df, profile, window, source_col)
    if args.json:
        print(json.dumps({k: rep[k] for k in ("source_col", "sources", "outliers", "insufficient",
                                               "threshold_d", "note")}, indent=2))
    else:
        print(_render_quality(rep))
    return 0


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
