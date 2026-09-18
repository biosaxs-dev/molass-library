"""
    Test Decomposition.export_xr_components() -- library-level equivalent of
    molass_gui/plot_embed.py::export_component_data(), so the GUI and
    scripts/notebooks share one implementation instead of duplicating the
    np.savetxt loop (molass-library#276 follow-up).
"""
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


def test_export_xr_components_writes_expected_files(decomp, tmp_path):
    folder = tmp_path / "exported"
    paths = decomp.export_xr_components(str(folder))

    assert len(paths) == decomp.num_components
    for i, path in enumerate(paths):
        assert path == str(folder / f"component_{i + 1}.dat")
        assert (folder / f"component_{i + 1}.dat").exists()


def test_export_xr_components_matches_jcurve_array(decomp, tmp_path):
    folder = tmp_path / "exported2"
    paths = decomp.export_xr_components(str(folder))

    components = decomp.get_xr_components()
    for path, comp in zip(paths, components):
        loaded = np.loadtxt(path)
        np.testing.assert_allclose(loaded, comp.get_jcurve_array())


def test_export_xr_components_creates_folder_if_missing(decomp, tmp_path):
    folder = tmp_path / "does" / "not" / "exist" / "yet"
    assert not folder.exists()
    decomp.export_xr_components(str(folder))
    assert folder.exists()
