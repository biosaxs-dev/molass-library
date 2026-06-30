# Architecture: Repository Role Separation

**Source**: Rule 13 of `Copilot/copilot-guidelines.md`  
**Last updated**: Jun 2026

---

## Target dependency direction

```
Target:  molass-legacy (GUI) → molass-library (computation)
Current: molass-library imports from molass-legacy  (interim state)
```

- **`molass-legacy`** — maintained for the **tkinter GUI** and as a **historical record**.
  The GUI should be actively maintained. Legacy-only code not called by any GUI or library
  path can be left as-is for reference.
- **`molass-library`** — the home for **all active computational code**: models, estimators,
  optimizers, data objects, and algorithms. Any computation shared across GUI and notebook
  API belongs here.

**When to act**: Refactoring should happen incrementally — when a relevant need arises
(fixing a bug, adding a feature, unifying a duplicated algorithm). Do not refactor
speculatively. Each step must leave both repos in a working state.

---

## Migration levels (sequential track)

| Level | Scope | Status |
|---|---|---|
| **A — Estimators** | Legacy estimators delegate to library for all init logic | ✅ Complete (SDM, EDM, CEDM, EGH peak recognition) |
| **B — Physical models** | `egh`, `edm_impl`, SDM/LKM model equations moved to library | ⏳ Not started |
| **C — Optimizer** | `BasicOptimizer`, `InProcessRunner` moved to library | ⏳ Not started — requires circular-import surgery |

Levels B and C require careful circular-import analysis before execution.

---

## Data object consolidation (parallel track)

The legacy `sd` (`SerialData`) and the library `ssd` (`SecSaxsData`) represent the same
concept at different stages of development. Long-term goal: `ssd` fully replaces `sd`
as the authoritative data container, with the GUI eventually constructing and accepting
`ssd` directly.

This is a larger refactor than A–C because `sd` is deeply embedded in the legacy GUI's
internal data flow.

**Incremental steps**: identify GUI paths that construct or pass `sd`, replace them one
by one with `ssd` equivalents.

**Completed steps**:
- `PeakEditor` / `JobStateCanvas`: "Complementary View" replaced by library `plot_components_impl`
  (Jun 2026 — see `DESIGN_complementary_view_refactor.md`)

---

## Subprocess parity (orthogonal issue)

The GUI always uses `in_process=False` (subprocess via `BackRunner`). The subprocess
re-derives data from disk, bypassing the library's prepared data. This causes a ~5–6 SV
gap for new solvers (DE, NSGA2).

See `PLAN_subprocess_parity.md` for the full analysis and fix options.
