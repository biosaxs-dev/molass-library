"""
Reports.ReportUtils.py

This module is used to make reports with _MOLASS.
It includes a wrapper to hide the Controller class.
"""
import numpy as np

MINOR_COMPONENT_MAX_PROP = 0.1

def make_v1report(ssd, *args, **kwargs):
    debug = kwargs.get('debug', False)
    if debug:
        import molass.Reports.Controller
        from importlib import reload
        reload(molass.Reports.Controller)
    from molass.Reports.Controller import Controller
    controller = Controller()
    controller.make_v1report(ssd, *args, **kwargs)

def make_v1report_ranges_impl(lr_info, area_ratio, debug=False):
    if debug:
        print("make_v1analysis_ranges_impl: area_ratio=", area_ratio)

    components = lr_info.get_xr_components()

    if debug:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        for comp in components:
            icurve = comp.get_icurve()
            ax.plot(icurve.x, icurve.y, label=f'Component {comp.peak_index}')
        ax.set_xlabel('Frames')
        ax.set_ylabel('Intensity')
        ax.set_title('Components Elution Curves')
        ax.legend()
        fig.tight_layout()
        plt.show()

    ranges = []
    areas = []
    for comp in components:
        areas.append(comp.compute_area())
        ranges.append(comp.compute_range(area_ratio))

    area_proportions = np.array(areas)/np.sum(areas)
    if debug:
        print("area_proportions=", area_proportions)

    ret_ranges = []
    for comp, range_, prop in zip(components, ranges, area_proportions):
        minor = prop < MINOR_COMPONENT_MAX_PROP
        ret_ranges.append(comp.make_paired_range(range_, minor=minor))

    return ret_ranges