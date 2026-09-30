# molass — AI assistant context

This file ships **inside the installed package** (`pip install molass`), so it
is current for whatever version you have — unlike a repo's own
`.github/copilot-instructions.md` or issue history, which assume a git
checkout of the source repository.

Find this file's absolute path at runtime: `python -c "import molass; print(molass.context_path())"`
(or `molass.print_context()` to dump it directly).

If you're developing `molass-library`/`molass-legacy` themselves (not just
using the package), see `.github/copilot-instructions.md` and `PROJECT_STATUS.md`
in the source repository instead — those cover testing conventions, the
multi-repo research workspace, and dated investigation history that don't
belong here.

---

## What molass does

Molass decomposes SEC-SAXS data: the measured 2D matrix $M$ (q-values ×
elution frames) is factored into scattering profiles $P$ and elution curves
$C$ via $M \approx PC$.

```
Raw data folder / molass_data sample
        ↓
   SecSaxsData (DataObjects/)          ← Load, trim, correct
        ↓
   quick_decomposition()               ← Low-rank factorization (LRF)
        ↓
   Decomposition object (LowRank/)     ← Holds xr_ccurves, uv_ccurves, components
        ↓
   optimize_rigorously()               ← (Optional) Physics-constrained refinement
        ↓
   Reports / DENSS                     ← Output
```

### Key packages

| Package | Role |
|---------|------|
| `DataObjects/` | Core data containers: `SecSaxsData`, `XrData`, `UvData`, `SsMatrixData`, `Curve` |
| `LowRank/` | Matrix factorization engine: `Decomposition`, `CurveDecomposer`, `CoupledAdjuster` |
| `Rigorous/` | Physics-constrained optimization (EGH/SDM/EDM/LKM/GRM models + Rg-consistency); bridges to `molass-legacy` |
| `SEC/Models/` | Column elution models: `EDM.py`, `SDM.py`, `Simple.py` (+ Gaussian, lognormal pore distributions) |
| `Guinier/` | Rg estimation: `RgEstimator`, `RgCurve`, `RgCurveUtils` |
| `Peaks/` | Peak recognition: `Recognizer`, `PeakSimilarity` |
| `Mapping/` | XR/UV frame-axis correspondence and affine mapping estimation |
| `Trimming/` | Data trimming (`trimmed_copy()`, `make_trimming()`) |
| `Baseline/` | Baseline correction |
| `Global/` | Global optimization options (`Options.py`) |
| `SAXS/` | DENSS integration, MRC viewer |

### Important relationships

- **`molass-legacy`** is a required runtime dependency. `Rigorous/` bridges to
  it heavily (`LegacyBridgeUtils.py`) for the physics-constrained optimizer —
  don't assume all optimization logic lives in `molass-library`.
- **`molass_data`** is a separate package providing sample datasets
  (`SAMPLE1`–`SAMPLE5`) for tutorials/experimentation.
- **Dual-channel design**: `SecSaxsData` carries both XR (X-ray scattering)
  and UV (absorbance) data. Many methods have `xr_only` variants. The two
  channels can have different extinction ratios per component — don't assume
  peak prominence is comparable across channels (see Mapping note below).
- **EDM `e` parameter**: in `molass_legacy/SecTheory/Edm.py`, `e` (default 0.4)
  is $V_0/(V_0+V_p)$ — the mobile-phase fraction of the *accessible* volume
  only; solid bead volume is entirely outside the EDM mass balance. This is
  **not** the standard chromatographic total porosity
  $\varepsilon_T=(V_0+V_p)/V_\text{column}$. The phase ratio
  $F=(1-e)/e = V_p/V_0$ directly. The Henry coefficient
  $a = K_\text{SEC} \times (V_p/V_0)$; default $a=1.5$ requires $V_p/V_0 \geq 1.5$.

### Canonical usage

```python
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD

ssd = SSD(SAMPLE1)                        # Load raw data
trimmed = ssd.trimmed_copy()              # Trim to SEC peak region
corrected = trimmed.corrected_copy()      # Baseline correction
decomposition = corrected.quick_decomposition()   # Low-rank factorization
decomposition.plot_components()           # Inspect result
```

Rigorous refinement (optional, bridges to `molass-legacy`):
```python
rgcurve = corrected.get_rg_curve()        # cache once (see below)
decomp = corrected.quick_decomposition(rgcurve=rgcurve)
run_info = decomp.optimize_rigorously(rgcurve=rgcurve, analysis_folder="temp_analysis")
```

---

## Working conventions worth knowing

### Overlapping peaks: prefer `proportions=` over the default

`quick_decomposition()`'s default peak initialization (`recognize_peaks`,
greedy sequential subtraction) degrades when components overlap heavily,
producing high-variance results. If components visibly overlap, pass
`proportions=[...]` (relative area weights, e.g. `[1, 1, 1]` or `[3, 2, 5]`)
to use cumulative-area slicing instead — much more robust to overlap. Values
are normalized internally, so `[1,1]`, `[0.5,0.5]`, `[3,3]` are equivalent.

### Expensive-object caching: `get_<noun>()`

When a method produces an expensive computed object (e.g. `RgCurve`), the
convention is a `get_`-prefixed accessor that computes once and caches:

```python
rgcurve = corrected.get_rg_curve()                        # cached on `corrected`
decomp  = corrected.quick_decomposition(rgcurve=rgcurve)   # injected -> cached in decomp
run_a   = decomp.optimize_rigorously(rgcurve=rgcurve, ...)
run_b   = decomp.optimize_rigorously(rgcurve=rgcurve, ...)  # no recomputation
```
`get_` means "cached, safe to call repeatedly"; `compute_` (where it exists)
means "always runs fresh."

### Trimming and the XR/UV mapping

`trimmed_copy()` auto-aligns the XR and UV frame ranges using an estimated
affine mapping (`mapped_trimming=True` by default). If it emits:

> `UserWarning: XR and UV cover very different frame ranges after trimming...`

the two channels ended up with mismatched coverage — this can inflate
`UV_LRF_residual`/`UV_2D_fitting` scores during `optimize_rigorously()` by
comparing the model against frames where UV was never really measured. Use
`ssd.make_trimming(debug=True)` to see the raw peaks, the peak-matching
decision, and the chosen slices for both channels; pass an explicit
`mapping=` to `trimmed_copy()` if the auto-estimated one looks wrong.

### `Decomposition.score()` / `RunInfo.score()`: check `.source`

Both return a `Score` object with `.sv`, `.fv`, `.breakdown`, `.plot()`,
`.diagnose()`, `.print_summary()`. They are **not** interchangeable:
`decomp.score()` evaluates whatever parameters `decomp` currently holds
(typically pre-optimization); `run_info.score()` evaluates the best
parameters an `optimize_rigorously()` run has found so far. Check
`score.source` (`'decomp'` or `'rigorous'`) if it's ambiguous which one
produced a given result — `print_summary()`/`repr()` show it too. The
parameter vector is `score.params` (`.init_params` is a deprecated alias —
it isn't always the *initial* guess). For a plain, storable/loggable result
with no live optimizer reference, use `score.snapshot()`.

Each call to `score()`/`optimize_rigorously()` reloads the model's
optimizer module from disk — edits to `molass-legacy`'s
`Optimizer/BasicOptimizer.py` or `ObjectiveFunctions/*.py` take effect on the
*next* call with no process restart needed, but this also means repeated
calls aren't cheap (each one re-imports and re-executes those modules).

### Rigorous optimization: Score Value (SV)

The optimizer's raw objective `fv` (lower is better) is converted to a 0–100
scale for display: `SV = -200 / (1 + exp(-1.5 * fv)) + 100`. Rough
thresholds: **≥80 good**, **60–80 fair**, **<60 poor**. Use
`run_info.diagnose()` to map a score breakdown to physical interpretations
(e.g. "UV_LRF_residual near zero → failing UV low-rank fit") rather than
guessing from the numbers alone.

For an in-flight or completed run, prefer the single-call `run_info.live_status()`
over reading `callback.txt`/manifests by hand — it returns
`{phase, n_evals, best_fv, best_sv, elapsed_s, analysis_folder, work_folder,
subprocess_pid, subprocess_returncode, manifest}` in one disk read.
`run_info.get_current_curves()` returns the same data/model curves shown on
the live monitor dashboard as a plain dict, for numeric comparison against
what's visually displayed.

`optimize_rigorously()` defaults to `in_process=True` (runs in the calling
process; used by notebook/library workflows). `in_process=False` spawns a
subprocess with its own independent data-derivation pipeline (used by the
legacy GUI) — the two paths can diverge if you're comparing results across
them.

---

## Where to find more

- Tutorial (usage-oriented): https://biosaxs-dev.github.io/molass-tutorial/
- Essence (theory): https://biosaxs-dev.github.io/molass-essence/
- Technical report (algorithms/implementation): https://biosaxs-dev.github.io/molass-technical/
- Source / issues: https://github.com/biosaxs-dev/molass-library
