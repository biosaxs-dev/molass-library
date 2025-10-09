"""
run_tests.py
Helper script for running tests with different plot configurations.
This script was suggested by Copilot to simplify test execution.
"""
import os
import sys
import subprocess
from pathlib import Path

def set_env_vars(enable_plots=False, save_plots=False, plot_dir="test_plots"):
    """Set environment variables for plot control."""
    os.environ['MOLASS_ENABLE_PLOTS'] = 'true' if enable_plots else 'false'
    os.environ['MOLASS_SAVE_PLOTS'] = 'true' if save_plots else 'false'
    os.environ['MOLASS_PLOT_DIR'] = str(plot_dir)

def run_tests(test_path=None, mode='batch', order_range=None):
    """
    Run tests with specified plot mode.
    
    Parameters
    ----------
    test_path : str, optional
        Specific test file or directory to run
    mode : str
        'batch' - No plots shown, no plots saved (fastest for CI/CD)
        'save' - No plots shown, plots saved to files (good for debugging)  
        'interactive' - Plots shown interactively (for manual inspection)
        'both' - Plots shown AND saved (for thorough testing)
    order_range : tuple, optional
        Range of test orders to run, e.g., (1, 3) runs orders 1, 2, 3
    """
    
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
    
    # Handle directory vs file differently to preserve order
    if test_path and Path(test_path).is_dir():
        # For directories, run each file individually to preserve order within files
        test_dir = Path(test_path)
        # First try direct .py files, then recursive search
        test_files = sorted(test_dir.glob('*.py'))
        
        if not test_files:
            # No direct .py files, look recursively
            test_files = sorted(test_dir.rglob('*.py'))
            
        if not test_files:
            print(f"No Python files found in {test_path} or its subdirectories")
            return 1
            
        print(f"Running {len(test_files)} test files individually to preserve order...")
        total_failures = 0
        
        for test_file in test_files:
            print(f"\n{'='*60}")
            print(f"Running {test_file.name}")
            print('='*60)
            
            pytest_args = ['-v', '--tb=short', '-s']
            if mode == 'interactive':
                pytest_args.extend(['--capture=no', '--tb=line'])
            
            cmd = [sys.executable, '-m', 'pytest', str(test_file)] + pytest_args
            print(f"Command: {' '.join(cmd)}")
            env = os.environ.copy()  # Copy current environment
            result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
            
            if result.returncode != 0:
                total_failures += 1
                print(f"❌ {test_file.name} FAILED")
            else:
                print(f"✅ {test_file.name} PASSED")
        
        print(f"\n{'='*60}")
        print(f"Summary: {len(test_files) - total_failures}/{len(test_files)} files passed")
        print('='*60)
        return total_failures
    else:
        # For single files or default, run normally
        cmd = [sys.executable, '-m', 'pytest']
        
        if test_path:
            cmd.append(test_path)
        else:
            cmd.extend(['tests/'])
        
        # Add order range filtering if specified
        if order_range:
            start, end = order_range
            test_patterns = []
            for i in range(start, end + 1):
                test_patterns.append(f"test_{i:03d}")
            # Use pytest's -k option with 'and' logic for partial matching
            k_expression = ' or '.join([f"'{pattern}' in test_name" for pattern in test_patterns])
            # Simpler approach: just use the test name prefixes
            k_expression = ' or '.join(test_patterns)
            cmd.extend(['-k', k_expression])
            print(f"Running tests with orders {start} to {end}")
        
        # Add useful pytest options
        pytest_args = ['-v', '--tb=short', '-s']  # -s shows print output
        
        # For interactive mode, add additional options to help with GUI display
        if mode == 'interactive':
            pytest_args.extend(['--capture=no', '--tb=line'])
            
            # Special handling for single file interactive mode to avoid pytest issues
            if test_path and Path(test_path).is_file():
                print("Interactive mode detected - trying direct execution to avoid pytest GUI issues...")
                try:
                    # Set up the environment 
                    env = os.environ.copy()
                    
                    # Use absolute path to avoid path issues
                    abs_test_path = str(Path(test_path).resolve())
                    
                    # Create a temporary script to avoid string escaping issues
                    temp_script = f"""
import os
import sys
sys.path.insert(0, '.')

# Set environment variables
os.environ['MOLASS_ENABLE_PLOTS'] = r'{env.get("MOLASS_ENABLE_PLOTS", "false")}'
os.environ['MOLASS_SAVE_PLOTS'] = r'{env.get("MOLASS_SAVE_PLOTS", "false")}'
os.environ['MOLASS_PLOT_DIR'] = r'{env.get("MOLASS_PLOT_DIR", "test_plots")}'

# Import and execute the test
with open(r'{abs_test_path}', 'r', encoding='utf-8') as f:
    exec(f.read())
"""
                    
                    # Write to a temporary file to avoid command line escaping issues
                    temp_file = Path("temp_interactive_test.py")
                    temp_file.write_text(temp_script, encoding='utf-8')
                    
                    try:
                        exec_cmd = [sys.executable, str(temp_file)]
                        print("Running test directly for better interactive display...")
                        result = subprocess.run(exec_cmd, cwd=Path(__file__).parent)
                        return result.returncode
                    finally:
                        # Clean up temp file
                        if temp_file.exists():
                            temp_file.unlink()
                    
                except Exception as e:
                    print(f"Direct execution failed: {e}, falling back to pytest...")
        
        cmd.extend(pytest_args)
        
        # Run the tests with environment variables passed through
        print(f"Command: {' '.join(cmd)}")
        env = os.environ.copy()  # Copy current environment
        result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
        return result.returncode

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run molass tests with plot control')
    parser.add_argument('--mode', choices=['batch', 'save', 'interactive', 'both'], 
                       default='batch', help='Plot display mode')
    parser.add_argument('--test', help='Specific test file or directory to run')
    parser.add_argument('--range', help='Range of test orders to run, e.g., "1-3" or "2-5"')
    parser.add_argument('--plot-dir', default='test_plots', 
                       help='Directory for saved plots')
    
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
    
    exit_code = run_tests(args.test, args.mode, order_range)
    
    if args.mode in ['save', 'both'] and Path(args.plot_dir).exists():
        plot_count = len(list(Path(args.plot_dir).glob('*.png')))
        print(f"\n{plot_count} plots saved to {args.plot_dir}/")
    
    sys.exit(exit_code)