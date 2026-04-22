# Vendored DENSS

This folder contains a vendored copy of [DENSS](https://github.com/tdgrant1/denss)
used by molass for ab-initio 3D reconstruction.

## Source

- Upstream: https://github.com/tdgrant1/denss
- Vendored version: **DENSS v1.8.7** (see `_version.py`)
- License: GPL v3 (preserved; see upstream `LICENSE`)

## Local modifications

All deviations from the unmodified upstream `core.py` / `options.py` are
preserved as `core-orig.py` / `options-orig.py` for diffing:

```powershell
git diff --no-index core-orig.py core.py
git diff --no-index options-orig.py options.py
```

> **`*-orig.py` are read-only baselines.** Each file carries a `# molass-fork: DO NOT EDIT`
> header. The header itself is the **only** intentional deviation from pristine upstream;
> ignore it when diffing (e.g., `git diff -I '^# molass-fork:'` or skip the first 3 lines).
> Drift incident on 2026-04-16 — see "Known caveats" below — was the motivation (issue #110).

Local edits within the vendored Python files are tagged with the comment
marker `# molass-fork:` so they can be listed via:

```powershell
Select-String -Path *.py -Pattern "molass-fork:"
```

### Summary of local edits

1. **Import path adjustment** — `denss.resources` → `molass.SAXS.denss.resources`
   (required because we vendor under `molass/SAXS/denss/`).
2. **GUI/progress hooks** — added `progress_cb`, `gui` kwargs and an
   optional `self.logger` for integration with the molass GUI.
3. **`optimize_alpha(qmax)` floor** — `qmax = max(0.1, qmax)` to avoid
   degenerate low-qmax behavior on truncated profiles.
4. **NumPy 2.0 / Python 3.14 compatibility** (April 2026):
   - `np.in1d(..., assume_unique=True)` → `np.isin(...)`
     (`np.in1d` removed in NumPy 2.0).
   - `np.trapz(...)` → `np.trapezoid(...)` (3 sites in `direct_I2P`, `P2Rg`)
     (`np.trapz` removed in NumPy 2.0).
   - `write_mrc`: explicit `float()` conversion of `side` values before
     `struct.pack('<fff', a, b, c)` (Python 3.14's `struct.pack` no longer
     accepts 1-element NumPy arrays implicitly).

All #4 fixes are also applicable upstream (see `tdgrant1/denss` `denss/core.py`
as of 2026-04-21 — none have been applied there).

## Known caveats about the baseline

- `core-orig.py` was inadvertently edited on 2026-04-16 (commit `023a3bb`) with
  the `np.trapz` → `np.trapezoid` change. It was restored to its true
  upstream-v1.8.7 state (commit `0db382f`, 2025-12-11) on 2026-04-21, and the
  trapezoid edits were re-classified as fork modifications (item #4 above).
- `options-orig.py` was last updated on 2025-09-19 (commit `6d0261a`), prior
  to the 1.8.7 import. The 1.8.7 update commit (`0db382f`) did not touch
  `options.py`/`options-orig.py`. Whether this means upstream `options.py`
  was unchanged between the prior version and 1.8.7, or whether the file
  was simply skipped during that import, has not been verified. Worth
  checking on the next refresh.

## Catch-up procedure

When refreshing against a new upstream release:

1. Note the current upstream commit/tag in this file.
2. Replace `core-orig.py` / `options-orig.py` with the new upstream files.
3. Re-apply the local edits listed above (`# molass-fork:` markers help
   locate them in the current `core.py` / `options.py`).
4. Update the "Vendored version" line above.
5. Run the molass test suite to verify.
