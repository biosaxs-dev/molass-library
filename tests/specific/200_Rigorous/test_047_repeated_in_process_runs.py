"""molass-library#334: a second optimize_rigorously(in_process=True) in the same process must work."""
import numpy as np
import pytest

from molass.Testing import Species, simulate_ssd

SPECIES = [Species(amp=1.0, center=40, sigma=5.0, mass=2.5, rg=36.0),
           Species(amp=1.0, center=75, sigma=5.0, mass=1.0, rg=24.0)]
# a compact geometry keeps the two optimizer runs short
AXES = dict(qv=np.linspace(0.0143, 0.3, 150), wv=np.linspace(250.0, 400.0, 40),
            xr_frames=np.arange(120), uv_frames=np.arange(3, 176))


def _run(ssd, folder):
    decomp = ssd.quick_decomposition(num_components=2)
    return decomp.optimize_rigorously(rgcurve=ssd.get_rg_curve(), analysis_folder=str(folder), method="BH", niter=1,
                                      in_process=True, async_=False, monitor=False, clear_jobs=True)


def test_two_in_process_runs_in_one_process(tmp_path):
    first = _run(simulate_ssd(SPECIES, seed=1, **AXES), tmp_path / "run1")
    second = _run(simulate_ssd(SPECIES, seed=2, **AXES), tmp_path / "run2")     # used to fail in prepare_rigorous_folders
    for run_info in (first, second):
        assert run_info.is_done
        assert run_info.load_best().num_components == 2
