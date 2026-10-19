"""molass-library#302: molass.environment_report()"""
import json

import molass


def test_environment_report_content():
    r = molass.environment_report()
    assert r["molass"] == molass.__version__
    assert r["packages"]["numpy"] is not None
    assert isinstance(r["blas"], list) and r["blas"], "threadpoolctl is a dependency of scikit-learn"
    assert {"internal_api", "version", "architecture", "num_threads"} <= set(r["blas"][0])
    json.dumps(r)


def test_environment_report_shows_relevant_env_vars(monkeypatch):
    monkeypatch.setenv("OPENBLAS_CORETYPE", "NEHALEM")
    assert molass.environment_report()["env"]["OPENBLAS_CORETYPE"] == "NEHALEM"
