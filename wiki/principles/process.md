---
type: principles
status: active
updated: 2026-06-25
sources:
  - ../../scripts/diagnostics/analyze_csv_signal.py
  - ../../scripts/diagnostics/window_survival_sim.py
tags: [principles, process, diagnosis, support, methodology]
---

# Process principles — how to diagnose a user's data-prep problem

Rules for investigating and answering a platform user's data-preparation question (from field experience). The step-by-step expansion is the [diagnostic playbook](../synthesis/support-diagnostic-playbook.md); the data/signal rules these lead to are in [domain principles](domain.md). Read before composing any user-facing answer.

## P-01 — Read both halves of the request: the prose and the attachment

**Rule:** Read the user's words *and* any attached screenshot/config/CSV before theorizing. Map the user's **exact phrasing** ("data removed", "label has no data", "model too big") to a likely cause area; note any contradiction between what they say and what their data shows.
**Why:** Users describe the symptom; the screenshot/config usually reveals the actual setting causing it. Contradictions between prose and data are typically *the* problem.
**Precedent:** a "data removed" report where the screenshot showed window=150 with sliding-shift=10 — the overlap setting, invisible in the prose, was central.
**Source:** field experience (practitioner knowledge).

## P-02 — Profile before theorizing; compute the exact number yourself

**Rule:** Run a fixed profiler on the data first ([`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py)). Reach for **distributions and per-session breakdowns**, not averages. Re-derive any figure the user quotes — don't repeat their estimate.
**Why:** Users describe magnitudes imprecisely; a stated "20% removed" turned out to be ~48% on inspection. Per-session, per-label structure (run lengths, class composition, sampling rate) is where the cause hides.
**Source:** field experience (practitioner knowledge); [`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py).

## P-03 — Reconcile every stated claim against the actual data

**Rule:** Treat the user's class mapping, claimed label set, claimed durations, and claimed sampling rate as hypotheses to check against the file, not as facts.
**Why:** The discrepancy is usually the bug (an extra/unmapped class, a wrong rate, a mislabeled session). Users often don't notice their own data contains something they didn't describe.
**Precedent:** a user's stated 5-class mapping vs an actual 6-class file (see [domain P-03](domain.md)).
**Source:** field experience (practitioner knowledge).

## P-04 — Simulate the platform on the user's own data; lead with their numbers

**Rule:** When a complaint is about windowing/preprocessing, **simulate** the platform's behavior on their file ([`window_survival_sim.py`](../../scripts/diagnostics/window_survival_sim.py)) and try a few alternative settings. Quote concrete per-label results ("only N windows of class C survive"). Flag any simulation assumption as an assumption (the exact platform rule may differ — verify against the "Processed Data" view).
**Why:** Concrete numbers from the user's own data persuade and teach; abstract explanations don't.
**Source:** field experience (practitioner knowledge); [`window_survival_sim.py`](../../scripts/diagnostics/window_survival_sim.py).

## P-05 — Run the relevant ceiling/parity checks before promising a fix

**Rule:** Before recommending a postprocessing change, check the [postprocessing ceiling](domain.md) (per-class max probability). Before recommending a firmware filter, run the [preprocessing-parity audit](domain.md). Don't promise a fix the data can't support.
**Why:** Some "fixes" are structurally impossible (a dead class) or actively harmful (inference-only filtering). Checking first avoids a confident wrong answer.
**Source:** field experience (practitioner knowledge); [domain principles P-07, P-09](domain.md).

## P-06 — Confirm the execution protocol before calling a confusion a model bug

**Rule:** When evaluation data shows symmetric left/right (or up/down) confusion, confirm with the user which direction they actually performed first — it may be a protocol-execution mistake, not a model defect.
**Why:** A reversed execution order makes a correct model look wrong; correcting the assumed order can make apparent confusion vanish.
**Precedent:** an L/R "model bug" that resolved once the user confirmed they performed right-first, not left-first.
**Source:** field experience (practitioner knowledge).

## P-07 — Compose the reply: root cause first, their numbers, prioritized fixes, doc links

**Rule:** Structure the answer as: (1) the root cause in one sentence using the user's vocabulary; (2) the numbers from their data that prove it; (3) numbered, concrete fixes in priority order, each linked to the exact platform-docs rule (cite [`architecture/platform-*`](../architecture/platform-dataset-requirements.md)); (4) secondary issues they didn't ask about but should know; (5) collaborative tone ("let's get this working", not "you broke the rules").
**Why:** This structure has repeatedly produced fixes users could act on without a second round-trip.
**Source:** field experience (practitioner knowledge).

## P-08 — A user-facing skill references the wiki by path and never restates it; new transforms are code through the task cycle

**Rule:** When authoring a shipped skill (`.claude/skills/<slug>/SKILL.md`), draw a hard line: narration, orchestration, and platform facts are *referenced* from the canonical wiki by path (or via the shared cited reference `.claude/skills/_shared/platform-contract.md`) — never copied inline. Any new logic that *transforms the user's data* (concatenate, normalize, relabel, center, resample, validate) is `src/` code built through the spec → independent review → implement → re-review cycle, not written ad hoc inside a skill or a draft script. Presets are confirm-first data the skill loads then reconciles against the file ([P-02/P-03](process.md)), never auto-applied defaults.
**Why:** Restating platform rules inside skills creates drift the moment the wiki is corrected (the very rot the wiki exists to prevent). Putting transform logic in narration or one-off scripts bypasses the review that "correctness over speed" for a third-party tool requires. Keeping facts in one place and transforms in reviewed code means one wiki edit updates every skill and every transform has been adversarially checked.
**Precedent:** the user-facing skills mechanism decision — [ADR-0001](../decisions/adr-0001-user-facing-skills-mechanism.md).
**Source:** [ADR-0001](../decisions/adr-0001-user-facing-skills-mechanism.md); [CLAUDE.md](../../CLAUDE.md) Discipline rules 1, 4, 8 and the task-execution cycle.

## P-09 — Hand the user one self-explanatory deliverable folder, not a litter of files

**Rule:** Write a finished dataset to **its own folder `output/<name>/`** containing only what earns its place: the upload file, the engine-produced dictionary that goes with it, the `profile.json` build recipe, and a plain-language `README.md` that names **the single file to upload** and says in one line what each other file is for. **Never** create a file that duplicates one the engine already writes (the `prep` engine auto-writes `<csv>_dictionary.json` — do not hand-make a second class dictionary). **Never** leave intermediate/working files loose beside the deliverable, and never make the user guess which file goes to the platform. One folder per dataset also stops different datasets/versions getting confused; a rebuild overwrites in place.
**Why:** A third-party user cannot tell a deliverable from a working file by looking. Loose, unexplained, or duplicated artifacts erode trust and risk the wrong file being uploaded — exactly the confusion a data-prep assistant exists to remove.
**When to apply:** any time a skill produces files for the user (build-dataset Stage 6 export, prep-dataset export).
**Precedent:** a /build-dataset run left three JSONs loose beside the CSV in `output/` — the engine's dictionary, the profile recipe, and a redundant hand-made dictionary; the user could not tell which were theirs and asked why they existed.
**Source:** this session (25.06.2026); [CLAUDE.md](../../CLAUDE.md) `output/` layout; build-dataset skill Stage 5.
