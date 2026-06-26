"""data_builder — prepare & validate inertial-sensor CSVs for the Nordic Edge AI Lab platform.

The production engine the user-facing skills (prep-dataset, validate-upload) call. Knowledge about
the contract it satisfies lives in wiki/architecture/platform-* and wiki/architecture/
data-skill-preset-contract.md; this code is the source of truth on disk.

numpy + pandas only (no scipy, no pytest).
"""

from .findings import Finding, Report, Severity, Group, reduce_verdict

__all__ = ["Finding", "Report", "Severity", "Group", "reduce_verdict"]
