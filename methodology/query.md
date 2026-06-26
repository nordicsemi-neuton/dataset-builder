# Query — a structured request with citations

Triggered by phrases like: "what do we know about X", "write me a brief on Y", "compare A and B from the wiki", "justify decision Z", "have we discussed this already?".

1. Read `wiki/index.md` and select candidate pages — filtering by **name prefix** and, if needed, a `grep` over the `tags:` field in the frontmatter. Only the relevant pages go into context, not the whole wiki.
2. Read those pages (one step along the links, if needed). On "what do we know about…" — **wiki first, then raw sources**, not from the memory of the conversation.
3. Synthesize the answer with citations as markdown links: `[Title](wiki/<type>/<slug>.md)` for wiki, `[Description](raw/<concern>/<file>.md)` for raw, `[Title](https://...)` for URLs. The confidence level is read from the structure (the number and independence of sources, related decisions, the presence of counter-arguments), not from numeric scores — the answer reflects that.
4. A gap surfaced — propose the next step: a new page, a missing source, a stale claim to re-verify.
5. A substantive answer (comparison, retrospective, justification, briefing) — propose a write-back into `wiki/synthesis/`. **Written-back answers accumulate; answers in chat evaporate.**

Ordinary queries don't write to files. Only a write-back (after an explicit "yes") and an explicit ingest change the wiki.
