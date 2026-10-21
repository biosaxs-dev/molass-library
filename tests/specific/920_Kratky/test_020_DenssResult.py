"""
Test SAXS.DenssResult: reading back the per-component DENSS result files.
"""
import numpy as np
import pytest

FITDATA = """# Parameter Values:
# Dmax  = 3.73900e+02
# alpha = 1.22204e-11
# Rg    = 1.32125e+02 +- 1.29753e+00
# I(0)  = 4.40477e+00 +- 9.98592e-03
# Vp    = -1.53920e-02 +- nan
# q, I, error, fit
0.00000e+00 0.00000e+00 9.97995e-03 4.40477e+00
1.00000e-02 0.00000e+00 1.00000e-02 4.00000e+00
2.00000e-02 0.00000e+00 1.00000e-02 3.00000e+00
"""

MAPFIT = """# q(data),I(data),error(data),I(density); chi2=3.838
1.00000e-02 3.90000e+00 5.00000e-02 3.60000e+00
2.00000e-02 3.00000e+00 2.00000e-02 2.90000e+00
3.00000e-02 2.00000e+00 2.00000e-02 2.10000e+00
"""


def _write_component(parent, n, rg, with_map=True):
    d = parent / f"component_{n}"
    d.mkdir()
    (d / f"component_{n}_fitdata.fit").write_text(FITDATA.replace("1.32125e+02", f"{rg:.5e}"))
    if with_map:
        (d / f"component_{n}_map.fit").write_text(MAPFIT)
    return d


def test_010_load_denss_fit(tmp_path):
    from molass.SAXS.DenssResult import load_denss_fit

    d = _write_component(tmp_path, 1, 132.125)
    fit = load_denss_fit(str(d))
    assert fit.prefix == "component_1"
    assert fit.Rg == pytest.approx(132.125) and fit.Iz == pytest.approx(4.40477)
    assert fit.params["Rg_err"] == pytest.approx(1.29753)
    assert fit.params["Dmax"] == pytest.approx(373.9)
    assert np.isnan(fit.params["Vp_err"])
    assert fit.params["chi2"] == pytest.approx(3.838)
    np.testing.assert_allclose(fit.q_fit, [0, 0.01, 0.02])
    np.testing.assert_allclose(fit.I_fit, [4.40477, 4.0, 3.0])
    np.testing.assert_allclose(fit.q, [0.01, 0.02, 0.03])
    np.testing.assert_allclose(fit.I, [3.9, 3.0, 2.0])
    np.testing.assert_allclose(fit.I_density, [3.6, 2.9, 2.1])
    assert "Rg=132.1" in repr(fit)


def test_020_load_without_map_and_missing(tmp_path):
    from molass.SAXS.DenssResult import load_denss_fit, denss_profiles_on_common_q

    d = _write_component(tmp_path, 1, 100.0, with_map=False)
    fit = load_denss_fit(str(d))
    assert fit.q is None and fit.I_density is None and "chi2" not in fit.params
    with pytest.raises(ValueError):
        denss_profiles_on_common_q([fit])
    with pytest.raises(FileNotFoundError):
        load_denss_fit(str(tmp_path / "nowhere"))


def test_030_components_in_numeric_order_and_common_q(tmp_path):
    from molass.SAXS.DenssResult import load_denss_components, denss_profiles_on_common_q

    for n, rg in ((10, 50.0), (2, 90.0), (1, 130.0)):
        _write_component(tmp_path, n, rg)
    (tmp_path / "other_folder").mkdir()
    fits = load_denss_components(str(tmp_path))
    assert [f.prefix for f in fits] == ["component_1", "component_2", "component_10"]
    assert [round(f.Rg) for f in fits] == [130, 90, 50]
    q, P = denss_profiles_on_common_q(fits)
    assert P.shape == (3, 3)
    q2, P2 = denss_profiles_on_common_q(fits, q=np.array([0.015]))
    np.testing.assert_allclose(P2[0], 3.45)
    with pytest.raises(FileNotFoundError):
        load_denss_components(str(tmp_path / "other_folder"))
