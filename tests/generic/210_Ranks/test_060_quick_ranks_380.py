"""molass-library#380: quick_decomposition(ranks=...) is applied, not silently ignored."""
import warnings

import pytest

molass_data = pytest.importorskip("molass_data")
from molass.DataObjects import SecSaxsData as SSD


@pytest.fixture(scope="module")
def corrected():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SSD(molass_data.SAMPLE3).trimmed_copy().corrected_copy()


def test_ranks_keyword_equals_update_xr_ranks(corrected):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        by_keyword = corrected.quick_decomposition(num_components=1, ranks=[2])
        by_update = corrected.quick_decomposition(num_components=1)
        by_update.update_xr_ranks([2])
        plain = corrected.quick_decomposition(num_components=1)
    assert by_keyword.xr_ranks == [2]
    assert by_keyword.get_rgs() == pytest.approx(by_update.get_rgs())
    assert plain.xr_ranks is None
    assert by_keyword.get_rgs()[0] != pytest.approx(plain.get_rgs()[0], abs=0.1)     # rank 2 changes the Rg of SAMPLE3


def test_ranks_of_wrong_length_raises(corrected):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="Length of ranks"):
            corrected.quick_decomposition(num_components=1, ranks=[1, 2])
