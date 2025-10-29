import os
import sys
import importlib.util
import inspect
sys.path.insert(0, '.')

# Set environment variables
os.environ['MOLASS_ENABLE_PLOTS'] = r'{MOLASS_ENABLE_PLOTS}'
os.environ['MOLASS_SAVE_PLOTS'] = r'{MOLASS_SAVE_PLOTS}'
os.environ['MOLASS_PLOT_DIR'] = r'{MOLASS_PLOT_DIR}'

# Import the test module
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
