"""Test for quiet mode (issue #83).

Verifies that set_molass_options(quiet=True) suppresses
stdout output from the core pipeline:
SSD() -> trimmed_copy() -> corrected_copy() -> quick_decomposition()
"""
import io
import sys
import pytest

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
        set_molass_options(quiet=False)


def test_quiet_false_does_not_suppress():
    """With quiet=False (default), the context manager is a no-op."""
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
