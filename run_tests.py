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

def run_tests(test_path=None, mode='batch'):
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
    
    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.extend(['tests/'])
    
    # Add useful pytest options
    cmd.extend(['-v', '--tb=short'])
    
    # Run the tests
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run molass tests with plot control')
    parser.add_argument('--mode', choices=['batch', 'save', 'interactive', 'both'], 
                       default='batch', help='Plot display mode')
    parser.add_argument('--test', help='Specific test file or directory to run')
    parser.add_argument('--plot-dir', default='test_plots', 
                       help='Directory for saved plots')
    
    args = parser.parse_args()
    
    # Set plot directory
    os.environ['MOLASS_PLOT_DIR'] = args.plot_dir
    
    exit_code = run_tests(args.test, args.mode)
    
    if args.mode in ['save', 'both'] and Path(args.plot_dir).exists():
        plot_count = len(list(Path(args.plot_dir).glob('*.png')))
        print(f"\n{plot_count} plots saved to {args.plot_dir}/")
    
    sys.exit(exit_code)