# Contributing to dataset-builder

Thanks for your interest. Please read this first — the contribution path for this repository is a
little different from a typical open-source project.

## How this repository is maintained

This public repository is **generated from an internal source of truth** and refreshed on each
release. As a consequence:

- **Pull requests opened directly here are not the contribution path.** A merged PR would be
  overwritten the next time the maintainers publish a release. Please do not invest in large PRs
  against this repo expecting them to persist.
- **The best way to contribute is to [open an issue](../../issues).** Bug reports, incorrect platform
  guidance, and feature requests are triaged by the Nordic Edge AI / Neuton team and folded into the
  internal source, from where they flow back out to this repo.

If a future change moves this repo to accept PRs directly, this document will be updated to match.

## Reporting a bug

Open an issue using the **Bug report** template. Include:

- What you ran (the exact command / skill) and the input shape (rows, columns, sampling rate in Hz).
- What you expected vs. what happened, with the tool's output.
- Your OS and Python version (`python3 --version`).

Please **do not** attach real user or customer data — a small synthetic sample that reproduces the
problem is ideal.

## Requesting a feature or reporting incorrect platform guidance

Open an issue using the **Feature request** template. The tool's guidance must match the live
[Nordic Edge AI Lab documentation](https://docs.nordicsemi.com/bundle/edge-ai-lab/page/index.html) —
if you spot a mismatch between what the tool says and what the platform does, that is a high-priority
report; please link the relevant documentation page.

## Security

Do **not** open a public issue for a security vulnerability. See [SECURITY.md](SECURITY.md) for the
coordinated-disclosure process.

## Running the tests locally

```bash
pip install -r requirements.txt
PYTHONPATH=src python3 -m unittest discover -s src/tests
```
