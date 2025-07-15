"""
Reports.V1LrfReport.py

This module contains the functions to generate the reports for the LRF Analysis.
"""
from importlib import reload
from time import sleep

WRITE_TO_TEMPFILE = False

def make_lrf_report(punit, controller, ri, kwargs):
    """
    Make a report for the LRF Analysis.

    Migrated from molass_legacy.StageExtrapolation.control_extrapolation().
    """
    debug = kwargs.get('debug')
    if debug:
        import molass.Backward.SerialDataProxy
        reload(molass.Backward.SerialDataProxy)
        import molass.Backward.MappedInfoProxy
        reload(molass.Backward.MappedInfoProxy)
        import molass.Backward.PreviewParams
        reload(molass.Backward.PreviewParams)
        import molass_legacy.SerialAnalyzer.StageExtrapolation
        reload(molass_legacy.SerialAnalyzer.StageExtrapolation)
    from molass.Backward.SerialDataProxy import SerialDataProxy
    from molass.Backward.PreviewParams import make_preview_params
    from molass.Backward.MappedInfoProxy import make_mapped_info
    from molass_legacy.SerialAnalyzer.StageExtrapolation import prepare_extrapolation, do_extrapolation, clean_tempfolders
    from molass_legacy._MOLASS.SerialSettings import set_setting

    if len(ri.pairedranges) > 0:
        set_setting('conc_dependence', 1)           # used in ExtrapolationSolver.py
        set_setting('mapper_cd_color_info', ri.decomposition.get_cd_color_info())
        set_setting('concentration_datatype', 2)    # 0: XR model, 1: XR data, 2: UV model, 3: UV data

        controller.logger.info('Starting LRF report generation...')
        controller.ri = ri
        controller.applied_ranges = ri.pairedranges
        controller.qvector = ri.ssd.xr.qv
        sd = SerialDataProxy(ri.ssd, debug=debug)
        controller.serial_data = sd
        mapping = ri.ssd.get_mapping()
        controller.mapped_info = make_mapped_info(mapping)
        controller.preview_params = make_preview_params(mapping, sd, ri.pairedranges)
        controller.known_info_list = None

        convert_to_guinier_result_array(controller, ri.rgcurves)
        prepare_extrapolation(controller)
        try:
            do_extrapolation(controller)
            clean_tempfolders(controller)
        except:
            from molass_legacy.KekLib.ExceptionTracebacker import log_exception
            log_exception(controller.logger, 'Error during make_lrf_report: ')
            punit.tell_error()
    else:
        controller.logger.warning( 'No range for LRF was found.' )

    punit.all_done()

def convert_to_guinier_result_array(controller, rgcurves):
    """
    Convert the RG curves to a Guinier result array.
    
    """
    from molass_legacy.AutorgKek.LightObjects import LightIntensity, LightResult
    controller.logger.info('Converting to Guinier result array...')
    
    guinier_result_array = []
    intensities = rgcurves[0].intensities   # See RgCurve.construct_rgcurve_from_list
    for k, (mo_result, at_result) in enumerate(zip(rgcurves[0].results, rgcurves[1].results)):
        light_intensity = LightIntensity(intensities[k])
        light_result    = LightResult(mo_result)
        guinier_result_array.append([light_intensity, light_result, at_result])

    controller.guinier_result_array = guinier_result_array
    controller.logger.info('Conversion to Guinier result array completed.')