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

**Parent vs subprocess architecture**: `optimize_rigorously()` builds the optimizer object in the parent process, then launches an independent subprocess via `BackRunner` + `subprocess.Popen`. The subprocess receives only serialized data (init_params.txt, bounds.txt, restrict.txt, etc.) — it reconstructs its own optimizer from disk. Therefore:
- Parent-side `optimizer.objective_func(params)` and subprocess evaluations use the same code but independent instances
- The parent optimizer is used post-hoc by `get_score_breakdown()`, `plot_objective_func()`, and `load_best_rigorous_result()` to replay results
- Key files: `molass_legacy/Optimizer/BackRunner.py` (subprocess launch), `molass_legacy/Optimizer/MplMonitor.py` (parent-side monitoring)

**callback.txt format**: Each optimizer evaluation appends a multi-line entry:
```
t=<timestamp>
x=
[param_0 param_1 ... param_n]    ← may span multiple lines for long arrays
f=<fv_value>
a=<True|False>                   ← accepted by optimizer
c=<evaluation_count>
```
Parse `f=` lines with: `re.finditer(r'^f=([\-\d.eE+]+)', content, re.MULTILINE)`

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

See [NOTEBOOK_CONVENTIONS.md v0.1.0](https://github.com/freesemt/ai-context-standard/blob/main/NOTEBOOK_CONVENTIONS.md)  
Kernel preference: global Python (`py`). Do not create venvs.

---

## 🔄 Updates (AI-Readiness Trail)

| Date | What was learned / added |
|------|--------------------------|
| Feb 19, 2026 | Initial file created — first visit (architecture survey) |
| Feb 19, 2026 | P1+ diagnosis: traced full decomposition call chain (default vs proportions paths); identified root cause of overlap failure (greedy `recognize_peaks` + single Nelder-Mead); confirmed `proportions` option as effective workaround (std≤0.02 vs 0.27, robust to 3:1 mismatch); improved `quick_decomposition()` docstring and tutorial pages |
| Feb 19, 2026 | AI-readability pass: added inline comments at `recognize_peaks` import and call site in `CurveDecomposer.py` (algorithm summary, failure mode, cross-repo pointer); noted `randomize`/`global_opt` as unused fix levers in this file; created entry point for AI navigating `recognize_peaks` and other legacy code |
| Mar 24, 2026 | Migrated to `.github/copilot-instructions.md` (AI Context Standard v0.7) |
| Mar 25, 2026 | Updated to AI Context Standard v0.8; added `init.prompt.md` and `vscode-version.txt`; refreshed ecosystem table |

**Principle**: *Never leave this codebase harder to navigate than you found it. Update this file after each work session with new findings.*

---

**License**: GNU General Public License v3.0 — Part of molass-library
