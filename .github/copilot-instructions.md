<!-- AI Context Standard v0.8.9 - Adopted: 2026-04-02 -->
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

### 8. Version Convention

- Check `pyproject.toml` for current version (e.g., `0.8.2`)
- `molass/__init__.py::get_version()` reads from `pyproject.toml` during local development, falls back to `importlib.metadata` for installed package
- Use `get_version(toml_only=True)` in development to avoid confusion between local and installed versions

### 9. Rigorous Optimization Internals (Issue #107)

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

Read [NOTEBOOK_CONVENTIONS.md v0.2.5](https://github.com/freesemt/ai-context-standard/blob/main/NOTEBOOK_CONVENTIONS.md) before working with any notebook in this repo.  
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

**Principle**: *Never leave this codebase harder to navigate than you found it. Update this file after each work session with new findings.*

---

**License**: GNU General Public License v3.0 — Part of molass-library
