"""
Reports.ReportRange.py
"""
import numpy as np

MINOR_COMPONENT_MAX_PROP = 0.2

def make_v1report_ranges_impl(decomposition, ssd, mapped_curve, area_ratio, debug=False):
    """
    Make V1 report ranges from the decomposition and mapped curve.

    molass_legacy scheme:

    molass library scheme:
        decomp_result = Backward.DecompResultAdapter.adapted_decomp_result(...)
    """
    if debug:
        from importlib import reload
        import molass.Backward.DecompResultAdapter
        reload(molass.Backward.DecompResultAdapter)
    from molass.Backward.DecompResultAdapter import adapted_decomp_result
    # task: concentration_datatype must have been be set before calling this function.

    decomp_result= adapted_decomp_result(decomposition, ssd, mapped_curve, debug=debug)

    elm_recs = decomp_result.opt_recs
    elm_recs_uv = decomp_result.opt_recs_uv

    components = decomposition.get_xr_components()
    # components = decomposition.get_uv_components()

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
        ret_ranges.append(comp.make_paired_range(range_, minor=minor, elm_recs=elm_recs_uv, debug=debug))

    if debug:
        from importlib import reload
        import molass_legacy.Decomposer.UnifiedDecompResultTest
        reload(molass_legacy.Decomposer.UnifiedDecompResultTest)
        from molass_legacy.Decomposer.UnifiedDecompResultTest import plot_decomp_results
        editor_ranges = []
        for prange in ret_ranges:
            editor_ranges.append(prange.get_fromto_list())
        plot_decomp_results([decomp_result], editor_ranges)

    return ret_ranges