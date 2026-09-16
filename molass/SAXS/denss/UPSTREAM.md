# Vendored DENSS

This folder contains a vendored copy of [DENSS](https://github.com/tdgrant1/denss)
used by molass for ab-initio 3D reconstruction.

## Source

- Upstream: https://github.com/tdgrant1/denss
- Vendored version: **DENSS v1.8.8** (see `_version.py`; not yet tagged upstream as of this
  sync — corresponds to upstream commit `5009b1c`, "update version number to 1.8.8")
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
2. **GUI/progress hooks**, split across three call sites (corrected 2026-09-16 — previously
   this entry conflated the functions involved):
   - `reconstruct_abinitio_from_scattering_profile(...)` — added `progress_cb=None` kwarg,
     invoked once per iteration as `progress_cb(j, chi[j], rg[j], supportV[j])`.
   - `Sasrec.optimize_alpha(quiet=False)` — added `gui=False` kwarg; when `True`, routes the
     progress message through a `logging.getLogger()` instance instead of `sys.stdout.write`.
     Re-homed onto the new upstream L-curve algorithm on 2026-09-16 (see "Catch-up procedure"
     below) since the old algorithm it was originally written against no longer exists upstream.
   - `Sasrec.estimate_Vp_etal(...)` — added `qmax = max(0.1, qmax)` floor (previously
     mislabeled in this file as belonging to `optimize_alpha`) plus an `if self.logger is not
     None: self.logger.info(...)` call. `self.logger` on `Sasrec` is set in `__init__` from a
     hardcoded `debug = False` flag, so in practice it is always `None` today (dead but
     harmless code, kept for parity with the pre-2026-09-16 vendored copy).
3. **`write_mrc` explicit `float()` conversion** — `a, b, c = float(side[0]), float(side[1]),
   float(side[2])` instead of passing `side`/1-element numpy arrays directly to
   `struct.pack('<fff', ...)` (Python 3.14 no longer accepts implicit numpy-array-to-float).
4. **NumPy 2.0 / Python 3.14 compatibility** (April 2026):
   - `np.in1d(..., assume_unique=True)` → `np.isin(...)`
     (`np.in1d` removed in NumPy 2.0).
   - `np.trapz(...)` → `np.trapezoid(...)` (3 sites in `direct_I2P`, `P2Rg`)
     (`np.trapz` removed in NumPy 2.0).

All #3-#4 fixes are also applicable upstream (see `tdgrant1/denss` `denss/core.py`
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

## Sync history

- **2026-09-16** — v1.8.7 → v1.8.8 (upstream commit `5009b1c`). Notable upstream changes:
  new BIC-based auto Dmax/alpha estimator (`estimate_rough_alpha`, rewritten `optimize_alpha`),
  new `clean_low_q_artifacts` beam-stop trimming helper, dihedral symmetry bug fix. Performed
  via `denss-update/denss_update.ipynb` (see below) rather than the old `update-denss.py` /
  `update-custom-codes.py` scripts, which were stale (hardcoded pre-restructure upstream paths
  like `bin/`, `saxstats/scriptsbin`). Caught and fixed one real gap during this sync: the
  `write_mrc` float() conversion (item 3 above) was initially dropped from the merge despite
  being flagged by the notebook's own marker-listing cell — a reminder that a diagnostic
  finding something is not the same as it being acted on.
  Follow-up not done in this pass: evaluate porting the new BIC Dmax/alpha estimator into
  `molass/SAXS/DmaxEstimation.py` (design decision, tracked separately).

## Catch-up procedure

The steps below are now largely carried out by `denss-update/denss_update.ipynb` (a shared
human/AI notebook workflow) rather than by hand. The manual description is kept here as the
authoritative reference for what the notebook automates:

1. Note the current upstream commit/tag in this file.
2. Replace `core-orig.py` / `options-orig.py` with the new upstream files.
3. Re-apply the local edits listed above (`# molass-fork:` markers help
   locate them in the current `core.py` / `options.py`).
4. Update the "Vendored version" line above.
5. Run the molass test suite to verify.
