# API Improvement Proposals

**Source**: Friction points identified during AI-assisted research in `molass-researcher` (Experiment 01, March 6, 2026)  
**Context**: Running MOLASS on 6 SEC-SAXS datasets in a Jupyter notebook workflow, comparing original vs pre-averaged data. The issues below caused code failures or workarounds during that work.

---

## 1. `get_rgs()` should not return `None` silently

**Current behaviour**: When Guinier fitting fails for a component (e.g. because the component is a noise artifact from forced `num_components`), `get_rgs()` returns `None` in the list for that position.

**Problem**: This silently breaks all downstream numeric code. Example crash:
```python
for rg in decomp.get_rgs():
    print(f"Rg = {rg:.2f} Å")   # TypeError if rg is None
```
The failure mode is a `TypeError` at the format string, with no contextual message about which component failed or why.

**Recommendations** (in order of preference):
- Return `float('nan')` instead of `None` — composable with numpy math, and `math.isnan(rg)` is an explicit guard
- OR raise a named exception with context: `GuinierFailedError(component=2, reason="not enough valid data points")`
- OR add a companion `get_rg_flags()` → `["ok", "failed", "failed"]` so callers can inspect quality without try/except

**Workaround used**:
```python
rg_str = f"{rg:.2f}" if rg is not None else "N/A (Guinier failed)"
```

---

## 2. `plot_components()` is not axis-injectable

**Current behaviour**: `plot_components()` always creates its own `plt.figure()` internally. Calling `plt.sca(ax)` before it has no effect.

**Problem**: Cannot be embedded in a subplot grid. Any attempt to build a multi-panel figure with `plt.subplots()` and then call `plot_components()` into a specific axis silently produces a separate floating figure (and a blank subplot).

**Recommendation**: Add optional `fig=None` / `axes=None` parameters following the standard matplotlib convention:
```python
def plot_components(self, title=None, fig=None, axes=None):
    if fig is None:
        fig, axes = plt.subplots(...)
    # draw into provided axes
```

**Workaround used**: Called `plot_components()` standalone for each dataset and saved each figure individually, rather than composing a comparison grid.

---

## 3. No q-grid alignment utility

**Current behaviour**: `get_xr_matrices()` returns `P` with shape `(n_q, n_components)`, where `n_q` differs between datasets because trimming leaves different numbers of q-points. There is no built-in way to compare P(q) profiles across datasets.

**Problem**: `scipy.stats.pearsonr(P_a, P_b)` raises a `ValueError` when the arrays have different lengths (e.g. 966 vs 963 points). This is a routine need whenever comparing two decompositions.

**Recommendation**: Add a utility to project a scattering profile onto a target q-grid:
```python
decomp.P_at(q_target)   # interpolated P(q) array at given q values
# or
molass.align_decompositions(decomp_a, decomp_b)  # returns both P arrays on common grid
```

**Workaround used**:
```python
q_common = np.linspace(max(q_a[0], q_b[0]), min(q_a[-1], q_b[-1]), 500)
P_a_interp = np.interp(q_common, q_a, P_a[:, 0])
P_b_interp = np.interp(q_common, q_b, P_b[:, 0])
r, _ = pearsonr(P_a_interp, P_b_interp)
```

---

## 4. No component reliability indicator for forced decompositions

**Current behaviour**: `quick_decomposition(num_components=N)` forces exactly N components regardless of data quality. There is no returned quality metric to distinguish real from spurious components.

**Problem**: When `num_components` is forced higher than the data supports, the extra components are noise artifacts. There is currently no programmatic way to detect this — the only signal is `get_rgs()` returning `None` (see issue 1), but even then, components with a valid Guinier fit may still be physically spurious.

**Recommendation**: Add a per-component reliability flag or score:
```python
decomp.is_component_reliable(i)   # bool
decomp.component_quality_scores() # list of floats, e.g. SNR or residual fraction
```

**Workaround used**: Manual inspection of Rg values — if all components have similar Rg (e.g. all ≈ 32 Å) the decomposition is flagged as physically implausible.

---

## 5. Return shape documentation is missing

**Current behaviour**: The docstrings for `get_xr_matrices()`, `get_xr_components()`, `get_rgs()`, `get_proportions()` do not document array shapes or units.

**Problem**: Key facts like "P has shape `(n_q, n_components)`", "C has shape `(n_components, n_frames)`", "Rg is in Ångströms" had to be discovered by inspection or trial and error during AI-assisted work. An AI assistant cannot inspect objects interactively the way a human at a REPL can, so missing docstrings have a higher cost in agentic workflows than in human-only workflows.

**Recommendation**: Add numpy-doc style docstrings with explicit shape annotations:
```python
def get_xr_matrices(self):
    """
    Returns
    -------
    M : ndarray, shape (n_q, n_frames)
        Measured scattering matrix.
    C : ndarray, shape (n_components, n_frames)
        Elution curves per component.
    P : ndarray, shape (n_q, n_components)
        Scattering profiles per component (columns).
    Pe : ndarray, shape (n_q, n_components)
        Estimated errors on P.
    """
```

---

## Summary

| # | Issue | Severity | Fix complexity |
|---|-------|----------|----------------|
| 1 | `get_rgs()` returns `None` silently | High — causes runtime crashes | Low |
| 2 | `plot_components()` not axis-injectable | Medium — forces awkward workflow | Medium |
| 3 | No q-grid alignment utility | Medium — common need, manual workaround | Low |
| 4 | No component reliability indicator | Medium — forced decompositions produce silent garbage | Medium |
| 5 | Missing shape/unit docstrings | Low (human) / High (AI-assisted) — slow to discover | Low |

---

## Follow-through After Implementation

Once the fixes above are implemented:

1. **Bump version** (0.8.2 → 0.8.3 or appropriate) before releasing, so that downstream experiment notebooks can record which molass version produced each result. This is important for reproducibility — `molass-researcher` experiment logs reference molass by version.

---

## GitHub Issue Status

**Last verified**: March 11, 2026

| # | GitHub Issue | Title | Status |
|---|-------------|-------|--------|
| — | [#15](https://github.com/biosaxs-dev/molass-library/issues/15) | Add `wavelengths` and `frames` aliases to `UvData` | ✅ Done (closed) |
| 1 | [#8](https://github.com/biosaxs-dev/molass-library/issues/8) | `get_rgs()` returns `None` silently | ✅ Done (closed) |
| 2 | [#9](https://github.com/biosaxs-dev/molass-library/issues/9) | `plot_components()` not axis-injectable | ✅ Done (closed) |
| 3 | [#10](https://github.com/biosaxs-dev/molass-library/issues/10) | No q-grid alignment utility | ✅ Done (closed) |
| 4 | [#11](https://github.com/biosaxs-dev/molass-library/issues/11) | No component reliability indicator | ✅ Done (closed) |
| 5 | [#12](https://github.com/biosaxs-dev/molass-library/issues/12) | Missing shape/unit docstrings | ✅ Done (closed) |
| — | [#13](https://github.com/biosaxs-dev/molass-library/issues/13) | ComponentCurve.y, trimmed_copy(nsigmas=), auto-mapping (v0.8.4) | ✅ Done (closed) |
| — | [#14](https://github.com/biosaxs-dev/molass-library/issues/14) | SecSaxsData non-standard data support | ✅ Done (closed) |

### Newly filed (March 10, 2026)

Discovered during Experiment 01f (March 9, 2026):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#16](https://github.com/biosaxs-dev/molass-library/issues/16) | `.data` alias for `.M` in `SsMatrixData` | ✅ Done (closed) |
| [#17](https://github.com/biosaxs-dev/molass-library/issues/17) | Informative `__repr__` for `SsMatrixData` and `UvData` | ✅ Done (closed) |
| [#18](https://github.com/biosaxs-dev/molass-library/issues/18) | Document `simple_plot_3d` ax parameter and caller responsibilities | ✅ Done (closed) |
| [#19](https://github.com/biosaxs-dev/molass-library/issues/19) | Add `uv.wavelength_range` property to `UvData` | ✅ Done (closed) |
| [#20](https://github.com/biosaxs-dev/molass-library/issues/20) | Add `decomp.get_rg_curve()` to `Decomposition` (returns `RgCurve`) | ✅ Done (closed) |

### Newly filed (March 11, 2026)

Discovered during Experiment 01g (March 2026):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#21](https://github.com/biosaxs-dev/molass-library/issues/21) | `RgCurve.x` should carry original frame numbers, not column indices | ✅ Done (closed) |
| [#22](https://github.com/biosaxs-dev/molass-library/issues/22) | `RgCurve.y` should be float array with `nan`, not object array with `None` | ✅ Done (closed) |

### Newly filed (April 23, 2026)

Discovered during Experiment 13h (rigorous optimization, UltraNest):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#123](https://github.com/biosaxs-dev/molass-library/issues/123) | Add `RunInfo.check_progress()` for mid-run progress monitoring | ✅ Done (closed) |

2. **Simplify `molass-researcher` 01c workarounds** — the notebook `experiments/01_shimizu_averaging/01c_comparison_analysis.ipynb` previously contained manual workarounds for issues #1 and #3. Now that fixes are in place, consider revisiting `01c` to replace workarounds with the cleaner API calls. This is optional (the workarounds work), but it keeps the research notebook idiomatic.
