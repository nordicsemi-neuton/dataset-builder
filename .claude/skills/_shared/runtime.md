# Runtime — how to run the engine and scripts (all platforms)

Read this before the first engine or script command of a session. It is the single source for
environment setup, the per-OS command form, and the rules that keep the flow on the shipped tooling.

## The `<python>` placeholder

`<python>` in every command stands for the working interpreter found below — **never type the brackets
literally** (in a POSIX shell a literal `<python>` parses as redirections, not a command). After the
venv fallback below, `<python>` becomes the venv's interpreter path.

## 1. Find the interpreter

- **Windows:** try `py -3 --version`, then `python --version`, then `python3 --version`.
  A fresh machine's `python` may be the Microsoft Store stub that prints a store prompt and fails —
  that counts as "not found", move on.
- **macOS / Linux:** try `python3 --version`, then `python --version`.

Use the first that reports **3.11 or newer** — that is your `<python>`.

**If none does:** tell the user in plain language to install Python 3.11+ (from python.org, or
winget/Microsoft Store on Windows) and **stop — never improvise an alternative runtime.**

## 2. Check the environment (before the first run)

```
<python> -c "import numpy, pandas"
```

If that fails, dependencies are missing. Before installing anything, preview the consequences:
`<python> -m pip install --dry-run -r requirements.txt` (pip ≥ 22.2; if unavailable, compare
`<python> -m pip list` against the pins in `requirements.txt`). Then tell the user what will be
installed and why — **naming any version changes to packages they already have** — and run:

```
<python> -m pip install -r requirements.txt
```

**Fall back to a venv** when the direct install fails (PEP 668 "externally-managed-environment" on
Homebrew/Debian Pythons, or pip missing) **or would change versions of the user's existing packages**:
create it with `<python> -m venv .venv` in the repo root, then use it **activation-free** — from now on
`<python>` is `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows; no
`Activate.ps1`, so no ExecutionPolicy friction) — and install into it with the same pip command.

If venv creation itself fails (Debian/Ubuntu without `python3-venv`: "ensurepip is not available"), or
the install fails for network/permission reasons: **stop and tell the user in plain words what to
install** (e.g. `sudo apt install python3-venv`) — never improvise.

**Never install anything not in `requirements.txt`.** Notes:
- The engine needs numpy ≥ 2.0 / pandas ≥ 2.2; if imports succeed but the engine fails with a
  numpy/pandas incompatibility, the fix is the same pinned install — not source surgery.
- scipy is needed only for anti-alias downsampling. If the engine reports
  `scipy_required_for_downsample` (a FIX-REQUIRED finding), the fix is this same install — an
  environment gap, not a data problem.

## 3. Command form

`cd` **to the repo root** (the folder containing `data-builder.py`) **before any command** — every path
in the skills (`output/<name>/…`, `data/skill-presets/…`, `scripts/…`) is repo-relative, and running
from elsewhere scatters deliverables outside the repo. If you truly cannot `cd`, prefix **every**
repo-relative path (launcher, `--profile`, `--out`, scripts) with the repo path, not just the launcher.

- **Engine:** `<python> data-builder.py <prep|validate|quality-report> … [--json]`
- **Diagnostics:** `<python> scripts/diagnostics/<name>.py …`

Rules that hold on every OS:
- **Single-line commands only** — no `\`, backtick, or `^` continuations.
- **Quote any path containing spaces** (double quotes work in bash, PowerShell, and cmd).
- **No shell wildcards** — the engine does not glob, and neither PowerShell nor cmd expands `*.csv`
  for a child process; list files explicitly.

## 4. Exit codes

`0` ok · `2` FIX-REQUIRED · `3` WILL-LOSE-DATA · `4` I/O, profile, or usage error.

Caveat: a **mistyped command** (bad flag, missing `--profile`) makes argparse itself exit `2` with a
`usage:` message on **stderr** — that is a command error to correct, **not** a FIX-REQUIRED data
verdict. Check stderr before interpreting exit 2.

## Rules

- **R1 — fix the environment, don't improvise.** If a documented command fails, diagnose per this page
  and fix the environment; never substitute an ad-hoc script for the engine or the shipped diagnostics.
  Discriminator: interpreter-not-found, ImportError, argparse `usage:` errors, exit 4 →
  environment/usage — stay in R1.
- **R2 — the engine is a black box.** Treat `src/` and the `scripts/` diagnostics as tools with
  documented contracts (CLI flags, exit codes). For behavior questions consult the wiki pages the
  skills cite. A *suspected engine bug* means: the environment is healthy and the output/exit code
  contradicts the documented contract — only then open the source, **read-only, to report the bug to
  the user**; never patch it or work around undocumented behavior. (Documented, user-approved overrides
  like `--write-anyway` are not "workarounds" and stay available.)
- **R3 — plain-language install talk.** Before touching the user's environment, say what will be
  installed or changed and why, in plain words — naming any version changes to packages they already
  have.
