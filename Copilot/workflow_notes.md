# molass-library Workflow Notes

Notes for AI assistants (Copilot, etc.) working in this repository across multiple sessions and machines.

## Terminal tips (VS Code, Windows PowerShell only)
- `cd repo; git ...` — the tool may strip `cd` in PowerShell, running git in the wrong dir. Use `Push-Location repo; git ...` instead. (Not an issue in bash/zsh.)
- Multi-line `gh issue create --body "..."` fails in PowerShell due to special chars. Use:
  ```powershell
  $body = @"
  ...body text...
  "@
  $body | gh issue create --title "..." --label "enhancement" --body-file -
  ```
  In bash, use a heredoc: `gh issue create ... --body-file - <<'EOF'` ... `EOF`

## GitHub Issues
- Always use `gh` CLI to create issues — do NOT attempt browser-based approaches
- Repo: biosaxs-dev/molass-library

## Issue titling policy

Use the correct prefix to categorize issues:

- **`AI-friendliness:`** — API is confusing specifically for an AI (or any caller without deep context): wrong arg order, silent failures, missing defaults, opaque names. Examples: #47, #49, #28.
- **`Design:`** — workflow/philosophy issues: separation of concerns, consistency with existing patterns, architectural decisions. Example: #50.
- **`Enhancement:`** / **`Bug:`** — standard feature additions and bug fixes.

Do NOT label design or philosophy issues as AI-friendliness.

## AI-friendliness improvement series
When fixing AI-friendliness issues, follow this pattern per issue:
1. **Open a GitHub issue FIRST**: `gh issue create --title "AI-friendliness: ..." --label "enhancement"`
2. Implement the fix in molass-library source
3. Add a test in `tests/generic/010_DataObjects/test_010_SSD.py` (or relevant test file)
4. Run `python -m pytest <test_file> -v --tb=short --no-header -q` to verify
5. Close the issue: `gh issue close <N> --comment "Fix implemented and tested."`

### Issues completed (all closed)
- #8: `get_rgs()` returns `None` silently → `nan`
- #9: `plot_components()` not axis-injectable
- #10: No q-grid alignment utility
- #11: No component reliability indicator
- #12: Missing shape/unit docstrings
- #13: `ComponentCurve.y`, `trimmed_copy(nsigmas=)`, auto-mapping (v0.8.4)
- #14: `SecSaxsData` non-standard data support
- #15: Added `uv.wavelengths` and `uv.frames` aliases to `UvData`
- #23: `get_baseline2d()` printed `recognize_num_peaks`/`peak_width=` to stdout → suppressed with `redirect_stdout(io.StringIO())`
- #24: `'buffit'` baseline method — buffer-frame polyfit with Otsu adaptive threshold
- #25: Replaced fixed `BUFFIT_THRESHOLD=0.10` with Otsu adaptive threshold in `BuffitBaseline.py`
- #26: Made `'buffit'` default (v0.8.4) — **later reverted to `'linear'`** (actual default in code is `'linear'`)
- #27: Add `molass.requires(version)` helper for version guard in notebooks/tests (v0.8.4)
- #28: `SsMatrixData.q_values` / `.frame_indices` property aliases for opaque `iv` / `jv` (with setter)
- #29: `SsMatrixData.get_bpo_ideal()` — single-call dataset-relative ideal positive_ratio
- #30: `compute_lpm_baseline()` `mask` parameter for frame exclusion
- #31: Wire `xr_peakpositions` into `quick_decomposition()` API + bug fixes
- #32: `ComponentCurve` docstring Rg breadcrumb
- #33: `Decomposition.xr_components` / `uv_components` property aliases
- #34: `quick_decomposition()` docstring: documented `xr_peakpositions`, `tau_limit`, `max_sigma`, `min_sigma`, `debug`
- #35: `XrData.detect_peaks()` — savgol+find_peaks, returns frame positions
- #38: SNR-weighted `get_positive_ratio()`, `get_bpo_ideal()`, `get_snr_weights()` — default `weighting='snr'`
- #39: `evaluate_baseline(baseline)` → `BaselineEvaluation(positive_ratio, ideal, delta)` namedtuple
- #40: `get_ideal_positive_ratio()` alias for opaque `get_bpo_ideal()`
- #41: `get_recognition_curve()` + `elution_recognition` global option (`'icurve'`/`'sum'`)
- #46: `get_baseline2d(endpoint_fraction=...)` — opt-in endpoint-anchored LPM for negative-peak datasets (v0.8.7)
- #47: `E` optional (`E=None`) in `SsMatrixData`, `XrData`, `UvData` constructors (v0.8.7)
- #48: `corrected_copy()` forwards `**baseline_kwargs` to `get_baseline2d()` (v0.8.7)
- #49: Reorder constructor args to `(M, iv, jv, E=None)` — data matrix first (breaking change, v0.8.7)

### Issues pending (filed, not yet implemented)
- #50: Design: `allow_negative_peaks` as stored object state — separate baseline recognition from `corrected_copy`
