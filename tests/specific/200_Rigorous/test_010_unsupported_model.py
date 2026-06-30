"""
Test that construct_legacy_optimizer raises NotImplementedError
for unsupported models instead of an opaque TypeError.

See: https://github.com/biosaxs-dev/molass-library/issues/92
"""
import pytest


def test_unsupported_model_raises_not_implemented():
    """Passing an unrecognized model string must raise NotImplementedError."""
    from molass.Rigorous.LegacyBridgeUtils import construct_legacy_optimizer

    # Minimal dummy arguments — the function should fail before using them
    dummy_dsets = None
    dummy_baselines = (None, None)
    dummy_spectral = (None, None)

    with pytest.raises(NotImplementedError, match="does not support model"):
        construct_legacy_optimizer(
            dummy_dsets, dummy_baselines, dummy_spectral,
            model="NONEXISTENT",
        )


def test_unsupported_function_code_raises_not_implemented():
    """Passing an unrecognized function_code must raise NotImplementedError."""
    from molass.Rigorous.LegacyBridgeUtils import construct_legacy_optimizer

    dummy_dsets = None
    dummy_baselines = (None, None)
    dummy_spectral = (None, None)

    with pytest.raises(NotImplementedError, match="does not support model"):
        construct_legacy_optimizer(
            dummy_dsets, dummy_baselines, dummy_spectral,
            function_code="G9999",
        )
