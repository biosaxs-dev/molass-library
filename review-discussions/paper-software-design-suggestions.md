# Paper — Software Design Section: Pending Suggestions

Identified during AI-assisted notebook research session (2026-03-09, experiment 01f in molass-researcher).

The current Software Design paragraph is consistent with our actual practice, but two additions would strengthen it for reviewers.

---

## Suggestion 1 — Make the AI-readiness feedback loop concrete

**Current text** (paraphrased):
> "We are actively enhancing AI-readiness through systematic usability testing with AI agents and iterative improvements to API discoverability and inline documentation."

**Proposed addition** (one sentence after the above):
> "Friction points identified during active research sessions are tracked as GitHub Issues, providing a direct feedback loop between research use and library development — for example, opaque attribute names discovered during notebook work are immediately improved and recorded as issues in the public tracker."

**Rationale**: The current wording is assertive but abstract. A concrete description of the mechanism (notebook research → friction identified → GitHub Issue → fix) makes the claim verifiable by a reviewer.

---

## Suggestion 2 — Mention molass-researcher as evidence of researcher extensibility

**Current text** (paraphrased):
> "This approach allows domain researchers to maintain and extend the code using AI-assisted development tools."

**Proposed addition** (new sentence):
> "The companion repository `molass-researcher` provides a public record of AI-assisted research experiments that drive these improvements, demonstrating the library's use as a live research tool rather than a static analysis package."

**Rationale**: The "researcher extensibility" claim is currently asserted without evidence. `molass-researcher` is the living proof — referencing it makes the claim falsifiable and points reviewers to concrete material.

---

## Status
- [ ] Discuss with co-author (Shimizu) before incorporating
- [ ] Incorporate into `molass-library/paper.md` in this repo when agreed
- [ ] Sync to `joss-paper` branch in molass-library via subtree sync
