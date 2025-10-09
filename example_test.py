"""
Example of updating an existing test to use plot control
"""
import os
from molass import get_version
get_version(toml_only=True)
from molass_data import SAMPLE1
from molass.Testing import show_or_save, control_matplotlib_plot, is_interactive

@control_matplotlib_plot
def test_010_default():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    corrected_copy.estimate_mapping()
    
    # Use is_interactive() to control debug parameter
    decomposition = corrected_copy.quick_decomposition()
    decomposition.plot_components(debug=is_interactive())
    
    # Debug output
    print(f"is_interactive(): {is_interactive()}")
    print(f"MOLASS_ENABLE_PLOTS: {os.environ.get('MOLASS_ENABLE_PLOTS', 'not set')}")
    
    # Create a simple test plot to verify interactive mode
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 6))
    plt.plot([1, 2, 3], [1, 4, 2], 'ro-', label='Test data')
    plt.title('Simple Test Plot')
    plt.legend()
    
    # If the plot_components method doesn't automatically handle show/save,
    # you can add this line:
    show_or_save("test_010_default")

if __name__ == "__main__":
    test_010_default()