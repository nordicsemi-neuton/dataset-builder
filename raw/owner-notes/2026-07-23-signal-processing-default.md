# Owner note — Signal Processing is off by default

**Received:** 23.07.2026
**From:** the project owner (Nordic Edge AI Lab team), in conversation.
**Form:** verbal/chat statement. Not a document capture.

## The statement

> "The SP-toggle question - by default it is off."

Given in answer to a direct question about whether the platform's **Signal Processing** option is
enabled or disabled when a user creates a new solution.

## Status

**Owner-stated, not documentation-confirmed.** The captured platform docs in
`raw/platform-docs/` establish that Signal Processing is *conditional* — see
`2026-06-25-pipeline-data-preprocessing.md:45` ("If Signal Processing (SP) is enabled:") and
`2026-06-25-solution-management.md:29` (SP listed as an on/off indicator of a solution) — but they
**do not state its default state**.

So the two halves have different provenance and must stay distinguishable in the compiled page:

| claim | provenance |
|---|---|
| Signal Processing is an option, not a fixed pipeline stage | documentation-sourced |
| Signal Processing is **off** unless the user turns it on | this note (owner-stated) |

## Why it is kept out of `raw/platform-docs/`

`raw/platform-docs/` is the immutable baseline that the platform-contract drift check compares
against the live documentation site (`methodology/lint.md`). Adding a fact that is not in the live
docs would make that comparison report a false difference forever. Owner-stated platform facts
therefore live here instead, and carry an explicit verification task.

## Verification task (open)

On the next lint, or the next time anyone has the platform UI open: confirm the default state of the
Signal Processing toggle on a freshly created solution. If confirmed by the docs, move the claim into
the normal doc-sourced chain. If contradicted, correct
`wiki/architecture/platform-signal-processing-applicability.md` and everything that cites it.
