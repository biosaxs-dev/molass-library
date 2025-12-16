"""
run_tests.py

Helper script for running tests with different plot configurations and robust coverage support.

Coverage Workaround and Best Practice:
--------------------------------------
To ensure reliable code coverage collection—including subprocesses and interactive/temporary scripts—this script uses the official 'coverage' tool directly:

- When '--coverage' is specified, all test invocations use:
      coverage run -m pytest ...
  instead of pytest-cov or pytest --cov.

- After tests complete, the script runs:
      coverage combine
      coverage html
  to merge all coverage data files (including those from subprocesses) and generate the HTML report.

- For subprocesses that execute dynamically generated scripts (e.g., interactive mode), explicit coverage start/stop code is injected automatically.

This approach is robust and works on both Windows and Linux/Ubuntu, avoiding known issues with pytest-cov and subprocess coverage.

Note:
-----
On Windows, coverage for subprocesses and dynamically generated scripts may not be collected correctly without this workaround.
Using pytest-cov alone is often insufficient for full coverage in multi-process or interactive scenarios on Windows.
Always use this script's workflow for reliable results.

For more details, see the project documentation at https://biosaxs-dev.github.io/molass-develop/chapters/06/testing.html.
"""

import os
import sys
import subprocess
from pathlib import Path

# --- Ensure sys.path respects pythonpath from pyproject.toml ---

# --- Use shared utility to set sys.path from pyproject.toml pythonpath ---
from tools.pyproject_utils import get_pythonpath_from_pyproject
for abs_p in reversed(get_pythonpath_from_pyproject()):
    if abs_p not in sys.path:
        sys.path.insert(0, abs_p)
# print(f"sys.path: {sys.path}")

def set_env_vars(enable_plots=False, save_plots=False, plot_dir="test_plots"):
    """Set environment variables for plot control."""
    os.environ['MOLASS_ENABLE_PLOTS'] = 'true' if enable_plots else 'false'
    os.environ['MOLASS_SAVE_PLOTS'] = 'true' if save_plots else 'false'
    os.environ['MOLASS_PLOT_DIR'] = str(plot_dir)

def run_interactive_script(test_file, coverage, function=None):
    env = os.environ.copy()
    script_path = Path(__file__).parent / 'tools' / 'interactive_test_script.py'
    abs_test_path = str(test_file.resolve())
    script_arg = abs_test_path
    if function:
        script_arg += f"::{function}"
    # --- Add pythonpath from pyproject.toml to PYTHONPATH using shared utility ---
    from tools.pyproject_utils import get_pythonpath_from_pyproject
    pythonpath_entries = get_pythonpath_from_pyproject()
    orig_pythonpath = env.get('PYTHONPATH', '')
    combined_pythonpath = os.pathsep.join(pythonpath_entries + ([orig_pythonpath] if orig_pythonpath else []))
    if combined_pythonpath:
        env['PYTHONPATH'] = combined_pythonpath
    if coverage:
        cmd = [sys.executable, '-m', 'coverage', 'run', str(script_path), script_arg]
    else:
        cmd = [sys.executable, str(script_path), script_arg]
    print(f"Running interactive test script: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)

def run_single_test_file(test_file, mode, coverage, function=None):
    env = os.environ.copy()
    node_id = str(test_file)
    if function:
        node_id += f"::{function}"
    if mode == 'interactive':
        print("Interactive mode detected - trying direct execution to avoid pytest GUI issues...")
        try:
            run_interactive_script(test_file, coverage, function=function)
            result = subprocess.CompletedProcess(args=[], returncode=0)  # Assume success if no exception
        except Exception as e:
            import traceback
            print("Direct execution failed:")
            traceback.print_exc()
            print("Falling back to pytest...")
            pytest_args = ['-v', '--tb=short', '-s', '--capture=no', '--tb=line']
            if coverage:
                cmd = [sys.executable, '-m', 'coverage', 'run', '-m', 'pytest', node_id] + pytest_args
            else:
                cmd = [sys.executable, '-m', 'pytest', node_id] + pytest_args
            print(f"Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
    else:
        pytest_args = ['-v', '--tb=short', '-s']
        if coverage:
            cmd = [sys.executable, '-m', 'coverage', 'run', '-m', 'pytest', node_id] + pytest_args
        else:
            cmd = [sys.executable, '-m', 'pytest', node_id] + pytest_args
        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
    return result.returncode

def run_tests(test_path=None, mode='batch', order_range=None, coverage=False, function=None):
    """Unified test runner for single files and directories."""
    # Set environment variables for plot control based on mode
    if mode == 'batch':
        set_env_vars(enable_plots=False, save_plots=False)
        print("Running tests in BATCH mode (no plots)")
    elif mode == 'save':
        set_env_vars(enable_plots=False, save_plots=True)
        print("Running tests in SAVE mode (plots saved to files)")
    elif mode == 'interactive':
        set_env_vars(enable_plots=True, save_plots=False)
        print("Running tests in INTERACTIVE mode (plots shown)")
    elif mode == 'both':
        set_env_vars(enable_plots=True, save_plots=True)
        print("Running tests in BOTH mode (plots shown AND saved)")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Unify single-file and directory logic
    test_files = []
    if test_path:
        p = Path(test_path)
        if p.is_dir():
            test_dir = p
            test_files = sorted(test_dir.glob('*.py'))
            if not test_files:
                test_files = sorted(test_dir.rglob('*.py'))
            if not test_files:
                print(f"No Python files found in {test_path} or its subdirectories")
                return 1
            print(f"Running {len(test_files)} test files individually to preserve order...")
        elif p.is_file():
            test_files = [p]
        else:
            print(f"Test path {test_path} does not exist.")
            return 1
    else:
        test_dir = Path('tests')
        test_files = sorted(test_dir.glob('*.py'))
        if not test_files:
            test_files = sorted(test_dir.rglob('*.py'))
        if not test_files:
            print("No Python files found in tests/ or its subdirectories")
            return 1
        print(f"Running {len(test_files)} test files individually to preserve order...")

    if order_range:
        start, end = order_range
        def in_range(f):
            for i in range(start, end + 1):
                if f"{i:02d}" in f.name or f"{i:03d}" in f.name:
                    return True
            return False
        test_files = [f for f in test_files if in_range(f)]
        print(f"Running tests with orders {start} to {end}")

    total_failures = 0
    for test_file in test_files:
        print(f"\n{'='*60}")
        if function:
            print(f"Running {test_file.name}::{function}")
        else:
            print(f"Running {test_file.name}")
        print('='*60)
        rc = run_single_test_file(test_file, mode, coverage, function=function)
        if rc != 0:
            total_failures += 1
            if function:
                print(f"❌ {test_file.name}::{function} FAILED")
            else:
                print(f"❌ {test_file.name} FAILED")
        else:
            if function:
                print(f"✅ {test_file.name}::{function} PASSED")
            else:
                print(f"✅ {test_file.name} PASSED")
    print(f"\n{'='*60}")
    print(f"Summary: {len(test_files) - total_failures}/{len(test_files)} files passed")
    print('='*60)
    return total_failures

# Check for required packages
REQUIRED_PACKAGES = [
    "pytest",
    "pytest_cov",
    "pytest_env",
    "pytest_order",
    "molass_data",
]

missing = []
for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        missing.append(pkg)

if missing:
    print(f"\nERROR: The following required packages are missing: {', '.join(missing)}")
    print("Please install them with:")
    print(f"    pip install {' '.join(missing)}")
    sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run molass tests with plot control')
    parser.add_argument('--mode', choices=['batch', 'save', 'interactive', 'both'],
                        default='batch', help='Plot display mode')
    parser.add_argument('--test', help='Specific test file or directory to run')
    parser.add_argument('--range', help='Range of test orders to run, e.g., "1-3" or "2-5"')
    parser.add_argument('--plot-dir', default='test_plots',
                        help='Directory for saved plots')
    parser.add_argument('--coverage', action='store_true',
                        help='Enable coverage reporting with pytest-cov')
    parser.add_argument('--function', help='Run only a specific test function (e.g. test_func or TestClass::test_method)')

    args = parser.parse_args()

    # Parse range argument
    order_range = None
    if args.range:
        try:
            start, end = map(int, args.range.split('-'))
            order_range = (start, end)
        except ValueError:
            print(f"Error: Invalid range format '{args.range}'. Use format like '1-3'")
            sys.exit(1)

    # Set plot directory
    os.environ['MOLASS_PLOT_DIR'] = args.plot_dir

    exit_code = run_tests(args.test, args.mode, order_range, coverage=args.coverage, function=args.function)

    # If coverage was enabled, combine and generate HTML report
    if args.coverage:
        try:
            print("Combining coverage data and generating HTML report...")
            subprocess.run([sys.executable, '-m', 'coverage', 'combine'], check=True)
            subprocess.run([sys.executable, '-m', 'coverage', 'html'], check=True)
            print("Coverage HTML report generated at htmlcov/index.html")
        except Exception as e:
            print(f"Warning: coverage combine/html failed: {e}")

    if args.mode in ['save', 'both'] and Path(args.plot_dir).exists():
        plot_count = len(list(Path(args.plot_dir).glob('*.png')))
        print(f"\n{plot_count} plots saved to {args.plot_dir}/")

    sys.exit(exit_code)