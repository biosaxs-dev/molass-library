"""
Test the composed homogeneity analysis SecSaxsData.homogeneity() (molass-library#325).
"""
import numpy as np
import pytest
import matplotlib
matplotlib.use("Agg")
from molass.Homogeneity import find_cores, HomogeneityResult


def test_010_find_cores_two_peaks():
    f = np.arange(200)
    y = np.exp(-0.5 * ((f - 60) / 8.0) ** 2) + 0.7 * np.exp(-0.5 * ((f - 140) / 8.0) ** 2)
    (a0, a1), (b0, b1) = find_cores(f, y)
    assert a0 < 60 < a1 < 100 < b0 < 140 < b1
    assert a1 - a0 == pytest.approx(2 * 8 * np.sqrt(2 * np.log(1 / 0.3)), abs=3)


def test_020_find_cores_single_peak_and_nan():
    f = np.arange(100)
    y = np.exp(-0.5 * ((f - 50) / 6.0) ** 2)
    y[3] = np.nan
    (a0, a1), = find_cores(f, y)
    assert a0 < 50 < a1


@pytest.fixture(scope="module")
def corrected():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1).trimmed_copy().corrected_copy()
    ssd.get_rg_curve()          # computed once, cached on the object
    return ssd


@pytest.fixture(scope="module")
def result(corrected):
    return corrected.homogeneity()


def test_030_default_set_and_cores(result):
    assert isinstance(result, HomogeneityResult)
    assert len(result.cores) == 2
    (a0, a1), (b0, b1) = result.cores
    assert abs(a0 - 77) <= 3 and abs(a1 - 113) <= 3 and abs(b0 - 145) <= 3 and abs(b1 - 170) <= 3
    assert len(result.ratios) == 6 and not result.skipped
    assert result.independent_axes == 6
    names = list(result.ratios)
    assert names[0].startswith("I(0)/I(") and names[1] == "I(0)/A280"
    assert result.is_classical(names[0]) and result.is_classical("I(0)/A280")
    assert not result.is_classical("A260/A280")


def test_040_statistics_reproduce_experiment_50e(result):
    f2 = result.stats[(1, "I(0)/A280")]               # peak 2: mapping artefact, tilt about -31 %
    assert f2.tilt == pytest.approx(-0.31, abs=0.03)
    assert abs(f2.curvature) < 0.1
    assert result.stats[(1, "A280/A290")].median == pytest.approx(1.58, abs=0.03)
    f1 = result.stats[(0, "A260/A280")]               # peak 1: the spectrum changes
    assert f1.tilt > 0.15 and f1.sd_over_noise > 10
    assert result.stats[(0, "I(0)/A280")].curvature < -0.3       # a hump
    assert result.ratios["A320/A280"].depends_on_mapping is False


def test_050_shifted_flattens_peak2_cross_ratio(result):
    base = result.stats[(1, "I(0)/A280")].sd
    shifted = result.shifted(-0.75)
    assert shifted.delta == -0.75
    assert shifted.stats[(1, "I(0)/A280")].sd < 0.5 * base
    assert shifted.stats[(1, "A260/A280")].median == pytest.approx(result.stats[(1, "A260/A280")].median, rel=0.01)


def test_060_reselect_skips_unavailable_and_rejects_unknown(result):
    r = result.reselect([("I(0)", "A280"), ("I(0.03)", "A280"), ("I(0)", "A999")])
    assert list(r.ratios) == ["I(0)/A280", "I(0.03)/A280"]
    assert len(r.skipped) == 1 and "A999" in r.skipped[0]
    assert r.independent_axes == 2
    with pytest.raises(KeyError):
        result.reselect([("I(0)", "B280")])


def test_070_summary_table_plot(result):
    text = result.summary()
    assert "core 1" in text and "core 2" in text and "independent axes" in text
    rows = result.table()
    assert len(rows) == 12 and {"core", "ratio", "sd", "tilt", "curvature", "classical"} <= set(rows[0])
    fig = result.plot()
    assert len(fig.axes) >= 2


def test_075_plot_with_many_classical_ratios(result):
    # more than two I(0)-numerator ratios used to exhaust the colour list
    names = ["I(0)", "I(0.021)", "I(0.063)", "A260", "A280", "A290"]
    pairs = [("I(0)", n) for n in names[1:]]
    fig = result.reselect(pairs).plot()
    assert len(fig.axes) >= 2


def test_080_xr_only_default_set(corrected):
    from molass.DataObjects import SecSaxsData as SSD
    xr = corrected.xr
    xr_only = SSD.from_arrays(xr.M, xr.qv, xr.E, xr_jv=xr.jv, trimmed=True)
    r = xr_only.homogeneity(rgcurve=corrected.get_rg_curve())
    assert len(r.ratios) == 2 and not r.skipped and r.independent_axes == 2
    assert all(not x.depends_on_mapping for x in r.ratios.values())


def test_090_mapping_argument_equals_shift(corrected, result):
    slope, intercept = tuple(corrected.get_mapping())
    delta = 0.5
    by_mapping = corrected.homogeneity(mapping=(slope, intercept - slope * delta), cores=result.cores)
    by_shift = result.shifted(delta)
    for key, f in by_shift.stats.items():
        assert by_mapping.stats[key].median == pytest.approx(f.median, rel=1e-6)
        assert by_mapping.stats[key].tilt == pytest.approx(f.tilt, rel=1e-6, abs=1e-9)
    assert result.mapping is not None and by_mapping.reselect([("I(0)", "A280")]).mapping is by_mapping.mapping


def test_100_decomposition_homogeneity_uses_its_own_mapping(corrected, result):
    from molass.Mapping.Mapping import Mapping
    from molass.Homogeneity import mapping_shift
    decomp = corrected.quick_decomposition()
    a, b = tuple(corrected.get_mapping())
    assert tuple(decomp.get_uv_mapping()) == pytest.approx((a, b))
    same = decomp.homogeneity(cores=result.cores)
    assert same.stats[(1, "I(0)/A280")].tilt == pytest.approx(result.stats[(1, "I(0)/A280")].tilt, rel=1e-6)
    # an "optimized" mapping, 0.75 frame earlier at every frame as in experiment 50b
    for uv_ccurve in decomp.uv_ccurves:
        uv_ccurve.mapping = Mapping(a, b - a * (-0.75))
    moved = decomp.homogeneity(cores=result.cores)
    np.testing.assert_allclose(mapping_shift((a, b), decomp.get_uv_mapping(), [100, 150]), -0.75)
    assert moved.stats[(1, "I(0)/A280")].sd < 0.5 * result.stats[(1, "I(0)/A280")].sd
    assert decomp.ssd.get_mapping() is not None and tuple(decomp.ssd.get_mapping()) == pytest.approx((a, b))
