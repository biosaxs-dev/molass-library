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

## AI-friendliness improvement series
When fixing AI-friendliness issues, follow this pattern per issue:
1. **Open a GitHub issue FIRST**: `gh issue create --title "AI-friendliness: ..." --label "enhancement"`
2. Implement the fix in molass-library source
3. Add a test in `tests/generic/010_DataObjects/test_010_SSD.py` (or relevant test file)
4. Run `python -m pytest <test_file> -v --tb=short --no-header -q` to verify
5. Close the issue: `gh issue close <N> --comment "Fix implemented and tested."`

### Issues completed (all closed as of March 12, 2026)
- #8: `get_rgs()` returns `None` silently → `nan`
- #9: `plot_components()` not axis-injectable
- #10: No q-grid alignment utility
- #11: No component reliability indicator
- #12: Missing shape/unit docstrings
- #13: `ComponentCurve.y`, `trimmed_copy(nsigmas=)`, auto-mapping (v0.8.4)
- #14: `SecSaxsData` non-standard data support
- #15: Added `uv.wavelengths` and `uv.frames` aliases to `UvData`
- #23: `get_baseline2d()` printed `recognize_num_peaks`/`peak_width=` to stdout → suppressed with `redirect_stdout(io.StringIO())`
- #24: `'buffit'` baseline method — buffer-frame polyfit with Otsu adaptive threshold; `positive_ratio` 0.496–0.522 (nearest to ideal 0.5) on all 7 tested datasets
- #25: Replaced fixed `BUFFIT_THRESHOLD=0.10` with Otsu adaptive threshold in `BuffitBaseline.py`
- #26: Made `'buffit'` the default `baseline_method` for `XrData` (v0.8.4) — **later reverted to `'linear'`** (actual default in code is `'linear'`)
- #27: Add `molass.requires(version)` helper for version guard in notebooks/tests; updated all 10 tutorial tests and data_correction.ipynb (v0.8.4)

### Issues pending (filed, not yet implemented)
- (none)
