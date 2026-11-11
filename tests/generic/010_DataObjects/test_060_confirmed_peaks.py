"""
    Test issue #382: the detected XR peaks and their confirmation by the XR/UV mapping.
"""
import pytest
from molass import get_version
get_version(toml_only=True)
from molass.Decompose.Recommend import confirm_peaks, restrict_to_confirmed

# the numbers of PROTEINS5 (molass_benchmarks)
DETECTED = [500, 562, 648, 758, 827, 871, 1103]
MAPPING_PEAKS = [561, 648, 760, 825, 878]


def test_confirm_peaks_flags_the_detected_peaks_near_a_mapping_peak():
    c = confirm_peaks(DETECTED, MAPPING_PEAKS)
    assert c.positions.tolist() == DETECTED
    assert c.confirmed.tolist() == [False, True, True, True, True, True, False]
    assert c.confirmed_positions.tolist() == [562, 648, 758, 827, 871]
    assert c.num_mapping_peaks == 5 and c.tolerance == 10
    assert confirm_peaks(DETECTED, MAPPING_PEAKS, tolerance=5).confirmed[5] == False    # 871 vs 878 needs 7 frames


def test_confirm_peaks_without_mapping_peaks_confirms_nothing():
    c = confirm_peaks(DETECTED, [])
    assert not c.confirmed.any() and c.num_mapping_peaks == 0
    assert confirm_peaks(None, MAPPING_PEAKS).positions.tolist() == []


def test_restrict_to_confirmed_needs_a_mapping_of_three_peaks():
    opts = {'num_components': 7, 'xr_peakpositions': DETECTED}
    restricted = restrict_to_confirmed(opts, confirm_peaks(DETECTED, MAPPING_PEAKS))
    assert restricted['num_components'] == 5
    assert restricted['xr_peakpositions'] == [562, 648, 758, 827, 871]
    assert opts['num_components'] == 7                      # the input is left alone
    # SAMPLE1: the real shoulder at 110 has no mapping peak, and the mapping has only two
    sample1 = {'num_components': 3, 'xr_peakpositions': [89, 110, 157]}
    assert restrict_to_confirmed(sample1, confirm_peaks([89, 110, 157], [88, 157])) is sample1


def test_restrict_to_confirmed_leaves_other_cases_and_keeps_ranks_consistent():
    proportions = {'num_components': 3, 'proportions': [1, 1, 1]}
    assert restrict_to_confirmed(proportions, confirm_peaks(DETECTED, MAPPING_PEAKS)) is proportions
    all_confirmed = {'num_components': 5, 'xr_peakpositions': [562, 648, 758, 827, 871]}
    assert restrict_to_confirmed(all_confirmed, confirm_peaks([562, 648, 758, 827, 871], MAPPING_PEAKS)) is all_confirmed
    with_ranks = {'num_components': 7, 'xr_peakpositions': DETECTED, 'ranks': [2] * 7}
    assert restrict_to_confirmed(with_ranks, confirm_peaks(DETECTED, MAPPING_PEAKS))['ranks'] == [2] * 5


@pytest.fixture(scope="module")
def proteins5():
    mb = pytest.importorskip("molass_benchmarks")
    from molass.DataObjects import SecSaxsData as SSD
    return SSD(mb.PROTEINS5).trimmed_copy().corrected_copy()


def test_proteins5_confirmed_peaks_are_a_subset_of_the_detected_ones(proteins5):
    detected = proteins5.recommend_decomposition_options()['xr_peakpositions']
    c = proteins5.get_confirmed_peaks()
    assert c.positions.tolist() == detected
    assert set(c.confirmed_positions.tolist()) <= set(detected)
    assert c.confirmed_positions.tolist() == [562, 648, 758, 827, 871]
    assert c.num_mapping_peaks == 5


def test_proteins5_confirm_with_uv_gives_the_five_proteins(proteins5):
    assert proteins5.recommend_decomposition_options()['num_components'] == 7      # the default is unchanged
    opts = proteins5.recommend_decomposition_options(confirm_with_uv=True)
    assert opts['num_components'] == 5
    assert opts['xr_peakpositions'] == [562, 648, 758, 827, 871]
    decomp = proteins5.quick_decomposition(**opts)
    assert len(decomp.get_xr_components()) == 5
