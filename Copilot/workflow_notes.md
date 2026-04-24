# molass-library Workflow Notes

Notes for AI assistants (Copilot, etc.) working in this repository across multiple sessions and machines.

## Terminal tips (VS Code, Windows PowerShell only)

### Multi-repo `git` invocations
Use `git -C <path> ...` instead of `cd <path>; git ...`. The terminal tool may silently strip `cd` from chained commands in PowerShell, running `git` against the wrong repo. (Not an issue in bash/zsh.)

```powershell
# ❌ Unreliable
cd c:\Users\takahashi\GitHub\molass-library; git log -1
# ✅ Reliable
git -C c:\Users\takahashi\GitHub\molass-library log -1
```

### Multi-line `gh issue create` (preferred: temp-file pattern)
Writing the body to a temp file and passing `--body-file <path>` avoids both (a) PowerShell quoting issues and (b) the VS Code terminal tool's "may be waiting for input" misfire that triggers on stdin pipes.

```powershell
$body = @'
...markdown body...
'@
Set-Content -Path "$env:TEMP\issue.md" -Value $body -Encoding UTF8
gh -R biosaxs-dev/molass-library issue create --title "..." --label "enhancement" --body-file "$env:TEMP\issue.md"
```

Stdin-pipe form (`$body | gh ... --body-file -`) also works but trips the false-input warning on every call.
In bash, a heredoc is fine: `gh issue create ... --body-file - <<'EOF'` ... `EOF`.

### NEVER use PowerShell text ops on non-ASCII files (CRITICAL)
`Get-Content` / `.Replace()` / `WriteAllText()` / `Set-Content` (without explicit `-Encoding UTF8`) default to **cp932 (Shift-JIS) on Japanese Windows**. They silently garble UTF-8 multi-byte characters (–, Δ, Å, →, ×, etc.) and **destructively consume adjacent ASCII bytes** — making automated reversal impossible.

Safe alternatives:
- `replace_string_in_file` tool (VS Code's native edit tool)
- Python `json` module for `.ipynb` files (explicitly reads/writes UTF-8)
- `Set-Content -Encoding UTF8` when writing — never read-modify-write text files via PS

## GitHub Issues
- Always use `gh` CLI to create issues — do NOT attempt browser-based approaches
- **Always pass `-R biosaxs-dev/molass-library`** explicitly. `gh` auto-detects the repo from cwd, but in a multi-root workspace cwd is unreliable; explicit `-R` removes the ambiguity. (Same applies for other repos in the workspace — use `-R <owner>/<repo>` always.)
- Repo: biosaxs-dev/molass-library

## Issue titling policy

Use the correct prefix to categorize issues:

- **`AI-friendliness:`** — anything that makes the *working environment* harder to use without deep context. This includes Python APIs (wrong arg order, silent failures, opaque names) AND tools/extensions/conventions (missing tools, undiscoverable capabilities, broken workflows). Examples: #47, #49, #28; ai-context-vscode missing `canBeReferencedInPrompt`.
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
- #126: AI-friendliness: add `best_fv`/`best_sv` to `mplmonitor_latest.json` — implemented in molass-legacy `MplMonitor._build_monitor_snapshot_json()`
- #127: AI-friendliness: write `run_complete.json` on optimizer job completion — implemented in molass-legacy `MplMonitor._write_run_complete_json()` + molass-library `RunInfo.run_complete_path` / `load_run_complete()`
- #128: AI-friendliness: widget title should show best accepted SV, not current snapshot SV — implemented in molass-legacy `JobStatePlot.plot_objective_func()` (add `best_sv` kwarg, update title to `"best SV=XX.X  (cur=YY.Y)"`) + `MplMonitor.update_plot()` (compute `best_sv` from `job_state.fv` and pass through)
