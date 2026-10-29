"""The interparticle detection of recommend_decomposition_options() with the default trimming (molass-library#342).

The suppression ratio is taken at the first q point kept, so the default trimming that keeps more low-q points made the
former threshold (0.995) flag the ordinary SAMPLE1 and SAMPLE5 and ``recommend_decomposition()`` applied rank 2 to them.
Measured values (molass-researcher experiment 53b): SAMPLE3 0.81, SAMPLE1 0.988, SAMPLE5 0.994, SAMPLE2/4/6 >= 0.997.
"""
import pytest

from molass.Decompose import Recommend


def test_threshold_separates_the_measured_samples():
    t = Recommend._LOWQ_SUPPRESSION_THRESHOLD
    assert 0.81 < t < 0.988


@pytest.mark.parametrize("sample, flagged", [("SAMPLE1", False), ("SAMPLE3", True)])
def test_default_trimming_flags_only_the_interparticle_sample(sample, flagged):
    import molass_data
    from molass.DataObjects import SecSaxsData as SSD

    corrected = SSD(getattr(molass_data, sample)).trimmed_copy().corrected_copy()
    opts = corrected.recommend_decomposition_options()
    assert ('ranks' in opts) is flagged
