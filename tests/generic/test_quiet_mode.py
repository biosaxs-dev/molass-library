"""Test for quiet mode (issue #83, default flipped in #398).

Verifies that quiet mode (the default) suppresses
stdout output from the core pipeline:
SSD() -> trimmed_copy() -> corrected_copy() -> quick_decomposition()
"""
import io
import subprocess
import sys
import pytest


@pytest.fixture(autouse=True)
def restore_quiet_option():
    from molass.Global.Options import get_molass_options, set_molass_options
    saved = get_molass_options('quiet')
    yield
    set_molass_options(quiet=saved)


def test_quiet_is_the_default():
    from molass.Global.Options import GLOBAL_OPTIONS
    assert GLOBAL_OPTIONS['quiet'] is True


def test_quiet_suppresses_pipeline_output():
    """Full pipeline with quiet=True should produce no stdout."""
    from molass.Global.Options import set_molass_options
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    set_molass_options(quiet=True)
    try:
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf

        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition()

        sys.stdout = old_stdout
        output = buf.getvalue()
        # Should have zero or near-zero stdout output
        assert len(output.strip()) == 0, (
            f"quiet=True should suppress pipeline output, but got {len(output)} chars:\n{output[:200]}"
        )
    finally:
        sys.stdout = old_stdout


def test_quiet_mode_still_shows_the_warnings_meant_for_the_user():
    """In a real process the UserWarning reaches stderr; the legacy RuntimeWarning does not."""
    script = (
        "import warnings\n"
        "from molass.Global.Quiet import suppress_if_quiet\n"
        "with suppress_if_quiet():\n"
        "    print('legacy trace')\n"
        "    warnings.warn('numerical noise', RuntimeWarning)\n"
        "    warnings.warn('num_components=4 returned 3 components', UserWarning)\n"
    )
    done = subprocess.run([sys.executable, "-W", "always", "-c", script], capture_output=True, text=True,
                          timeout=300)
    assert done.returncode == 0
    assert "legacy trace" not in done.stdout + done.stderr
    assert "numerical noise" not in done.stderr
    assert "returned 3 components" in done.stderr


def test_quiet_false_does_not_suppress():
    """With quiet=False, the context manager is a no-op."""
    from molass.Global.Options import set_molass_options
    from molass.Global.Quiet import suppress_if_quiet

    set_molass_options(quiet=False)
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    with suppress_if_quiet():
        print("VISIBLE")
    sys.stdout = old_stdout
    assert "VISIBLE" in buf.getvalue()


def test_debug_overrides_quiet():
    """debug=True should bypass quiet mode."""
    from molass.Global.Options import set_molass_options
    from molass.Global.Quiet import suppress_if_quiet

    set_molass_options(quiet=True)
    try:
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        with suppress_if_quiet(debug=True):
            print("DEBUG_VISIBLE")
        sys.stdout = old_stdout
        assert "DEBUG_VISIBLE" in buf.getvalue()
    finally:
        set_molass_options(quiet=False)
