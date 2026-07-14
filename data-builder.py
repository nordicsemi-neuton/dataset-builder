#!/usr/bin/env python3
"""Cross-platform launcher for the data-builder CLI.

Zero-install twin of the `data-builder` console script (pyproject.toml):
identical on macOS/Linux/Windows, no PYTHONPATH needed:

    python3 data-builder.py <prep|validate|quality-report> ...   (macOS/Linux)
    python  data-builder.py <prep|validate|quality-report> ...   (Windows)

No logic lives here — it delegates to data_builder.cli.main() and passes its
exit codes (0/2/3/4) through unchanged. See .claude/skills/_shared/runtime.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from data_builder.cli import main

if __name__ == "__main__":
    sys.exit(main())
