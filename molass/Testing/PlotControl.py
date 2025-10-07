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
        self.enable_plots = os.getenv('MOLASS_ENABLE_PLOTS', 'false').lower() == 'true'
        self.save_plots = os.getenv('MOLASS_SAVE_PLOTS', 'false').lower() == 'true'
        self.plot_dir = Path(os.getenv('MOLASS_PLOT_DIR', 'test_plots'))
        self.plot_format = os.getenv('MOLASS_PLOT_FORMAT', 'png')
        
        # Configure matplotlib backend
        if not self.enable_plots:
            matplotlib.use('Agg')  # Non-interactive backend
            
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
        if self.enable_plots:
            plt.show()
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
        return self.enable_plots
    
    def configure_for_test(self, test_func):
        """
        Decorator to configure a test function for plot control.
        
        Usage:
        @plot_controller.configure_for_test
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

# Global instance
plot_controller = PlotController()

# Convenience functions
def show_or_save(test_name=None, fig=None):
    """Convenience function to show or save plot."""
    plot_controller.show_or_save(test_name, fig)

def is_interactive():
    """Returns True if plots should be shown interactively."""
    return plot_controller.is_interactive()

def configure_for_test(test_func):
    """Decorator for test functions with plots."""
    return plot_controller.configure_for_test(test_func)