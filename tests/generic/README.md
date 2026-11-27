# tests/generic

## Which command to run

| Purpose | Command | Time |
|---|---|---|
| CI subset: pure logic and bundled simulated data (`fast`, see `FAST_MODULES` in `conftest.py`) | `pytest tests/generic -m fast` | about 2.5 min |
| Everything except the slow tests (`slow`, see `SLOW_TESTS` in `conftest.py`) | `pytest tests/generic -m "not slow"` | needs the local data |
| One file, with the slowest tests listed | `pytest tests/generic/210_Ranks/test_030_rg_call_order.py --durations=5` | |

The slow tests (molass-library#422), measured 2026-11-26:

| Test | Time |
|---|---|
| `210_Ranks/test_040_getter_order_independence.py::test_getters_are_order_independent[rank2]` / `[rank1]` | 259 s / 157 s |
| `210_Ranks/test_010_Ranks.py::test_010_compute_scds` | 44 s |
| `210_Ranks/test_030_rg_call_order.py::test_get_rgs_independent_of_call_order` | 33-60 s |

Running `200_LRF` and `210_Ranks` together takes more than 25 minutes; run by file.

## Which tests cover which source

| Source | Tests |
|---|---|
| `LowRank/Decomposition.py`: `get_xr_matrices`, `update_xr_ranks`, `set_rank2_method` | `200_LRF/test_130_soft_bounded_lrf.py` (fast, about 70 s), `210_Ranks/test_020_update_xr_ranks.py`, `210_Ranks/test_060_quick_ranks_380.py`; the call-order tests `210_Ranks/test_030_*` and `test_040_*` are slow |
| `LowRank/SoftBoundedLrf.py`, `ConcentrationRefine.py`, `LowRankInfo.get_weighted_denoised_data` | `200_LRF/test_130_soft_bounded_lrf.py` |
| `LowRank/Rank2Report.py` (`rank2_report()`) | `200_LRF/test_150_rank2_report_420.py` (fast) |
| `LowRank/Findings.py`, `findings()` of the infos, the impact of `rank2_report()` | `200_LRF/test_170_findings_423.py` (fast) |
| `LowRank/SecondDirection.py` (`second_direction_report()`) | `200_LRF/test_180_second_direction_417.py` (fast) |
| `LowRank/CorrectInterparticle.py` (`correct_interparticle`) | `200_LRF/test_160_correct_interparticle_414.py` (fast) |
| `Guinier/RgConventions.py` (`rg_conventions`), `RgEstimator` repr / `describe()` | `200_LRF/test_140_rg_conventions_419.py` (fast) |
| `LowRank/BoundedLrf.py` | `200_LRF/test_020_BoundedLrf.py` (fast) |
| `LowRank/ErrorScale.py`, residual report | `230_ErrorModel/test_020_error_scale_416.py`, `200_LRF/test_116_residual_report_392.py` |
| `molass.Testing` (`interparticle_frames`, `simulate_tiny`) | `200_LRF/test_120_interparticle_frames_415.py`, `130_Mapping/test_090_simulate_tiny_387.py` |
| `Guinier/RgEstimator.py`, Rg getters | `200_LRF/test_030_get_rgs.py`, `200_LRF/test_080_rg_order_penalty.py`, `210_Ranks/test_030_rg_call_order.py` (slow) |

A change in `Decomposition.get_xr_matrices` is validated by
`pytest tests/generic/200_LRF/test_130_soft_bounded_lrf.py tests/generic/210_Ranks/test_020_update_xr_ranks.py tests/generic/210_Ranks/test_060_quick_ranks_380.py`,
plus the slow call-order files when the change touches caching or the order of calls.
