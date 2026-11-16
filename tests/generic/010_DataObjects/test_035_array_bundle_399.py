import json
import pickle
import subprocess
import sys

import numpy as np
import pytest

from molass.DataObjects.XrData import XrData
from molass.Global.ArrayBundle import ArrayBundle
from molass.Guinier.RgCurve import RgCurve
from molass.Testing import Species, simulate_ssd


def _bundle():
    return ArrayBundle(
        {"M": np.arange(12.0).reshape(3, 4), "jv": np.arange(4), "flag": np.array([True, False])},
        meta={"kind": "test"},
    )


def _assert_same(a, b):
    assert sorted(a.keys()) == sorted(b.keys()) and a.meta == b.meta
    for name in a:
        assert a[name].dtype == b[name].dtype
        np.testing.assert_array_equal(a[name], b[name])


def test_pickle_and_disk_round_trip(tmp_path):
    bundle = _bundle()
    _assert_same(bundle, pickle.loads(pickle.dumps(bundle)))
    bundle.save(tmp_path)
    _assert_same(bundle, ArrayBundle.load(tmp_path))
    with ArrayBundle.load(tmp_path, mmap=True) as mapped:
        assert not mapped["M"].flags.writeable


def test_unsafe_names_and_object_arrays_are_rejected():
    with pytest.raises(ValueError):
        ArrayBundle({"../x": np.zeros(1)})
    with pytest.raises(TypeError):
        ArrayBundle({"x": np.array([object()])})
    with pytest.raises(TypeError):
        ArrayBundle({"x": np.zeros(1)}, meta={"bad": object()})


def test_shared_views_follow_the_owner_and_are_read_only():
    with _bundle().share() as owner:
        with ArrayBundle.attach(owner.spec) as reader:
            _assert_same(_bundle(), reader)
            assert not reader["M"].flags.writeable
            owner.bundle["M"][0, 0] = 99.0
            assert reader["M"][0, 0] == 99.0


def test_a_child_process_reads_the_input_and_fills_the_output():
    child = (
        "import json, sys\n"
        "from molass.Global.ArrayBundle import ArrayBundle\n"
        "spec_in, spec_out = json.loads(sys.stdin.read())\n"
        "with ArrayBundle.attach(spec_in) as a, ArrayBundle.attach(spec_out, readonly=False) as out:\n"
        "    out['total'][0] = a['M'].sum()\n"
        "    out['colsum'][:] = a['M'].sum(axis=0)\n"
    )
    with _bundle().share() as source, ArrayBundle.zeros({"total": ((1,), float), "colsum": ((4,), float)}).share() as sink:
        stdin = json.dumps([source.spec, sink.spec])      # the specs are plain JSON
        subprocess.run([sys.executable, "-c", child], input=stdin, text=True, check=True, timeout=120)
        assert sink.bundle["total"][0] == np.arange(12.0).sum()
        np.testing.assert_array_equal(sink.bundle["colsum"], np.arange(12.0).reshape(3, 4).sum(axis=0))


def _ssd():
    species = [Species(amp=1.0, center=30, sigma=5, mass=2.0, rg=36.0)]
    return simulate_ssd(species, noise=1.0, seed=1, xr_frames=np.arange(60))


def test_xr_data_round_trip_through_shared_memory():
    xr = _ssd().xr
    with xr.to_bundle().share() as owner, ArrayBundle.attach(owner.spec) as bundle:
        again = XrData.from_bundle(bundle)
        for name in ("M", "qv", "jv", "E"):
            np.testing.assert_array_equal(getattr(again, name), getattr(xr, name))
        assert again.pickat == xr.pickat and again.baseline_method == xr.baseline_method
        del again


def test_rg_curve_round_trip_through_a_bundle():
    curve = _ssd().get_rg_curve()
    with curve.to_bundle().share() as owner, ArrayBundle.attach(owner.spec) as bundle:
        again = RgCurve.from_bundle(bundle)
    np.testing.assert_array_equal(again.frames, curve.frames)
    np.testing.assert_allclose(again.rgs, curve.rgs, equal_nan=True)
    np.testing.assert_allclose(again.scores, curve.scores)
    np.testing.assert_allclose(again.i0s, curve.i0s, equal_nan=True)
    assert again.score_source == curve.score_source
