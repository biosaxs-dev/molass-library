"""
Testing.PlotControl.py
Utility for controlling matplotlib plots in automated testing.
This module was suggested by Copilot to manage plot behavior during tests.
"""
import os
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path

class PlotController:
    """
    Controls matplotlib behavior for testing environments.
    
    Environment Variables:
    - MOLASS_ENABLE_PLOTS: 'true' to show plots interactively (default: 'false')
    - MOLASS_SAVE_PLOTS: 'true' to save plots to files (default: 'false')  
    - MOLASS_PLOT_DIR: directory for saved plots (default: 'test_plots')
    - MOLASS_PLOT_FORMAT: format for saved plots (default: 'png')
    """
    
    def __init__(self):
        self._backend_configured = False
        self._refresh_config()
    
    def _refresh_config(self):
        """Refresh configuration from environment variables."""
        old_enable_plots = getattr(self, 'enable_plots', None)
        self.enable_plots = os.getenv('MOLASS_ENABLE_PLOTS', 'false').lower() == 'true'
        self.save_plots = os.getenv('MOLASS_SAVE_PLOTS', 'false').lower() == 'true'
        self.plot_dir = Path(os.getenv('MOLASS_PLOT_DIR', 'test_plots'))
        self.plot_format = os.getenv('MOLASS_PLOT_FORMAT', 'png')
        
        # Force matplotlib backend reconfiguration if enable_plots changed
        if old_enable_plots != self.enable_plots:
            self._backend_configured = False
        
        # Configure matplotlib backend
        if not self._backend_configured:
            if not self.enable_plots:
                matplotlib.use('Agg')  # Non-interactive backend
            else:
                # For interactive mode, ensure we have a GUI backend
                try:
                    # Force matplotlib to use an interactive backend
                    matplotlib.use('TkAgg', force=True)
                except ImportError:
                    try:
                        matplotlib.use('Qt5Agg', force=True)
                    except ImportError:
                        try:
                            matplotlib.use('module://matplotlib_inline.backend_inline', force=True)
                        except ImportError:
                            print("WARNING: No interactive backend available, plots may not display")
            
            self._backend_configured = True
            
        # Create plot directory if saving plots
        if self.save_plots:
            self.plot_dir.mkdir(parents=True, exist_ok=True)
    
    def show_or_save(self, test_name=None, fig=None):
        """
        Show plot interactively or save to file based on configuration.
        
        Parameters
        ----------
        test_name : str, optional
            Name for the saved plot file
        fig : matplotlib.figure.Figure, optional
            Figure to save (uses current figure if None)
        """
        # Refresh config in case environment changed
        self._refresh_config()
        
        if self.enable_plots:
            print(f"Interactive mode: showing plot (backend: {matplotlib.get_backend()})")
            
            # Get the figure
            fig = plt.gcf() if fig is None else fig
            
            # Show the plot
            plt.show(block=False)
            
            # Keep the plot visible longer for interactive viewing
            plt.pause(2.0)  # 2 second pause to ensure visibility
            
            # In interactive mode, don't auto-close - let user see the plot
            print(f"Plot window should be visible. Backend: {matplotlib.get_backend()}")
            print("Plot will remain open until test completes or you close it manually.")
        elif self.save_plots and test_name:
            if fig is None:
                fig = plt.gcf()
            filename = self.plot_dir / f"{test_name}.{self.plot_format}"
            fig.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"Plot saved: {filename}")
        
        # Always close the figure in batch mode to free memory
        if not self.enable_plots:
            if fig is None:
                plt.close()
            else:
                plt.close(fig)
    
    def is_interactive(self):
        """Returns True if plots should be shown interactively."""
        self._refresh_config()
        return self.enable_plots
    
    def control_matplotlib_plot(self, test_func):
        """
        Decorator to control matplotlib behavior for test functions.
        
        Usage:
        @plot_controller.control_matplotlib_plot
        def test_my_function():
            # Your test code with plots
            plt.plot([1, 2, 3])
            plot_controller.show_or_save("test_my_function")
        """
        def wrapper(*args, **kwargs):
            try:
                return test_func(*args, **kwargs)
            finally:
                # Ensure all figures are closed in batch mode
                if not self.enable_plots:
                    plt.close('all')
        return wrapper
    
    def suppress_numerical_warnings(self, test_func):
        """
        Decorator to suppress numerical computation warnings.
        
        Usage:
        @plot_controller.suppress_numerical_warnings
        def test_my_function():
            # Your test code that might generate numerical warnings
            pass
        """
        def wrapper(*args, **kwargs):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                warnings.simplefilter("ignore", DeprecationWarning)
                warnings.filterwarnings("ignore", message=".*non-interactive.*", category=UserWarning)
                # Suppress numerical computation warnings that are often expected in scientific computing
                warnings.filterwarnings("ignore", message=".*invalid value encountered.*", category=RuntimeWarning)
                warnings.filterwarnings("ignore", message=".*divide by zero.*", category=RuntimeWarning)
                warnings.filterwarnings("ignore", message=".*overflow encountered.*", category=RuntimeWarning)
                
                return test_func(*args, **kwargs)
        return wrapper

# Global instance
plot_controller = PlotController()

# Convenience functions
def show_or_save(test_name=None, fig=None):
    """Convenience function to show or save plot."""
    plot_controller.show_or_save(test_name, fig)

def is_interactive():
    """Returns True if plots should be shown interactively."""
    return plot_controller.is_interactive()

def control_matplotlib_plot(test_func):
    """Decorator for test functions with matplotlib plots."""
    return plot_controller.control_matplotlib_plot(test_func)

# Backward compatibility alias
def configure_for_test(test_func):
    """Deprecated: Use control_matplotlib_plot instead."""
    return plot_controller.control_matplotlib_plot(test_func)

def suppress_numerical_warnings(test_func):
    """Decorator to suppress numerical computation warnings."""
    return plot_controller.suppress_numerical_warnings(test_func)