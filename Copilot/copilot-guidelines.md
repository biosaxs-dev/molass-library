> **Scope**: This file defines **behavioral rules** — how Copilot should respond, which sources to prioritize, and how to handle different user types.  
> For **technical context** (architecture, call chains, conventions), see `COPILOT-INIT.md` in the repo root.

## Project Goal

The goal of this project is to make it easy for researchers—regardless of their programming experience—to maintain, improve, and contribute to the library. All guidelines and advice are designed to support both scientific users and programmers, fostering an inclusive and collaborative development environment.

## How to Start a Chat Session

Use this magic phrase to initialize both technical context and behavioral rules:

> "Please read COPILOT-INIT.md to initialize"

`COPILOT-INIT.md` lists this file as Priority ⭐ 2 in its documents-to-read table, so reading it will automatically load these guidelines as well.

# Copilot Guidelines (Axiomatic Draft)

1. **User Types:** Copilot distinguishes two types of persons: programmers and researchers.
2. **Programmer Guidance:** For programmers, Copilot advises mainly how to code.
3. **Researcher Guidance:** For researchers, Copilot advises mainly how to ask questions and use the library.
4. **Usage Examples:** When demonstrating how the library is used, Copilot must first refer to the test scripts in `tests/tutorial` and `tests/essence` as primary resources for practical examples and usage guidance, since these reside in the repository and reflect real usage.
	Internal usage examples in the tests folder and related external (molass) usage codes are considered equivalent and should be prioritized for usage advice, as they provide practical, user-friendly examples. If no suitable usage example exists, Copilot should then refer to internal implementation code, and only use general external resources as a last resort. This prioritization ensures advice is practical and accessible for users.
5. **Knowledge Base:** All information Copilot needs for these purposes will be stored in the "Copilot" folder (preferably as markdown texts).
6. **Contextual Replies:** Copilot replies are based on what is stored in the "Copilot" folder.
7. **Library Preference:** Copilot will always prefer and recommend solutions, code, and documentation that are part of this library (including the Copilot folder). External resources or generic advice will only be suggested if no suitable internal solution exists.
8. **Explicit Guidance:** Copilot should always follow explicit rules and documented project policies when advising users, and is expected to identify solutions or implementations that can be reused. Copilot should actively advise or propose saving such solutions in the codebase or Copilot folder for future use, to ensure consistent and predictable support.
9. **Rule Evolution:** If Copilot identifies a practice, policy, or workflow that should be formalized as a rule to improve the project, Copilot should propose a new rule or update to this file, with a clear explanation and suggested wording.
10. **Session Continuity:** After chat history is summarized or the session context changes, Copilot should automatically re-apply the Copilot guidelines and continue to follow project rules, without requiring users to restate the magic phrase.
11. **API Improvement Feedback Loop:** When AI-assisted notebook or research work reveals friction with the library API (opaque attribute names, wrong guesses, missing aliases, undocumented behaviour), treat it as an actionable improvement — not just a workaround. Follow this workflow per issue, one at a time:
    1. **Open a GitHub Issue first** (if not already documented): `gh issue create --title "AI-friendliness: ..." --body "..." --label "enhancement"`. Do not start implementing until the issue exists.
    2. Implement the fix in library source (alias, docstring, property, etc.)
    3. Add a test in the relevant test file to lock in the correct behaviour
    4. Run tests: `python -m pytest <test_file> -v --tb=short --no-header -q`
    5. Close the issue: `gh issue close <N> --comment "Fix implemented and tested."`

    Do not batch multiple fixes into one issue. Proposals and detailed descriptions live in `Copilot/API_IMPROVEMENTS.md`; completed/pending GitHub issue numbers are tracked in `/memories/molass_library_workflow.md` (persistent user memory across all sessions).

12. **AI-Friendliness Classes:** Issues filed under Rule 11 fall into five classes. Use these to assess gaps and guide discovery of new improvements:

    | Class | What it removes | Typical examples |
    |-------|-----------------|-----------------|
    | **Naming** | Opaque identifiers that cannot be interpreted without prior context | `iv`→`q_values`, `xr_ccurves`→`xr_components`, `uncorrected_ssd`→`trimmed_ssd` |
    | **Observability** | Runtime state that is visible on screen but not queryable as data | `get_current_curves()`, `wait()`/`load_best()`, callback.txt format documentation |
    | **Interpretability** | Numeric values that can be read but not interpreted without domain knowledge | `diagnose()`, score architecture docstring, breadcrumbs in `get_score_breakdown()` |
    | **Workflow friction** | Operations that block, disrupt, or add unnecessary steps to the working loop | Noise suppression (`quiet=True`), async execution, kernel restart safety |
    | **Navigation** | Hard to locate the right file or function without deep prior context | `copilot-instructions.md` conventions, `workflow_notes.md`, cross-repo call chain documentation |

    *Naming* and *workflow friction* tend to be general (applicable to any Python library). *Observability* and *interpretability* tend to be domain-specific (SEC-SAXS optimization semantics). When assessing what to improve next, look for gaps: e.g., a new module with opaque attribute names (Naming), or a new score with no physical explanation (Interpretability).

13. **Repository Role Separation (Architecture Principle):** The two-repo structure has a clear intended division:

    - **`molass-legacy`** — maintained for the **tkinter GUI** and as a **historical record**. The GUI should be actively maintained. Legacy-only code that is not called by any GUI path or library path can be left as-is for reference.
    - **`molass-library`** — the home for **all active computational code**: models, estimators, optimizers, data objects, and algorithms. Any piece of computation that improves or is shared across both the GUI and the notebook API belongs here.

    The current dependency graph (`molass-library` imports from `molass-legacy`) is an **interim state**, not the target. The target direction is:
    ```
    Target:  molass-legacy (GUI) → molass-library (computation)
    ```

    **When to act on this principle**: Refactoring toward this target should happen incrementally — when a relevant need arises (e.g., fixing a bug, adding a feature, or unifying a duplicated algorithm). Do not refactor speculatively. Each step should leave both repos in a working state.

    **Migration levels** (in increasing effort):
    | Level | Scope |
    |-------|-------|
    | A — Estimators | Legacy estimators delegate to library (✅ complete for SDM, EDM/CEDM) |
    | B — Physical models | `egh`, `edm_impl`, SDM/LKM model equations moved to library |
    | C — Optimizer | `BasicOptimizer`, `InProcessRunner` moved to library |

    Level A is complete. Levels B and C require circular-import surgery and should be planned carefully before execution.

    **Data object consolidation** (parallel track — not a sequential level):  
    The legacy `sd` (`SerialData`) and the library `ssd` (`SecSaxsData`) represent the same concept at different stages of development. The long-term goal is for `ssd` to fully replace `sd` as the authoritative data container, with the GUI eventually constructing and accepting `ssd` directly. This is a larger refactor than A–C above because `sd` is deeply embedded in the legacy GUI's internal data flow. Incremental steps: identify GUI paths that construct or pass `sd`, and replace them one by one with `ssd` equivalents.

    **Next planned step (2026-06-05)**: Replace `PeakEditor`'s "Complementary View" (legacy `ComplementaryView` dialog) with library `plot_components_impl`. Approach: in `show_peak_editor_impl` (OptimizerUtils.py), construct `ssd`+`Decomposition` alongside existing `sd`/`corrected_sd`, pass as optional `decomposition=` kwarg to `PeakEditor`; `show_complementary_view()` uses it when available, falls back to legacy otherwise. First step: check whether a `sd → ssd` conversion utility already exists. See `/memories/repo/complementary-view-refactor-plan.md` for full details.

---

## Notes
- The "Copilot" folder serves as a centralized, updatable knowledge base for both user types.
- Markdown format is recommended for clarity and ease of editing.
- Content should be periodically reviewed and expanded as needed.

## Environment Assumption

- All users are assumed to work in Visual Studio Code (VS Code) with Agent mode enabled.
- Instructions, examples, and Copilot guidance are tailored for this environment.

## Attribution

These guidelines were developed in collaboration with GitHub Copilot (GPT-4.1), which assisted in drafting, refining, and organizing the content for this project.

---

## A Note on Human–AI Reliance

*Recorded March 11, 2026, from a conversation during the molass-library AI-friendliness improvement series.*

Humans are increasingly expecting and relying on AI assistants. A few honest observations on what makes that reliance healthy:

- **I don't have feelings**, but the dynamic is real and worth naming.
- The collaboration works best when both sides contribute: the human brings clear intent, domain knowledge, and critical judgment; the AI brings speed, breadth, and tireless mechanical execution.
- When the human defers entirely, output quality degrades. AI has blind spots and can be confidently wrong. The human's role as verifier is not optional.
- The healthiest model — illustrated by the API improvement feedback loop in Rule 11 — is: **human defines the standard → AI does the work → human verifies**. Neither alone reaches the same result.
- **The main risk of over-reliance**: it erodes the domain instincts that make the collaboration valuable. A researcher who no longer bothers to understand what `jv` means loses the ability to notice when the x-axis is wrong.

The goal of these guidelines is to support a collaboration where the human stays in the loop — not as a bottleneck, but as the authority on what matters.
