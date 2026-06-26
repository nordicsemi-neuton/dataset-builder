"""report — render a Report to plain text (process P-07 shape) and to JSON.

Verdict first → the numbers → prioritised fixes each citing the rule → secondary notes. Plain language,
no internal jargon (CLAUDE.md "In human terms").
"""
from __future__ import annotations

from .findings import Report, Group, Severity

_VERDICT_LINE = {
    "PASS": "PASS — no blocking problems found.",
    "FIX_REQUIRED": "FIX REQUIRED — the platform would reject this or it must be corrected first.",
    "WILL_LOSE_DATA": "WILL LOSE DATA — the file is accepted, but a class/window would silently disappear.",
}

_GROUP_ORDER = [Group.HARD_REJECT, Group.SILENT_LOSS, Group.BAD_MODEL, Group.INTAKE, Group.INFO]
_GROUP_TITLE = {
    Group.HARD_REJECT: "Must fix (platform rejects otherwise)",
    Group.SILENT_LOSS: "Silent data loss (verify in the Processed Data view)",
    Group.BAD_MODEL: "Model-quality recommendations",
    Group.INTAKE: "File format issues",
    Group.INFO: "Notes",
}


def render(report: Report) -> str:
    lines = [_VERDICT_LINE.get(report.verdict, report.verdict), ""]
    n = 0
    for group in _GROUP_ORDER:
        items = [f for f in report.findings if f.group == group]
        if not items:
            continue
        lines.append(f"## {_GROUP_TITLE[group]}")
        for f in items:
            n += 1
            ref = f"  [rule: {f.rule_ref}]" if f.rule_ref else ""
            lines.append(f"{n}. {f.message}{ref}")
        lines.append("")
    if report.verdict == "PASS" and n == 0:
        lines.append("Nothing to change — this dataset satisfies the checked rules.")
    return "\n".join(lines).rstrip() + "\n"


def to_json(report: Report) -> dict:
    return report.to_dict()
