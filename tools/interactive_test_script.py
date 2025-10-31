
import os
import sys
import importlib.util
# --- Prepend pythonpath from PYTHONPATH env if set, or from pyproject.toml ---
from tools.pyproject_utils import get_pythonpath_from_pyproject
pythonpath_env = os.environ.get('PYTHONPATH', '')
if pythonpath_env:
    for p in reversed(pythonpath_env.split(os.pathsep)):
        if p and p not in sys.path:
            sys.path.insert(0, p)
else:
    # Fallback: use pyproject.toml if present (for direct runs)
    for abs_p in reversed(get_pythonpath_from_pyproject()):
        if abs_p not in sys.path:
            sys.path.insert(0, abs_p)
sys.path.insert(0, '.')     # Ensure current directory is in sys.path


# Support node id: test_file.py::test_func
if len(sys.argv) < 2:
    print("Usage: python interactive_test_script.py <test_file.py>[::test_func]")
    sys.exit(1)

node_id = sys.argv[1]
if '::' in node_id:
    file_part, func_part = node_id.split('::', 1)
else:
    file_part, func_part = node_id, None
abs_test_path = os.path.abspath(file_part)

# Set environment variables (optional: could be passed from parent)
os.environ.setdefault('MOLASS_ENABLE_PLOTS', 'true')
os.environ.setdefault('MOLASS_SAVE_PLOTS', 'false')
os.environ.setdefault('MOLASS_PLOT_DIR', 'test_plots')

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"Test file path: {abs_test_path}")
print(f"Test file exists: {os.path.exists(abs_test_path)}")

try:
    spec = importlib.util.spec_from_file_location("test_module", abs_test_path)
    test_module = importlib.util.module_from_spec(spec)
    print(f"Module spec created successfully")
    spec.loader.exec_module(test_module)
    print(f"Module loaded successfully")
except Exception as e:
    print(f"Error loading module: {e}")
    import traceback
    traceback.print_exc()
    test_module = None


# Find all test functions (including decorated ones)
test_functions = []
if test_module:
    print(f"Module attributes: {[name for name in dir(test_module) if not name.startswith('__')]}")
    for name in dir(test_module):
        obj = getattr(test_module, name)
        if name.startswith('test_') and callable(obj):
            test_functions.append((name, obj))
            print(f"Found test function: {name}")
else:
    print("No test module loaded, cannot find test functions")

# Sort test functions by name for predictable order
test_functions.sort(key=lambda x: x[0])

if func_part:
    # Only run the specified function (exact match)
    selected = [(name, func) for name, func in test_functions if name == func_part]
    if not selected:
        print(f"No test function named '{func_part}' found in module.")
    else:
        print(f"Running only test function: {func_part}")
    test_functions = selected

print(f"Found {len(test_functions)} test functions: {[name for name, func in test_functions]}")

# Run each test function
for test_name, test_func in test_functions:
    print(f"\nRunning {test_name}...")
    try:
        test_func()
        print(f"✅ {test_name} PASSED")
    except Exception as e:
        print(f"❌ {test_name} FAILED: {e}")
        import traceback
        traceback.print_exc()

print("\nAll test functions completed.")

# Show plots if interactive mode is enabled and matplotlib.pyplot is imported
if os.environ.get('MOLASS_ENABLE_PLOTS', 'false').lower() == 'true':
    print("[DEBUG] Entering plot display block at end of script.")
    try:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        fignums = plt.get_fignums()
        print(f"[DEBUG] Number of open figures: {len(fignums)}; Figure numbers: {fignums}")
        print("Calling plt.show() to display plots (interactive mode)...")
        plt.show()
    except ImportError:
        print("matplotlib is not installed; skipping plt.show()")
    except Exception as e:
        print(f"Error calling plt.show(): {e}")
