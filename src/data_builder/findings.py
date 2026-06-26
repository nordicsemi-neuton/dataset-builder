"""Frozen cross-module contract: Severity, Group, Finding, Report, verdict reduction.

This is the seam the CLI and the 5 skills bind to (databuilder-001 "Cross-module contract"). Keep it
stable. A Finding's `rule_ref` points into the canonical wiki (path#Lx) so a human can trace any claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


class Severity:
    HARD_REJECT = "hard-reject"      # platform refuses the upload
    FIX_REQUIRED = "fix-required"    # accepted but must be fixed (e.g. rate unknown)
    WILL_LOSE_DATA = "will-lose-data"  # accepted, but a class/window silently disappears
    ADVISORY = "advisory"            # model-quality recommendation; does not change the verdict
    INFO = "info"                    # neutral note; does not change the verdict


class Group:
    HARD_REJECT = "HARD-REJECT"
    SILENT_LOSS = "SILENT-LOSS"
    BAD_MODEL = "BAD-MODEL"
    INTAKE = "INTAKE"
    INFO = "INFO"


class Verdict:
    PASS = "PASS"
    FIX_REQUIRED = "FIX_REQUIRED"
    WILL_LOSE_DATA = "WILL_LOSE_DATA"


# CLI exit codes (databuilder-001 frozen contract).
EXIT_CODES = {
    Verdict.PASS: 0,
    Verdict.FIX_REQUIRED: 2,
    Verdict.WILL_LOSE_DATA: 3,
    # 4 = IO / profile / usage error (raised in cli.py)
}


@dataclass
class Finding:
    group: str               # one of Group.*
    severity: str            # one of Severity.*
    code: str                # stable slug, e.g. "non_numeric_value"
    message: str             # plain-language description for the user
    rule_ref: str = ""       # wiki path#Lx the rule comes from
    data: dict[str, Any] = field(default_factory=dict)  # the numbers (counts, examples)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    verdict: str
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "findings": [f.to_dict() for f in self.findings]}

    def by_group(self, group: str) -> list[Finding]:
        return [f for f in self.findings if f.group == group]


def reduce_verdict(findings: list[Finding]) -> str:
    """Any hard-reject/fix-required -> FIX_REQUIRED; else any will-lose-data -> WILL_LOSE_DATA; else PASS."""
    sev = {f.severity for f in findings}
    if Severity.HARD_REJECT in sev or Severity.FIX_REQUIRED in sev:
        return Verdict.FIX_REQUIRED
    if Severity.WILL_LOSE_DATA in sev:
        return Verdict.WILL_LOSE_DATA
    return Verdict.PASS


def make_report(findings: list[Finding]) -> Report:
    return Report(verdict=reduce_verdict(findings), findings=list(findings))
