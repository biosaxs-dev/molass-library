"""
    The ``fast`` subset of tests/generic (molass-library#389): pure-logic tests and tests on bundled
    simulated data that need no local data (no ``local_settings.py``, no Dropbox) and take seconds
    (about 1.5 minutes in all).  CI runs it on every push: ``pytest tests/generic -m fast``.
    The full suite (about 35 minutes, needs the local data) is ``pytest tests/tutorial tests/generic``.

    To add a module, append its path (relative to this folder, without ``.py``) to FAST_MODULES.
"""
import pytest

FAST_MODULES = {
    "005_Version/test_010_Version",
    "005_Version/test_020_numba_parallel_start",
    "005_Version/test_020_version_info_378",
    "005_Version/test_030_environment_report",
    "007_Options/test_010_Options",
    "007_Options/test_020_progress_switch_375",
    "010_DataObjects/test_020_RgCurve_i0",
    "010_DataObjects/test_030_did_you_mean",
    "020_DataUtils/test_020_DropboxSync",
    "110_Trimming/test_020_anomaly_handler",
    "130_Mapping/test_020_peak_matcher",
    "130_Mapping/test_030_subframe_peaks",
    "130_Mapping/test_040_mapping_vocabulary",
    "130_Mapping/test_050_mapping_resolution",
    "130_Mapping/test_060_simulator",
    "130_Mapping/test_070_peak_core_valley",
    "130_Mapping/test_080_mapping_quality_371",
    "200_LRF/test_020_BoundedLrf",
    "200_LRF/test_060_ai_friendliness_343_347",
    "200_LRF/test_060_proportional_degenerate",
    "200_LRF/test_090_proportional_boundaries",
    "200_LRF/test_110_quick_options",
    "200_LRF/test_112_rgcurve_repr",
    "200_LRF/test_113_rgcurve_reliable_361",
    "200_LRF/test_114_continuity_report_370",
    "200_LRF/test_115_rg_helpers_and_shape_cache_374_377",
    "210_Ranks/test_215_title_ranks",
    "215_Homogeneity/test_215_Homogeneity",
    "230_ErrorModel/test_010_sedlak_390",
    "810_VoxelSpace/test_010_shapes",
    "910_DENSS/test_020_denss_detector",
    "test_log_streams",
}


def pytest_collection_modifyitems(items):
    for item in items:
        path = item.path.as_posix()
        if "/tests/generic/" not in path:
            continue
        module = path.split("/tests/generic/", 1)[1].removesuffix(".py")
        if module in FAST_MODULES:
            item.add_marker(pytest.mark.fast)
