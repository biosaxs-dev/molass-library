"""
    Test Decomposition.export() -- figure-reproducing export (molass-library#319).
"""
import json
import numpy as np
import pytest
from molass import get_version
get_version(toml_only=True)
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD


@pytest.fixture(scope="module")
def decomp():
    ssd = SSD(SAMPLE1)
    corrected = ssd.trimmed_copy().corrected_copy()
    return corrected.quick_decomposition(num_components=3)


def test_export_dat_files_and_contents(decomp, tmp_path):
    paths = decomp.export(str(tmp_path))
    names = {p.replace("\\", "/").split("/")[-1] for p in paths}
    n = decomp.num_components
    expected = {f"component_{i + 1}.dat" for i in range(n)}
    expected |= {"xr_elution.dat", "uv_elution.dat", "uv_spectra.dat", "guinier.dat", "summary.json"}
    assert expected <= names
    assert paths[-1].endswith("summary.json")

    # component files are unchanged from export_xr_components()
    for i, comp in enumerate(decomp.get_xr_components()):
        np.testing.assert_allclose(np.loadtxt(tmp_path / f"component_{i + 1}.dat"),
                                   comp.get_jcurve_array())

    xr = np.loadtxt(tmp_path / "xr_elution.dat")
    assert xr.shape == (len(decomp.xr_icurve.x), n + 4)
    np.testing.assert_allclose(xr[:, 0], decomp.xr_icurve.x)
    np.testing.assert_allclose(xr[:, 2:2 + n].sum(axis=1), xr[:, 2 + n])
    np.testing.assert_allclose(xr[:, 1] - xr[:, 2 + n], xr[:, 3 + n], atol=1e-10)
    header = (tmp_path / "xr_elution.dat").read_text().splitlines()[0]
    assert header.startswith("# frame xr_total comp1")

    uv_spectra = np.loadtxt(tmp_path / "uv_spectra.dat")
    assert uv_spectra.shape == (len(decomp.uv.wv), n + 1)


def test_export_csv_loads_with_header(decomp, tmp_path):
    decomp.export(str(tmp_path), fmt='csv')
    with open(tmp_path / "guinier.csv") as fh:
        assert fh.readline().strip() == "component,rg,i0,q_min,q_max,score"
    data = np.loadtxt(tmp_path / "guinier.csv", delimiter=',', skiprows=1)
    assert data.shape == (decomp.num_components, 6)
    np.testing.assert_allclose(data[:, 1], decomp.get_rgs(), equal_nan=True)
    assert (tmp_path / "component_1.csv").exists()


def test_export_column_names_are_igor_safe(decomp, tmp_path):
    import re
    decomp.export(str(tmp_path), fmt='csv')
    for f in tmp_path.glob("*.csv"):
        if f.name.startswith("component_"):
            continue
        for name in f.read_text().splitlines()[0].split(','):
            assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,30}", name), (f.name, name)


def test_export_summary_and_rg_curve_skipped_by_default(decomp, tmp_path):
    decomp.export(str(tmp_path))
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["num_components"] == decomp.num_components
    assert len(summary["components"]) == decomp.num_components
    if not decomp.has_rg_curve:
        assert "rg_curve" in summary["skipped"]
        assert not (tmp_path / "rg_curve.dat").exists()


def test_export_rg_curve_when_given(decomp, tmp_path):
    from molass.Guinier.RgCurve import RgCurve
    frames = np.asarray(decomp.xr_icurve.x, dtype=int)
    rgcurve = RgCurve(frames, np.linspace(30, 20, len(frames)), np.ones(len(frames)))
    decomp.export(str(tmp_path), rgcurve=rgcurve)
    data = np.loadtxt(tmp_path / "rg_curve.dat")
    np.testing.assert_allclose(data[:, 0], frames)
    np.testing.assert_allclose(data[:, 1], rgcurve.rgvalues)


def test_export_rejects_unknown_format(decomp, tmp_path):
    with pytest.raises(ValueError):
        decomp.export(str(tmp_path), fmt='xlsx')
