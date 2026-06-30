<!-- AI Context Standard v0.9.2 - Adopted: 2026-05-07 -->
# AI Assistant Initialization Guide — molass-library

**Purpose**: Initialize AI context for coding work in this repository  
**Created**: February 19, 2026

> **Note**: This file follows the AI Context Standard (v0.8). It provides **technical context** (architecture, call chains, conventions).  
> For **behavioral rules** (response style, user types, source priorities), see `Copilot/copilot-guidelines.md` (Priority ⭐ 2 below).  
> For current development status and task history, see `PROJECT_STATUS.md` (in this repo).

> **On every session start**: Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) to get the current task and recent context before responding.

---

## 📚 Documents to Read

| Priority | File | Purpose |
|----------|------|---------|
| ⭐ 1 | `README.md` | Project overview & entry points |
| ⭐ 2 | `Copilot/copilot-guidelines.md` | Project policies and user-type rules |
| ⭐ 3 | `Copilot/workflow_notes.md` | AI workflow notes: issue patterns, terminal tips, issue history |
| 4 | `pyproject.toml` | Package version, dependencies, test config |
| 5 | `tests/tutorial/01-quick_start.py` | Canonical usage example (start here for API) |
| 6 | `tests/tutorial/05-lrf.py` | Low-rank factorization (LRF) tutorial |
| 7 | `tests/tutorial/11-rigorous_optimization.py` | Rigorous optimization tutorial |

---

## 🏗️ Architecture Overview

### What Molass Does

Molass decomposes SEC-SAXS data: the measured 2D matrix $M$ (q-values × elution frames) is factored into scattering profiles $P$ and elution curves $C$ via $M \approx PC$.

The data flows through three main stages:

```
Raw data folder / molass_data sample
        ↓
   SecSaxsData (DataObjects/)          ← Load, trim, correct
        ↓
   quick_decomposition()               ← Low-rank factorization (LRF)
        ↓
   Decomposition object (LowRank/)     ← Holds xr_ccurves, uv_ccurves, components
        ↓
   make_rigorous_decomposition()       ← (Optional) Physics-constrained refinement
        ↓
   Reports / DENSS                     ← Output
```

### Key Packages

| Package | Role |
|---------|------|
| `DataObjects/` | Core data containers: `SecSaxsData`, `XrData`, `UvData`, `SsMatrixData`, `Curve` |
| `LowRank/` | Matrix factorization engine: `Decomposition`, `CurveDecomposer`, `CoupledAdjuster`, `QuickImplement` |
| `Rigorous/` | Physics-constrained optimization (EGH/SDM/EDM elution models + Rg-consistency); bridges to `molass-legacy` |
| `SEC/Models/` | Column elution models: `EDM.py`, `SDM.py`, `Simple.py` (+ Gaussian, lognormal pore distributions) |
| `Guinier/` | Rg estimation: `RgEstimator`, `RgCurve`, `RgCurveUtils` |
| `Peaks/` | Peak recognition: `Recognizer`, `PeakSimilarity` |
| `Decompose/` | Helper utilities for decomposition variants (proportional, XR-only) |
| `Global/` | Global optimization options (`Options.py`) |
| `Baseline/` | Baseline correction |
| `Trimming/` | Data trimming |
| `SAXS/` | DENSS integration (`DenssTools`), MRC viewer (`MrcViewer`) |
| `Shapes/` | Geometric shapes for scattering models (`Ellipsoid`, `Sphere`) |
| `Testing/` | Test infrastructure (`control_matplotlib_plot` decorator, etc.) |
| `Legacy/` | Bridge to `molass-legacy` package |

### Important Relationships

- **`molass-legacy`** is a required dependency (installed separately). The `Rigorous/` module bridges to it heavily via `LegacyBridgeUtils.py`. Do not assume all optimization logic is in `molass-library`.
- **`molass_data`** is a separate data package (not in this repo) that provides test samples (`SAMPLE1`–`SAMPLE4`).
- **Dual-channel design**: `SecSaxsData` carries both XR (X-ray) and UV data. Many methods have `xr_only` variants. REGALS uses SAXS only; Molass uses UV + SAXS (information asymmetry — document when comparing).
- **EDM `e` parameter**: In `molass_legacy/SecTheory/Edm.py`, `e` (default 0.4) is **V₀/(V₀+Vp)** — the mobile-phase fraction of the *accessible* volume only. Solid bead volume is entirely outside the EDM mass balance. This is **not** the standard chromatographic total porosity ε_T=(V₀+Vp)/V_column. The phase ratio `F=(1-e)/e = Vp/V₀` directly. In the 2D column simulation (`SEC/ColumnSimulation.py`, rs=0.0381, ~42 grains): V₀≈0.109, Vp≈0.096, V_solid≈0.096 → e≈0.53, F≈0.88. The Henry coefficient `a = K_SEC × (Vp/V₀)`; default a=1.5 requires Vp/V₀≥1.5 (beyond the simulation geometry).

### The Canonical Usage Pattern

```python
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD

ssd = SSD(SAMPLE1)                        # Load raw data
trimmed = ssd.trimmed_copy()              # Trim to SEC peak region
corrected = trimmed.corrected_copy()      # Baseline correction
decomposition = corrected.quick_decomposition()   # LRF (P0+–P5+ relevant here)
decomposition.plot_components()           # Inspect result
```

Rigorous refinement (optional, bridges to molass-legacy):
```python
from molass.Rigorous import make_rigorous_decomposition
result = make_rigorous_decomposition(decomposition, rgcurve)
```

---

## 🧪 Testing Conventions

### Test Structure

```
tests/
├── tutorial/       ← End-to-end usage examples (primary usage reference per guidelines)
├── essence/        ← Mathematical/theoretical foundations (24-*, 41-*, 61-*, etc.)
├── generic/        ← Cross-cutting functionality tests
├── specific/       ← Module-specific unit tests
└── technical/      ← Infrastructure and environment tests
```

### Running Tests

```powershell
# All tests
python run_tests.py

# Specific category
pytest tests/tutorial/ -v

# With coverage
pytest --cov=molass tests/
```

### Test File Naming

- Tutorial tests: `01-quick_start.py`, `02-data_objects.py`, ... (ordered with `pytest-order`)
- Essence tests: `21-gaussian.py`, `41-lrf_and_svd.py`, ... (numbered by topic)
- The `@control_matplotlib_plot` decorator from `molass.Testing` suppresses plot display during automated tests

### Key Test Config (pyproject.toml)

```toml
[tool.pytest.ini_options]
pythonpath = [".", "../molass-legacy"]   # molass-legacy must be sibling directory
env = ["MOLASS_ENABLE_PLOTS=false", "MOLASS_SAVE_PLOTS=false"]
```

---

## 🔑 Working Conventions

### 1. Usage Example Priority

Per `Copilot/copilot-guidelines.md` Rule 4:  
**Reference order**: `tests/tutorial/` → `tests/essence/` → implementation code → external resources.  
Always check tutorial tests first before reading implementation internals.

### 2. Module Reload Pattern

Many internal modules use `importlib.reload()` at the top of functions (e.g., `QuickImplement.py`, `RigorousImplement.py`). This is intentional for development convenience. Do not remove these when editing unless explicitly asked.

### 3. Types of Users

Defined in `Copilot/copilot-guidelines.md` Rules 1–4. In short: researchers → direct to `tests/tutorial/`; programmers → read implementation, then tests.

### 4. R-Centric Framework (from research context)

When analyzing or improving decomposition quality, frame analysis in terms of transformation matrix $R$:
- $P_\text{true} = P_\text{svd} \cdot R$, $C_\text{true} = R^{-1} \cdot C_\text{svd}$
- The goal of every constraint (Rg-consistency, elution model, non-negativity) is to determine or restrict $R$
- See `modeling-vs-model_free/R_CENTRIC_FRAMEWORK.md` for full framework

### 5. Decomposition Call Chain (traced Feb 19, 2026)

Two distinct code paths exist for `quick_decomposition()`:

**Default path** (no `proportions`):
```
SecSaxsData.quick_decomposition(num_components=2)
  → QuickImplement.make_decomposition_impl()
    → CoupledAdjuster.make_component_curves()
      → CurveDecomposer.decompose_icurve_impl(icurve, num_components)
        → recognize_peaks(x, sy, num_peaks, exact_num_peaks)  # from molass-legacy!
          → get_a_peak(): greedy sequential subtraction (fit tallest → subtract → repeat)
        → fit_objective(): 6 penalty terms (data fit, area proportion, tau, mean order, sigma order, Guinier)
        → scipy.optimize.minimize(method='Nelder-Mead')  # SINGLE RUN, no multi-start
      → ComponentCurve(x, params)  # EGH model: (H, tR, sigma, tau)
    → Decomposition(ssd, xr_icurve, xr_ccurves, ...)
```

**Proportions path** (`proportions=[1, 1]` etc.):
```
SecSaxsData.quick_decomposition(num_components=2, proportions=[1, 1])
  → QuickImplement.make_component_curves_with_proportions()
    → Proportional.decompose_proportionally(icurve, proportions)
      → get_proportional_slices(): cumulative area split by given ratios
      → estimate_initial_params(): fit EGH to each slice independently
      → Two-stage optimizer: scale-only → full joint Nelder-Mead
    → ComponentCurve(x, params)
  → Decomposition(...)
```

**Key insight**: The default path fails at high overlap because `recognize_peaks` (greedy subtraction) produces bad initialization when peaks merge. The proportions path bypasses this entirely with cumulative-area slicing. Values are normalized internally, so `[1,1]`, `[0.5,0.5]`, `[3,3]` give the same result.

**Critical file**: `molass/LowRank/CurveDecomposer.py` — contains `decompose_icurve_impl()` with:
- `randomize` kwarg (default 0) — adds Gaussian noise to init params
- `global_opt` kwarg (default False) — enables `scipy.optimize.basinhopping`
- `sec_constraints` kwarg — adds Guinier penalty via denoised data matrix
- Neither `randomize` nor `global_opt` is used by the default `quick_decomposition()` call

**Unused fix levers**: `randomize` and `global_opt` already exist as code paths but are never activated in the default call chain. They are candidate levers for improving P1+ without rewriting `recognize_peaks`. If a future session wires them into `quick_decomposition()`, the default-path overlap failure may be mitigated without requiring the `proportions` workaround.

**Cross-repo dependency**: `recognize_peaks` lives in `molass-legacy/molass_legacy/QuickAnalysis/ModeledPeaks.py`, not in molass-library.

### 6. Subprocess Coordinate Contract (Issue #80)

When `optimize_rigorously()` exports data for the legacy subprocess (`needs_export=True`, e.g. anomaly-masked datasets), the following contract applies:

1. **Exported filenames carry original frame numbers** from `ssd.xr.jv` (e.g. `PREFIX_00032.dat`), so the legacy loader sets `start_file_no` correctly.
2. **Restrict-lists are identity** `(0, N, N)` — no re-trimming; data is already trimmed.
3. **The subprocess does NOT need** `elution_recognition`, anomaly masks, or original trimming info — all preprocessing is already applied.

**Continuity assumption**: Exported frame numbers are always contiguous (no gaps). This is guaranteed because `trimmed_copy()` takes a contiguous slice of `jv`. The legacy loader relies on this: it constructs `jvector = np.arange(N)` and uses `start_file_no` (from the first filename) as a simple offset. If files had gaps, `jvector` would not reflect actual frame numbers.

**Key files**: `Rigorous/RigorousImplement.py` (`_set_identity_restrict_lists`), `DataUtils/ExportSsd.py`.

### 7. Evaluation Criteria (P0+–P6+)

The research repo defines 7 positive criteria for method evaluation. When improving Molass:

| Criterion | Module most relevant |
|-----------|---------------------|
| P0+ (handle R ≠ I) | `LowRank/CoupledAdjuster.py`, `Guinier/` |
| P1+ (graceful overlap degradation) | `LowRank/CurveDecomposer.py`, `Decompose/Proportional.py` |
| P2+ (resolve permutations) | `Guinier/RgCurve.py`, `Peaks/Recognizer.py` |
| P3+ (cross singularity barriers) | `Rigorous/RigorousImplement.py` (parametric C) |
| P4+ (escape local traps) | `Global/Options.py`, rigorous optimizer |
| P5+ (constrained global search) | `Rigorous/`, EGH/SDM/EDM models |
| P6+ (Kratky preprocessing) | Not yet implemented — candidate feature |

### 8. Expensive-Object Caching Pattern (May 2026)

When a method produces an expensive computed object (like `RgCurve`), follow this three-layer pattern:

1. **`get_<noun>()`** on the highest-level object the user already holds signals "cached, safe to call repeatedly". It computes on first call and returns the cached result thereafter.
2. **Downstream methods** (`quick_decomposition`, `optimize_rigorously`, etc.) accept it as an optional parameter. If passed, they use it; if omitted, they compute it internally. No required parameters added.
3. **Naming**: `get_rg_curve()` (with underscore, `get_` prefix) — not `compute_rgcurve()`. The `get_` prefix is the convention for cached accessors; `compute_` means "always runs".

**Canonical workflow** (no redundant computation):
```python
rgcurve = corrected.get_rg_curve()                      # once, cached on corrected
decomp   = corrected.quick_decomposition(rgcurve=rgcurve)  # injected → cached in decomp
run_cma  = decomp.optimize_rigorously(rgcurve=rgcurve, ...)
run_bh   = decomp.optimize_rigorously(rgcurve=rgcurve, ...)
```

**Implemented so far**: `SecSaxsData.get_rg_curve()`, `Decomposition.get_rg_curve()` (issue #168).  
**When adding new expensive objects** (e.g. `baseline2d`, `peak_positions`): apply the same pattern.

### 9. Version Convention

- Check `pyproject.toml` for current version (e.g., `0.8.2`)
- `molass/__init__.py::get_version()` reads from `pyproject.toml` during local development, falls back to `importlib.metadata` for installed package
- Use `get_version(toml_only=True)` in development to avoid confusion between local and installed versions

### 10. Rigorous Optimization Internals (Issue #107)

**Score Value (SV)**: The optimizer's raw objective `fv` is converted to a 0–100 scale for display:
```
SV = -200 / (1 + exp(-1.5 * fv)) + 100
```
Thresholds: **≥80 Good**, **60–80 Fair**, **<60 Poor**. Defined in `molass_legacy/Optimizer/FvScoreConverter.py` (`convert_score()`), aliased as `fv_to_sv()` in `molass/Rigorous/CurrentStateUtils.py`.

**Split architecture (Phase 4, April 2026)**: `optimize_rigorously()` now defaults to `in_process=True`. Two paths exist:

| | In-process (default, `in_process=True`) | Subprocess (`in_process=False`) |
|---|---|---|
| Who uses it | Notebook / library API | Legacy tkinter GUI |
| Optimizer source | Parent's prepared object (live dsets, base curves, spectral vectors) | Re-derived from disk via `OptimizerInput` |
| Parent/subprocess divergence | Impossible — one process | Structural — two independent derivation pipelines (issues #117, #119) |
| Crash isolation | None (kernel dies on segfault) | Yes (subprocess isolated) |
| Key file | `molass_legacy/Optimizer/InProcessRunner.py` | `molass_legacy/Optimizer/BackRunner.py` |

Design rationale: see `molass-library/Copilot/DESIGN_split_optimizer_architecture.md`.

**callback.txt format**: Both paths write the same format. Each optimizer evaluation appends:
```
t=<timestamp>
x=
[param_0 param_1 ... param_n]    ← may span multiple lines for long arrays
f=<fv_value>
a=<True|False>                   ← accepted by optimizer
c=<evaluation_count>
```
Parse `f=` lines with: `re.finditer(r'^f=([\-\d.eE+]+)', content, re.MULTILINE)`

**SV consistency across methods (verified April 2026)**: SV is on the same scale for both Basin-Hopping (`bh`) and Nested Sampling (`ultranest`). The reason:
- UltraNest internally receives `-fv` as its log-likelihood (`my_likelihood` in `SolverUltraNest.py` returns `-fv`). This negation is entirely internal; UltraNest maximises it, which is equivalent to minimising `fv`.
- `callback.txt` always records the **raw `fv`** — the NS callback re-evaluates `self.objective(params)` directly (ignoring the negated `f` argument UltraNest passes), so `fv` in `callback.txt` is on the same scale as BH.
- `convert_score(fv)` is therefore applied to the same `fv` scale in both methods.
- Side-effect: the NS callback incurs one extra `objective_func` evaluation per accepted live-point (it re-evaluates instead of using `-f` from UltraNest). This is harmless for correctness but slightly wasteful.

**Widget title vs best accepted SV (issue #128)**: The `MplMonitor` widget title (panel 3) now shows `"best SV=XX.X  (cur=YY.Y)"`. `best SV` is `convert_score(min(job_state.fv[:, 1]))` — the global min over all **accepted** NS callbacks. `cur` is the SV of the params being rendered at that snapshot. These can differ: UltraNest live-point proposals can temporarily visit higher-SV regions that are never accepted, making the `cur` value mislead upward relative to the converged best.

**Live run observability stack (April 2026)**: For any in-flight or completed rigorous run, prefer the canonical one-call probe over hand-rolled `sv_history` + `check_progress` + manifest reads:

| Source | Probe |
|--------|-------|
| `RunInfo` (single run) | `run.live_status()` (issue #133) |
| `ComparisonResult` (compare_optimization_paths) | `cmp.live_status()` or `cmp.live_status('subprocess')` |
| External observer (no notebook cell) | `aicKernelEval(expression="run.live_status()")` (ai-context-vscode#1) |

`live_status()` returns `{phase, n_evals, best_fv, best_sv, elapsed_s, analysis_folder, work_folder, subprocess_pid, subprocess_returncode, manifest}` in one disk read. It composes with `RunRegistry` (`molass.Rigorous.read_manifest`, `locate_recent_runs`) which writes/reads `RUN_MANIFEST.json` breadcrumbs in both `analysis_folder` and `work_folder`. Use these instead of parsing `callback.txt` directly.

**Monitor readability (molass-legacy#31, April 2026)**: `MplMonitor.get_current_curves()` returns the same data currently shown on the dashboard as a plain dict — enabling the AI to reason from the same evidence the human sees on screen. This is the canonical solution for *monitor readability*, a special class of AI-friendliness where the monitor's visual state was previously inaccessible to the AI. The user-facing entry point is `run_info.get_current_curves()`, which delegates to the monitor. Keys: `xr_frames`, `xr_data`, `xr_model`, `xr_components`, `uv_frames`, `uv_data`, `uv_model`, `uv_components`, `sv_history`, `best_sv`, `params`. When the user reports a visual deviation on the dashboard (e.g. "UV component doesn't match the data peak"), call `run_info.get_current_curves()` to get the numeric values and confirm.

**Score diagnosis (molass-library#145, April 2026)**: `run_info.diagnose(breakdown=None)` maps numeric score values to physical interpretations. Calls `get_score_breakdown()` automatically if no breakdown is passed. Returns a list of `Diagnosis(score, status, reason, suggestion)` namedtuples with `status` in `('good', 'fair', 'poor', 'failing')`. Encoded rules: `UV_LRF_residual` near zero → failing UV low-rank fit (model completely misaligned); `UV_2D_fitting / XR_2D_fitting < 0.33` → UV much worse than XR, likely alignment issue; `Guinier_deviation > -0.5` → poor Rg consistency; penalties > 0.1 → physical constraint violated. When `diagnose()` flags a UV issue, its `suggestion` field points to `run_info.get_current_curves()` as the next diagnostic step. Use this whenever `get_score_breakdown()` returns numbers that need interpretation — do NOT rely on domain knowledge from the session context.

**In-process kernel restart safety (molass-legacy#26, April 2026)**: `optimize_rigorously(in_process=True)` is now safe to interrupt with VS Code "Restart Kernel". Previously, `optimizer.solve()` ran directly on the main thread; UltraNest's back-to-back numpy C calls held the GIL long enough to block `KeyboardInterrupt` delivery, causing the kernel to hang and VS Code to spawn duplicate kernels. Fix: `solve()` runs in a `daemon=True` thread; the main thread loops on `thread.join(timeout=0.05)`, releasing the GIL every 50 ms as an interrupt delivery point. Key file: `molass_legacy/Optimizer/InProcessRunner.py`.

**In-process wall-time gap and Phase 5 analysis (April 2026)**: The in-process path was ~5× slower than subprocess before molass-legacy#18 fixed two root causes: (1) `ColumnInterp.D_` stored in C (row-major) order causing per-column cache misses → switched to Fortran order for 1.87× speedup; (2) GC cycle detector overhead ~25% → wrapped `optimizer.solve()` in `gc.disable()` / `gc.enable()` for 1.33× speedup. A residual ~13% wall-time gap remained (measured before these fixes); **re-benchmarking is needed** to know the current state.

Phase 5 (molass-library#134, `isolated=True`) proposes `ProcessPoolExecutor` for crash isolation, but **this will not work on Windows** because the default start method is `spawn` (not `fork`) and `BasicOptimizer` is not picklable (holds a `Logger`, threading locks, C-extension state). The two Phase 5 goals — crash isolation and GIL-free performance — are separable: the performance goal may be solved for free by switching to Python `3.14t` (free-threaded build). Full analysis in `Copilot/DESIGN_split_optimizer_architecture.md` § "Phase 5 — Windows / GIL analysis".

---

## 📂 Repository Structure Quick Reference

```
molass-library/
├── .github/
│   └── copilot-instructions.md  ◄── This file (auto-loaded by GitHub Copilot)
├── README.md                ◄── Project entry point
├── pyproject.toml           ◄── Version, deps, test config
├── run_tests.py             ◄── Test runner
│
├── Copilot/
│   └── copilot-guidelines.md  ◄── Chat session rules
│
├── molass/                  ◄── Main package
│   ├── DataObjects/         ◄── SecSaxsData, XrData, UvData
│   ├── LowRank/             ◄── Decomposition, CurveDecomposer
│   ├── Rigorous/            ◄── Physics-constrained optimization
│   ├── SEC/Models/          ◄── EDM, SDM, Simple elution models
│   ├── Guinier/             ◄── Rg estimation
│   ├── Peaks/               ◄── Peak recognition
│   ├── Global/              ◄── Global optimizer options
│   ├── SAXS/                ◄── DENSS integration
│   └── [25+ more modules]
│
├── tests/
│   ├── tutorial/            ◄── Primary usage examples (01–11)
│   ├── essence/             ◄── Mathematical foundations (21–71)
│   ├── generic/             ◄── Cross-cutting tests
│   └── specific/            ◄── Module-specific tests
│
└── docs/                    ◄── Sphinx docs (multiple doc sites)
```

---

## 🔗 Multi-Root Workspace Context

### Full Repository Ecosystem

| Repository | Role | Tool | AI Context File |
|------------|------|------|----------------|
| `molass-library` | Main library (this repo) | Python / Sphinx | `.github/copilot-instructions.md` ← this file |
| `molass-legacy` | Legacy GUI predecessor; required runtime dep | Python / Sphinx | `.github/copilot-instructions.md` |
| `modeling-vs-model_free` | Research: P0+–P6+ criteria, evaluation, roadmap | Markdown / Notebooks | `.github/copilot-instructions.md` |
| `molass-tutorial` | Usage documentation (Jupyter Book) | MyST Markdown | `.github/copilot-instructions.md` |
| `molass-essence` | Theory documentation (Jupyter Book) | MyST Markdown | `.github/copilot-instructions.md` |
| `molass-technical` | Technical report (Jupyter Book) | MyST Markdown | `.github/copilot-instructions.md` |
| `molass-develop` | Developer/contributor handbook (Jupyter Book) | MyST Markdown | `.github/copilot-instructions.md` |
| `molass-beginner` | Beginner onboarding (Agent mode) | Markdown | `.github/copilot-instructions.md` |

**Related (not doc repos)**:
- `molass-data` — test data package (provides `SAMPLE1`–`SAMPLE4`)
- `regals` — REGALS implementation used for evaluation comparisons (`C:\Users\takahashi\GitHub\regals`)

### Current VS Code Workspace

`C:\Users\takahashi\GitHub\molass-workspace.code-workspace` opens **all repos** side by side:

```
GitHub/
├── modeling-vs-model_free/  ← Research & evaluation (P0+–P6+ criteria, roadmap)
├── molass-library/          ← This repo (Molass source code)
├── molass-legacy/           ← Legacy code (required as a dep, reference only)
├── molass-tutorial/         ← Usage documentation (Jupyter Book, MyST Markdown)
├── molass-essence/          ← Theory documentation (Jupyter Book, MyST Markdown)
├── molass-technical/        ← Technical report (Jupyter Book, MyST Markdown)
├── molass-develop/          ← Developer handbook (Jupyter Book, MyST Markdown)
└── molass-beginner/         ← Beginner onboarding (Agent mode)
```

**In VS Code multi-root workspace**: All repos are open simultaneously. You can read/edit files in any repo without switching windows. Use absolute paths when referencing across repos.

**Why this matters**: `Rigorous/` in this repo calls into `molass-legacy/` at runtime. The legacy repo directory must be a sibling of this one (see `pythonpath` in `pyproject.toml`).

---

## 💡 Quick Tips for AI Assistants

- **First, check tutorials**: Before reading implementation, look for the relevant test in `tests/tutorial/`
- **Reload pattern is intentional**: Don't remove `importlib.reload()` calls
- **Dual-channel**: Always check whether a method uses UV, XR, or both before proposing changes
- **Legacy bridge**: `Rigorous/` depends on `molass-legacy` — changes there may need mirroring
- **Adding features**: After implementing, add a test in `tests/specific/` or extend the relevant tutorial test
- **After each fix**: Document what you learned here in the relevant section above

---

## Notebook workflow

Read [NOTEBOOK_CONVENTIONS.md v0.2.6](https://github.com/freesemt/ai-context-standard/blob/main/NOTEBOOK_CONVENTIONS.md) before working with any notebook in this repo.  
Kernel preference: global Python (`py`). Do not create venvs.

---

## Response language

**Response language**: English

---

## 🔄 Updates (AI-Readiness Trail)

| Date | What was learned / added |
|------|--------------------------|
| Feb 19, 2026 | Initial file created — first visit (architecture survey) |
| Feb 19, 2026 | P1+ diagnosis: traced full decomposition call chain (default vs proportions paths); identified root cause of overlap failure (greedy `recognize_peaks` + single Nelder-Mead); confirmed `proportions` option as effective workaround (std≤0.02 vs 0.27, robust to 3:1 mismatch); improved `quick_decomposition()` docstring and tutorial pages |
| Feb 19, 2026 | AI-readability pass: added inline comments at `recognize_peaks` import and call site in `CurveDecomposer.py` (algorithm summary, failure mode, cross-repo pointer); noted `randomize`/`global_opt` as unused fix levers in this file; created entry point for AI navigating `recognize_peaks` and other legacy code |
| Mar 24, 2026 | Migrated to `.github/copilot-instructions.md` (AI Context Standard v0.7) |
| Mar 25, 2026 | Updated to AI Context Standard v0.8; added `init.prompt.md` and `vscode-version.txt`; refreshed ecosystem table |
| May 2026 | **molass-legacy#34 (part 1)**: subprocess optimizer diverged from parent because `prepare_rigorous_folders` skipped re-exporting the `LegacyRgCurve` when the rg-curve folder already had stale data. Fix: always overwrite the rg-curve folder in `prepare_rigorous_folders` (`LegacyBridgeUtils.py`). Debugging infrastructure created: `DsetsDebug.py`, `test_dsets_debug.py`, `RunInfo.compare_subprocess_dsets()`. |
| Apr 29, 2026 | **molass-legacy#34 fully closed**: final divergence source was `uv_curve.spline` built with 0-based x (via `Absorbance.a_curve → ElutionCurve(y)`) while objective evaluates at original frame numbers (463–1402). With `ext=3`, all queries outside `[0, 939]` returned boundary value → flat `uv_y` → wrong `UV_2D_fitting` penalty (−0.44 vs −1.89) → SV=70 vs 78. **Fix**: added spline rebuild in `BasicOptimizer.__init__` (molass-legacy, `Optimizer/BasicOptimizer.py`): after `self.uv_curve = uv_curve`, if `uv_curve.x[0] > 100` but `spline.get_knots()[0] ≈ 0`, rebuild with original frame x. Verified: SV=78.23 vs parent 78.24 (delta_fv=0.0003). Issue closed. |
| May 2026 | **molass-legacy#38**: ElCurve derivation divergence — subprocess re-derived xr_curve/uv_curve from disk (legacy correction) while in-process used `ssd.xr.M`/`ssd.uv.M`. Fix: export `ip_xr_curve.npy`/`ip_uv_curve.npy` in `prepare_rigorous_folders`, override in `get_dsets_impl`. Issue closed. |
| May 2026 | **molass-legacy#39**: D/U matrix divergence — same pattern as #38 but for the 2D intensity matrices D and U. Export `ip_xr_D.npy`/`ip_uv_U.npy`, override in `get_dsets_impl`. Issue closed. |
| May 2026 | **molass-legacy#40**: E (error) matrix divergence — even after fixing D/U, a ~3 SV gap persisted. `OptDataSets.__init__` calls `compute_weight_info(1/(E+D/100))`; in-process uses `ssd.xr.E`, subprocess used `sd.intensity_array[:,:,2].T`. Fix: export `ip_xr_E.npy`, load via `get_dsets_impl(return_e_override=True)`, override in `OptDataSets.__init__`. Test `test_xr_E_returned_as_override_when_npy_exists` added (20 tests pass). Issue closed. |
| May 2026 | **molass-legacy#41**: qvector divergence — subprocess `sd.qvector` has 972 elements (from `get_sd_from_folder_impl` → legacy trimming of raw data; starts at q=0.01325), in-process `corrected.xr.q_values` has 966 elements (molass-library trimming; starts at q=0.01573). Difference shifts GuinierDeviation bisection → divergent initial fv even with identical parameters. Fix: export `ip_xr_qvector.npy` in `prepare_rigorous_folders` (LegacyBridgeUtils.py); override `qvector` in `create_optimizer_from_job` (OptimizerMain.py). `TestQvectorOverride` added (22/22 tests pass). Issue closed. |
| May 2026 | **molass-legacy#42**: FixedBaselineOptimizer asymmetry — subprocess `optimizer_main` wrapped the optimizer in `FixedBaselineOptimizer` when `strategy.trust_initial_baseline()` returned True (always True for EGH/DefaultStrategy), fixing ~22 baseline parameter indices at initial values. `InProcessRunner` never applied this wrapper. Root cause: in-process achieves better SVs precisely because all parameters are free. Fix: removed the `trust_initial_baseline()` branch from `optimizer_main`; both paths now call `optimizer.solve()` directly. `FixedBaselineOptimizer` kept in codebase for future explicit use. Commit `212d343`. Issue closed. |
| May 2026 | **molass-legacy#50**: Race condition in `MplMonitor.update_plot()` (watch_thread) calling `objective_func(best_params)` concurrently with the BH sub-minimizer, causing the sub-minimizer to use corrupted optimizer state → frozen progress. Fix: `threading.Lock` (`_objective_lock`) in `BasicOptimizer.__init__`; `objective_func_wrapper` holds lock for entire evaluation; `MplMonitor.update_plot()` acquires same lock with `timeout=2.0s` before calling `plot_job_state`. On timeout, `display_optimizer=None` → placeholder shown. Issue closed (commits a2e63a1, c2555e2). |
| May 2026 | **molass-legacy#52**: Duplicate upper panel in monitor dashboard for fast datasets (ATP, MY). Root cause: IPython double-routing — `display(fig)` called from a background thread inside `with Output():` while the launching cell is still executing routes the display message to both the cell's raw inline output and the Output widget simultaneously. Fix: render to PNG bytes via `fig.savefig()` then assign `self.plot_output.outputs = (...)` directly as a trait mutation, bypassing IPython routing. File: `MplMonitor.update_plot()`. |
| May 2026 | **molass-legacy#51**: Stale `uv_curve.sy` after `ip_uv_elcurve_y.npy` override — root cause of systematic UV baseline deviation (~2 SV gap between in-process and subprocess). `ElCurve` stores `self.sy` (legacy smoothed curve); ip override updates `y` and `spline` but not `sy`. `BasicOptimizer.__init__` molass-legacy#34 guard runs AFTER `apply_x_shifts` (which shifts `uv_curve.x` from 0-based to [464,...,1402]) and rebuilds spline from `getattr(uv_curve, 'sy', uv_curve.y)` — uses stale `sy` → objective uses legacy elution curve for `uv_y = uv_curve.spline(uv_x)` → wrong `Cuv` matrix → UV LRF computed from legacy data. Fix: add `uv_curve.sy = _new_uv_y` in `get_dsets_impl` ip override code. File: `molass_legacy/Optimizer/OptDataSets.py`. Issue closed (commit b26f1d8). |

| May 2026 | **molass-library#164**: AI-friendliness: `UserWarning` when `optimize_rigorously()` is called without `trimmed_ssd` on corrected data (Pattern A). Two changes: (1) `corrected_copy()` in `SecSaxsData.py` sets `ssd_copy.corrected = True`; (2) warning check in `make_rigorous_decomposition_impl()` in `RigorousImplement.py` fires after the `reload/import` block but before `prepare_rigorous_folders`. Warning cites `stacklevel=3` (user cell → `Decomposition.optimize_rigorously` → impl). Placement constraint comment added: the block must remain ABOVE `with _stack:` since `_stack` enters `warnings.simplefilter("ignore")`. Issue closed. |
| May 2026 | **molass-library#165**: Design: added `_dry_run=False` internal parameter to `optimize_rigorously()` and `make_rigorous_decomposition_impl()`. When `True`, fires all pre-flight checks (warnings, guards) then returns `None` immediately without building the optimizer. Tests in `test_090_pattern_a_warning.py` rewritten to use `_dry_run=True` — previous fragile reload-patch hack (patching `RigorousImplement.reload` to inject a sentinel raiser) fully removed. Test runtime unchanged (~106s, bottleneck is SAMPLE1 data load + `quick_decomposition`, not the optimizer). Issue closed. |
| May 2026 | **molass-library#166**: AI-friendliness: anomaly exclusion bands never appeared in the MplMonitor dashboard when using `in_process=True` (the default). Root cause: the code setting `monitor.anomaly_jv`/`monitor.anomaly_mask` was placed after `return run_info` in the in-process path — unreachable. Fix: moved the setup into the `if progress == 'dashboard':` block in `make_rigorous_decomposition_impl()`, immediately after `run_info.monitor = mon`. Also fixed `get_anomaly_mask_from_ssd` in `AnomalyBands.py` to convert `slice` objects (stored by `set_anomaly_mask()`) to boolean arrays — previously only boolean arrays were handled. Why the bands matter: the optimizer interpolates anomaly frames rather than fitting them; without bands the dashboard shows the interpolated region as if it were real data. Issue closed. |

| May 2026 | **molass-legacy#55 (num_trials resume)**: `MplMonitor.from_run_info()` initialized `num_trials=0` unconditionally, so the dashboard label showed "Job 000" even when resuming a prior run (e.g. jobs 000–008 already existed). First fix (fb3ccc2): count non-empty existing job folders — but this had an off-by-one race condition: the daemon thread may write `init_params.txt` to the new folder before `from_run_info()` finishes counting, producing "Job 011" instead of "Job 010". Second fix (5151fff): derive `num_trials = int(basename(run_info.work_folder))` — `work_folder_callback` is called before any files are written, so the path basename gives the correct 0-based job number with no race condition. Brief poll (≤2s) guards the rare case where the callback hasn't fired yet. |
| May 2026 | **molass-legacy#56**: Terminate button appeared to hang — `minima_callback` returned `False` unconditionally, never signaling BH to stop. Ctypes KI injection only fires at the next Python bytecode boundary (delayed if the optimizer is in numpy C code). Fix: (1) `InProcessRunner.run_optimizer_in_process` stores `stop_event` on `optimizer._stop_event` before starting the solver thread. (2) `BasicOptimizer.minima_callback` checks `_stop_event` and returns `True` when set — scipy BH then exits its outer loop cleanly at the next inter-trial boundary (after current Nelder-Mead finishes). Ctypes KI injection retained as belt-and-suspenders fallback. Committed fb3ccc2. |
| May 2026 | **molass-legacy#64**: NS narrow prior bug for boundary-adjacent params. With the old `max/min` clamping (#63), params whose BH-optimal normalized value is near 0 (e.g. LKM R_1=0.046) got prior `[0, 1.046]` — BH at only 4% of the range. NS wasted ~96% of 150,000 evaluations far from the high-likelihood region; Phase 2 improved fv by only -0.018 in 54,000 evals vs. needing -0.261 more to match BH. Fix: symmetric `half_w = min(dist-to-lower, dist-to-upper, NARROW_BOUNDS_ALLOW)`, so BH result is always at 50% of the prior. R_1: 4% → 50%, k_MT_0: 32% → 50%, typical params: 50% → 50% (unchanged). Applies equally to upper-boundary params (e.g. near_upper: 95% → 50%). Committed f603bd2 in molass-legacy. |
| May 2026 | **molass-library#192**: CMA Terminate button hung at "Status: Terminating..." indefinitely. Root cause: `SolverCMA.minimize()` called `minima_callback` only when a new best was found (`if gen_best_fv < best_fv`). Once CMA converged, `minima_callback` was never called → `_stop_event` check (set by Terminate button) never fired → cooperative stop never happened → `_async_thread.is_alive()` stayed True → watch loop stuck. Ctypes KI injection (one-shot fallback) may fail if pycma holds GIL in C code. Fix: added `_stop_event` check at end of every CMA generation loop in `SolverCMA.minimize()`. Terminate now responds within one generation. Commit eedd366. |

| May 2026 | **molass-library#193**: `optimize_rigorously(method='CMA', in_process=True, async_=True)` crashed the Jupyter kernel on Windows/Python 3.14+ with STATUS_ACCESS_VIOLATION (0xC0000005). Root cause: IPython's ProactorEventLoop (IOCP) runs on the main thread after the cell returns; concurrently, the optimizer's daemon `_solve_thread` executes NumPy BLAS (releases GIL) → C-level race condition. CMA is pure Python — the crash is asyncio/BLAS/IOCP interaction, not CMA C extensions. Fix: auto-fallback to `in_process=False` (subprocess) in `make_rigorous_decomposition_impl` when `method in _ASYNC_CRASH_METHODS` and `in_process=True` and `async_=True`. This preserves the MplMonitor dashboard (vs. the `async_=False` fallback which would block the cell and lose the dashboard). UserWarning emitted referencing issue #193. Tests: `test_100_cma_async_fallback.py` (3/3 pass). Full investigation: `molass-researcher/experiments/21_rigorous_solvers/21c_cma_inprocess_repro.ipynb`. Issue closed. |
| May 2026 | **EDM/CEDM initial parameter unification**: `CedmEstimator.estimate_params()` was calling `guess_multiple_impl` only (rough estimate), which gave `b ≈ -4.0` for all components because `RobustEDM.guess_init_params` hardcodes `b = -4.0` as the lower-bound initializer. Fix: added `estimate_cedm_shared_params(x, y, xr_ccurves)` to `molass-library/molass/SEC/Models/EdmEstimatorImpl.py`. It runs `guess_multiple_impl` for Dz/cinj seeds, then calls `optimize_edm_xr_decomposition(shared_column=True)` via a minimal mock decomposition. The optimizer resets `b_init=0` and `e_init=0.5` analytically, producing physically varied `b` values per component. Updated `molass-legacy/molass_legacy/Estimators/CedmEstimator.py`: `_EghCurveAdapter` now exposes `.x` and `.y` (needed for peak-frame detection by the optimizer), and `estimate_params` calls `estimate_cedm_shared_params` directly. Validated: output matches library `upgrade(model='EDM')` exactly. |
| May 2026 | **molass-library#195: SDM lognormal `upgrade()` failure with `rgcurve`**. Two linked bugs caused 2D residual≈0.981 instead of ≈0.21. **Cause 1**: `estimate_sdm_lognormal_from_monopore` used the mono `k` (≈1.4 when `rgcurve` anchors the fit) for the shift test peak → wrong shift (+34 vs −18) → moment matching fails → all NNLS scales=0.01 → degenerate start. **Fix 1** (`SdmEstimator.py`): use `k_for_shift = 2.0` (matching the lognormal optimizer's default `k_init`). **Cause 2**: mono stage WITH `rgcurve` gives N=834, T=0.458 vs N=731, T=0.523 without → different NM landscape → bad local minimum even after fixing the shift. **Fix 2** (`SDM.py`): strip `rgcurve` at the top of `optimize_decomposition()` — confirmed by experiment (22e cell 10) that `rgcurve` has zero effect on SDM upgrade quality for both mono and lognormal (identical residuals with/without). `adjust_rg_and_poresize()` accepted `rgcurve` but never read it (dead parameter, now removed). After both fixes: upgrade() starts from same `ln_env` as direct call (N≈731, T≈0.523, t0≈-19, mu≈4.36, σ≈0.39); 2D residual 0.981 → 0.216 (direct call reference: 0.207). The ~0.01 difference is due to different local minima. |
| Jun 2026 | **molass-legacy G1300 init fix (SdmEstimator.py, commits 8ebd078→b487093)**: G1300 (SDM lognormal + gamma) BH initial parameter estimation was producing terrible init fv, so BH never escaped the bad region. Root-cause investigation across 17 analyses: (1) `N0=14400` from `exec_spec` was used instead of `50000` (fix: commit 8ebd078); (2) 3-stage library pipeline `_CurveProxy`/`_ProxyDecomposition` implemented to mirror `upgrade()` (commit 7f01291); (3) `_CurveProxy.get_max_y()` missing (fix: commit 60811d8); (4) **critical**: library `LognormalEnv.T` ≠ legacy `K` — legacy stores `K = N×T` (confirmed via `DispersiveMonopore.py`: `T_ = K_/N_`), so T_lib=0.497 was placed at K position (expected ~387) → fv=+13018.9 (fix: `K_lib = N_lib * T_lib`, commit b487093); (5) `poresize_bounds` not passed to `estimate_sdm_column_params`, using default (70,300) instead of column-specific (71,81) Å from `get_setting("poresize_bounds")` (fix: same commit). **Result**: analysis-017 init fv=-0.760 (SV=51.6) vs broken +13018.9 vs fallback +1.17. Reference optimized fv=-1.049 (SV=65.7). The init is now firmly within the optimization basin. **Key rule**: in molass-legacy G1300, `K` is always `N×T`; never place the library's `T` directly at the K position. |
| Jun 2026 | **molass-legacy G1300 sigma fix (SdmEstimator.py, commit b5396d4)**: The stage-3 moment-matching `sigma_lib` was unreliable (e.g. 0.496 for 2-comp SAMPLE1 while the library optimizer runs with `ln_pore_sigma=0.3` fixed). Fix: always use `_SIGMA_FIXED = 0.3` in `sdmcol_8` — consistent with `optimize_sdm_lognormal_xr_decomposition` default. Comparison in `22e_sample1_sdm_comparison.ipynb` showed upgrade() (which also uses 0.3) fell into a bad local minimum (pore≈33 Å vs stage-3 pore≈70 Å); stage-3 moment-matching is the better init for G1300, not equivalent to upgrade(). |
| Jun 2026 | **molass-legacy G1300 Stage 4 addition (SdmEstimator.py)**: Legacy `_estimate_lognormal` was stopping after Stage 3 (moment matching, init fv≈-0.76, SV≈52) while the library notebook runs Stage 4 (`optimize_sdm_lognormal_xr_decomposition`) which reaches SV≈72 before BH. The old comment "stage 3 is sufficient" was wrong — Stage 4 is exactly what `upgrade()` does and gives a much better BH starting point. Fix: added Stage 4 call after Stage 3 in `_estimate_lognormal`; extract `column.get_params()` from `ln_ccurves[0]` → build `sdmcol_8` from Stage-4 params (N, K=N*T, x0, mu, sigma=0.3, N0, tI, k); also update `xr_w` (positions 0..nc-1) from Stage-4 `cc.scale` values. Fallback `xr_scales=None` keeps exception path unchanged. Verified: analysis-005 init SV 51.6 → 64.3, best accepted SV 71.1 (not accepted!) → 81.34 ✅. |
| Jun 2026 | **molass-legacy G1200 init unification (SdmEstimator.py)**: `_estimate_mono` (G1200, SDM mono-pore) was using legacy `guess_params_using_moments` (moment-matching) as init, while library `upgrade(model='SDM')` uses a 2-stage pipeline: `estimate_sdm_column_params` → `optimize_sdm_xr_decomposition`. Fix: rewrote `_estimate_mono` to mirror the same 2-stage pattern as `_estimate_lognormal`, using the existing `_ProxyDecomposition` adapter. Maps library result `(N, T, ..., x0, tI, N0, poresize, timescale, k)` → legacy G1200 `[N, K=N*T, x0, poresize, N0, tI, k_gamma]`. Also updates XR weights from Stage-2 `cc.scale` values. Fallback to legacy `guess_params_using_moments` result (k_gamma=2.0) on library import failure. |
| Jun 2026 | **molass-legacy EDM estimator unification (EdmEstimator.py, EghEstimator.py, CedmEstimator.py)**: `EdmEstimator.estimate_params` (non-CEDM EDM model) was calling legacy `EDM.guess_multiple_impl(x, y, num_peaks)` which redundantly re-ran `recognize_peaks` even though EGH params were already computed by `estimate_egh_params()`. Fix: `EdmEstimator.estimate_params` now builds `_EghCurveAdapter` objects from the already-computed `init_xr_params` and calls the library's `EdmEstimatorImpl.guess_multiple_impl(x, y, adapters)` instead. Fallback to legacy path on import failure. To share `_EghCurveAdapter`: moved it from `CedmEstimator.py` to `EghEstimator.py` (parent class of both); `CedmEstimator.py` now imports it via `from .EghEstimator import EghEstimator, _EghCurveAdapter`. Sharing status: EDM/CEDM fully unified for init estimation. |
| Jun 2026 | **molass-legacy#77 / molass-library#78 — eliminate rg_curve_parent/, unify to rg-curve/ (Jun 10 2026)**: The `rg_curve_parent/` folder was introduced as a workaround for a broken trimming check (bug #76). After fixing #76, the folder was no longer necessary. Key insight: the trimming check has exactly one legitimate use — cross-session loading (Result Viewer/Resume loading rg-curve from a different analysis folder with different trim boundaries). Within the same session, trimming is always consistent. Fix: eliminated `rg_curve_parent/`; both `prepare_rigorous_folders()` (notebook path) and `BackRunner.run()` (GUI path) now write directly to `rg-curve/`. Trimming mismatch → `warnings.warn` + `rg_curve=None` (no silent recomputation). `trust_rg_curve_folder` SerialSettings key removed. | `bridge_recognize_peaks` in `molass-library/molass/Peaks/RecognizerSpecific.py` was the last library-side caller of legacy `recognize_peaks` (from `molass_legacy.QuickAnalysis.ModeledPeaks`). Replaced with `EghPeeler.egh_peel` — the library-native implementation already used by `CurveDecomposer.py`. Interface is compatible: both return `(H, mu/m, sigma, tau)` tuples; index conversion `int(round(mu - x[0]))` is identical. Test: `tests/generic/030_Peaks/test_010_Peaks.py::test_010_Kosugi3a` (uses `curve.get_peaks(num_peaks=2)` → `Recognizer` → `bridge_recognize_peaks`) — 1 passed. All Level-A migration items (estimators + peak recognition) are now unified. |

| Jun 2026 | **molass-library#212**: AI-friendliness: `SecSaxsData.recommend_decomposition_options()` — auto-detects peak count and separation via `xr.detect_peaks(return_properties=True)`; returns `{'num_components': n, 'xr_peakpositions': peaks}` for well-separated peaks (separation = min(prominences)/max(peak_heights) ≥ `overlap_threshold=0.3`) or `{'num_components': n, 'proportions': [1]*n}` for overlapping ones; fallback `{'num_components': 2, 'proportions': [1, 1]}` when no peaks found. `SecSaxsData.recommend_decomposition(**kwargs)` is a convenience wrapper that calls the above then `quick_decomposition(**opts)`, with kwargs as overrides. This is the library equivalent of the legacy dialog's "Automatic" peak recognition option. Tests: `test_23`–`test_26` in `tests/generic/010_DataObjects/test_010_SSD.py`. Issue closed. |

| Jun 2026 | **Recommend.py: EGH peeling replaces detect_peaks** — `detect_peaks(prominence=0.005)` returned 12 components for SAMPLE2 (noise oscillations above 0.5% prominence). Replaced with `_count_components_by_egh_peeling()` using `EghPeeler.egh_peel` + cluster-merge. Algorithm: group consecutive EGH peaks where `spacing/sigma_sum < egh_overlap_threshold=1.3` into one component. Key calibration: SAMPLE3 pair (156→194) ratio=1.232; SAMPLE1 min=1.376; SAMPLE2 min=1.423 → safe threshold window (1.232, 1.376). Results: SAMPLE1=3, SAMPLE2=3, SAMPLE3=1, SAMPLE4=2. The `SecSaxsData.recommend_decomposition_options()` method updated to use `egh_overlap_threshold=1.3` (dropped old `overlap_threshold`/`min_prominence` params). Tests test_23–26 pass. |

**Principle**: *Never leave this codebase harder to navigate than you found it. Update this file after each work session with new findings.*

---

**License**: GNU General Public License v3.0 — Part of molass-library
