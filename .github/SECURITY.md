# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities **privately** — do not open a public GitHub issue.

**Preferred: [GitHub Private Vulnerability Reporting](https://github.com/nordicsemi-neuton/dataset-builder/security/advisories/new).**
Use the **"Report a vulnerability"** button on the repository's **Security** tab. Reports go directly
and privately to the maintainer.

The maintainer, **Danil Zherebtsov** ([@DanilZherebtsov](https://github.com/DanilZherebtsov)), triages
all reports.

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce (a minimal proof of concept if possible).
- Any suggested remediation.

We will acknowledge your report and keep you informed of the remediation progress. Please give us a
reasonable time to address the issue before any public disclosure.

## Scope

This tool prepares inertial-sensor CSV data locally for upload to the Nordic Edge AI Lab platform. It
processes user-supplied files; the most relevant classes of issue are those involving malformed or
malicious input files and dependency vulnerabilities (`numpy`, `pandas`).

## Supported versions

This repository tracks a single released line. Security fixes are applied to the latest published
version.
