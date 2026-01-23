# AI-Friendly Coding Principles

**Purpose**: Practical guidelines for writing code that AI assistants (and humans) can easily understand, use, and maintain.

**Status**: Living document - Updated as we learn from implementation

---

## Core Philosophy

**AI-friendly code means:**
1. Self-documenting API design (intuitive names, clear structure)
2. Helpful error messages that guide toward solutions
3. Examples embedded where needed (docstrings, not just tutorials)
4. Anticipation of common mistakes with proactive guidance

---

## 1. API Design Principles

### ✅ DO: Explicit Over Implicit

```python
# GOOD: Clear, self-documenting
xr_data.get_q_vector()  # Returns q-vector matching xr_data.M shape
xr_data.get_wavelength_vector()  # Returns wavelength vector

# AVOID: Abbreviations requiring domain knowledge
xr_data.sv  # What is 'sv'? Singular value? Spectral vector?
xr_data.qv  # Not obvious without documentation
```

### ✅ DO: Provide Property Shortcuts for Common Operations

```python
# GOOD: Common operations as properties
@property
def q_vector(self):
    """Q-vector corresponding to columns of M.
    
    Example:
        >>> ssd = SecSaxsData(SAMPLE1)
        >>> q = ssd.xr.q_vector  # Shape matches ssd.xr.M.shape[1]
        >>> plt.plot(q, ssd.xr.M[0])
    """
    return self.get_spectral_vectors()[0]
```

### ✅ DO: Method Names Should Reveal Intent

```python
# GOOD
data.calculate_signal_to_noise_ratio()
data.apply_baseline_correction()
model.fit_elution_curve()

# AVOID
data.calc_snr()  # Abbreviations unclear
data.proc()  # What does it process?
model.fit()  # Fit what to what?
```

### ✅ DO: Helpful Error Messages

```python
# GOOD: Guide the user
def __getattr__(self, name):
    if name in ['sv', 'qv', 'q']:
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'. "
            f"Did you mean: xr.q_vector (property) or "
            f"get_spectral_vectors()[0] (method)?"
        )
    raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

# AVOID: Bare error
def __getattr__(self, name):
    raise AttributeError(f"No attribute '{name}'")
```

---

## 2. Documentation Standards

### ✅ DO: Every Public Method Must Have Usage Example

```python
def get_spectral_vectors(self):
    """Return spectral vectors for XR and UV data.
    
    Returns:
        list: [xr_q_vector, uv_wavelength_vector]
              - xr_q_vector: Q-values (Å⁻¹) matching xr.M columns
              - uv_wavelength_vector: Wavelengths (nm) matching uv.M columns
    
    Examples:
        >>> from molass_data import SAMPLE1
        >>> from molass.DataObjects import SecSaxsData as SSD
        >>> ssd = SSD(SAMPLE1)
        >>> spectral_vecs = ssd.get_spectral_vectors()
        >>> xr_q = spectral_vecs[0]  # Q-vector for SAXS data
        >>> print(f"Q-range: {xr_q.min():.3f} to {xr_q.max():.3f} Å⁻¹")
        
        >>> # Use with intensity matrix
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(xr_q, ssd.xr.M[100])  # Plot frame 100
        >>> plt.xlabel('Q (Å⁻¹)')
        >>> plt.ylabel('Intensity')
    
    Note:
        Vector lengths match the number of columns in xr.M and uv.M
        respectively. If data trimming or binning was applied, vectors
        reflect the current state.
    """
```

### ✅ DO: Document Common Gotchas

```python
class XrData:
    """SAXS (X-ray) data container.
    
    Attributes:
        M : ndarray, shape (n_frames, n_q_points)
            Intensity matrix. Each row is a SAXS spectrum at one frame.
    
    Common Operations:
        # Access intensity matrix
        >>> intensities = xr_data.M
        
        # Get corresponding q-vector
        >>> q_vector = ssd.get_spectral_vectors()[0]
        
        # Plot single frame
        >>> plt.plot(q_vector, xr_data.M[0])
    
    ⚠️ Common Pitfall:
        The q-vector is accessed through the parent SecSaxsData object,
        not directly from XrData. This is because q-values may be shared
        across multiple data objects.
    """
```

### ✅ DO: Keep Examples Copy-Paste Ready

```python
# GOOD: Works without modification
>>> from molass_data import SAMPLE1
>>> from molass.DataObjects import SecSaxsData
>>> ssd = SecSaxsData(SAMPLE1)
>>> print(ssd.xr.M.shape)

# AVOID: Requires user to figure out imports/setup
>>> print(data.shape)  # What is 'data'? How do I get it?
```

---

## 3. Tutorial Requirements

Every tutorial should include these **AI-friendly elements**:

### ✅ "Hello World" Example in First Cell
```python
# Minimal working code that does something useful
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData

ssd = SecSaxsData(SAMPLE1)
print(f"Loaded {ssd.xr.M.shape[0]} frames with {ssd.xr.M.shape[1]} q-points")
```

### ✅ Common Operations Checklist
- ☑ Load data
- ☑ Access intensity matrix
- ☑ Get q-vectors
- ☑ Calculate SNR
- ☑ Apply baseline correction
- ☑ Perform decomposition

### ✅ Explicit Data Access Patterns
```python
# All ways to access key data
ssd.xr.M           # Intensity matrix (frames × q-points)
ssd.xr.q_vector    # Q-values (Å⁻¹)
ssd.uv.M           # UV absorbance matrix
ssd.uv.wavelength_vector  # Wavelengths (nm)
```

### ✅ Error Recovery Examples
```python
# Show common mistakes and how to fix them
# ❌ WRONG
try:
    q = xr_data.sv
except AttributeError:
    # ✅ CORRECT
    q = ssd.xr.q_vector
```

---

## 4. Quick Reference Checklists

### When Adding a New Public Method

- [ ] Method name clearly describes what it does
- [ ] Docstring includes Returns section
- [ ] Docstring has at least one usage example
- [ ] Example is copy-paste ready (includes imports)
- [ ] Common pitfalls documented if any
- [ ] Error messages guide toward solution

### When Adding a New Class

- [ ] Class docstring describes purpose
- [ ] Common operations listed in class docstring
- [ ] Properties provided for frequent attribute access
- [ ] `__repr__` method shows useful information

### When Designing an API

- [ ] Can a new user guess the method name?
- [ ] Are abbreviations necessary? (usually NO)
- [ ] Is there a property shortcut for common operations?
- [ ] Will error messages help or frustrate?

---

## 5. Verification: The AI Learning Test

**Quick Test**: Ask yourself:
> "Could an AI assistant complete this task on first attempt with only docstrings?"

**Standard Tasks**:
1. Load sample data → Should succeed immediately
2. Plot elution profile → Should succeed with 1-2 attempts
3. Access q-vector → Should succeed with 1-2 attempts
4. Calculate SNR → Should succeed with 2-3 attempts

If any task fails consistently, the API needs improvement.

---

## 6. Common Patterns to Follow

### Pattern: Property for Common Data Access
```python
@property
def q_vector(self):
    """Q-values (Å⁻¹) corresponding to columns of M."""
    return self._get_q_vector_internal()
```

### Pattern: Helpful __getattr__ for Common Mistakes
```python
def __getattr__(self, name):
    suggestions = {
        'sv': 'q_vector',
        'qv': 'q_vector', 
        'q': 'q_vector'
    }
    if name in suggestions:
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'. "
            f"Did you mean: {suggestions[name]}?"
        )
    raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
```

### Pattern: Descriptive Exceptions
```python
# GOOD
if len(q_vector) != matrix.shape[1]:
    raise ValueError(
        f"Q-vector length ({len(q_vector)}) does not match "
        f"matrix columns ({matrix.shape[1]}). "
        f"This usually happens after data trimming. "
        f"Regenerate q-vector with get_spectral_vectors()."
    )

# AVOID
if len(q_vector) != matrix.shape[1]:
    raise ValueError("Dimension mismatch")
```

---

## 7. Anti-Patterns to Avoid

### ❌ DON'T: Cryptic Abbreviations
```python
# BAD
def calc_rg_gp(self, q, I):
    """Calculate Rg from GP."""
    pass

# GOOD
def calculate_radius_of_gyration_guinier(self, q_values, intensities):
    """Calculate radius of gyration using Guinier plot."""
    pass
```

### ❌ DON'T: Silent Failures
```python
# BAD
def process(self, data):
    try:
        return self._complex_operation(data)
    except:
        return None  # User has no idea what went wrong

# GOOD
def process(self, data):
    try:
        return self._complex_operation(data)
    except ValueError as e:
        raise ValueError(
            f"Processing failed: {e}. "
            f"Check that data shape is (n_frames, n_q_points)."
        ) from e
```

### ❌ DON'T: Examples Without Context
```python
# BAD - docstring example
"""
Examples:
    >>> plot(data)  # What is 'data'? Where does it come from?
"""

# GOOD
"""
Examples:
    >>> from molass_data import SAMPLE1
    >>> from molass.DataObjects import SecSaxsData
    >>> ssd = SecSaxsData(SAMPLE1)
    >>> ssd.plot_elution_profile()
"""
```

---

## 8. Implementation Priority

When improving AI-readiness, tackle in this order:

**Priority 1: Critical Usability** (Do first)
- Add property shortcuts for most common operations
- Fix cryptic error messages
- Add usage examples to top 10 most-used methods

**Priority 2: Documentation Enhancement** (Do second)
- Complete docstring examples for all public methods
- Create "Common Operations" tutorial section
- Document known gotchas in class docstrings

**Priority 3: Systematic Testing** (Do third)
- Run AI Learning Tests on standard tasks
- Track success metrics
- Iterate based on findings

---

## 9. Success Metrics

**Qualitative Indicators:**
- New contributors can get started with AI help alone
- Fewer "how do I..." questions in forums
- AI assistants successfully auto-complete common tasks

**Quantitative Targets:**
- 90%+ of public methods have usage examples
- Standard tasks complete in ≤2 AI attempts
- <15% of tasks require workarounds

---

## 10. Evolution of This Document

This is a **living document**. As we implement and learn:

- ✅ Add new patterns discovered during development
- ✅ Record lessons learned from real AI interactions
- ✅ Update anti-patterns when we find them
- ✅ Refine guidelines based on usability testing

**To propose updates**: Discuss with the team and document the rationale.

---

## Attribution

Based on empirical testing with AI assistants (Claude 3.5 Sonnet, GitHub Copilot) and the comprehensive framework document `AI_assisted_maintenance_framework.md` (Jan 2026).

---

## Quick Summary Card

**For immediate reference when coding:**

1. **Names**: Explicit > Implicit
2. **Properties**: Add shortcuts for common operations
3. **Errors**: Guide toward solutions
4. **Examples**: Copy-paste ready in every docstring
5. **Test**: "Could AI do this on first try?"
