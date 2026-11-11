"""
    Global.DidYouMean.py

    A mixin that adds hints to the AttributeError of a wrong attribute guess (molass-library#338).
"""
import difflib

# Common wrong guesses and the names they are probably meant for; only the hints whose target
# exists on the object are shown. A value may be a tuple of candidates (the first one that exists wins).
ATTRIBUTE_HINTS = {
    'qvector': 'qv', 'q_vector': 'qv', 'qvec': 'qv', 'qvalues': 'qv', 'q': 'qv',
    'wavelength': 'wv', 'wavelengths': 'wv',
    'frame': 'jv', 'frames': 'jv', 'frame_numbers': 'jv',
    'matrix': 'M', 'intensity': 'M', 'intensities': 'M', 'error': 'E', 'errors': 'E',
    'n_components': 'num_components', 'ncomponents': 'num_components', 'num_comps': 'num_components',
    'indices': 'frames', 'index': 'frames', 'rg': ('rgs', 'compute_rg'), 'rgvalue': 'rgs', 'i0': 'i0s',
    # components (molass-library#385)
    'get_rg': 'compute_rg', 'getrg': 'compute_rg', 'rg_value': 'compute_rg', 'radius_of_gyration': 'compute_rg',
    'guinier': 'get_guinier_object', 'get_guinier': 'get_guinier_object',
    'get_peak_top_x': 'peak_index', 'peak_position': 'peak_index', 'peak_frame': 'peak_index',
    'peak_top': 'peak_index', 'peak_x': 'peak_index',
    'mass': 'get_volume_mass', 'get_mass': 'get_volume_mass', 'kda': 'get_volume_mass',
}


def suggest_names(obj, name, limit=3):
    """Names of ``obj`` close to ``name``: known hints first, then spelling matches."""
    public = [n for n in dir(obj) if not n.startswith('_')]
    suggestions = []
    hint = ATTRIBUTE_HINTS.get(name.lower())
    for candidate in (hint,) if isinstance(hint, str) else (hint or ()):
        if candidate in public:
            suggestions.append(candidate)
            break
    for n in difflib.get_close_matches(name, public, n=limit, cutoff=0.6):
        if n not in suggestions:
            suggestions.append(n)
    return suggestions[:limit]


class DidYouMeanMixin:
    """For an unknown public attribute, raise an AttributeError that lists close names and aliases."""

    def __getattr__(self, name):
        # only reached when the normal lookup failed
        if name.startswith('_'):
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
        if hasattr(type(self), name):
            # an AttributeError raised inside a property: show the original one
            return object.__getattribute__(self, name)
        message = f"{type(self).__name__!r} object has no attribute {name!r}."
        suggestions = suggest_names(self, name)
        if suggestions:
            message += " Did you mean: " + ", ".join(repr(s) for s in suggestions) + "?"
        exc = AttributeError(message)
        exc.name, exc.obj = name, self
        raise exc
