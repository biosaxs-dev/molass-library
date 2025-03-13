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

    components = lr_info.get_components()

    ranges = []
    areas = []
    for comp in components:
        areas.append(comp.compute_xr_area())
        ranges.append(comp.compute_range(area_ratio))

    area_proportions = np.array(areas)/np.sum(areas)
    if debug:
        print("area_proportions=", area_proportions)

    ret_ranges = []
    for comp, range_, prop in zip(components, ranges, area_proportions):
        minor = prop < MINOR_COMPONENT_MAX_PROP
        ret_ranges.append(comp.make_paired_range(range_, minor=minor))

    return ret_ranges