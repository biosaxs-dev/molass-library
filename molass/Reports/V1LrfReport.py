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
        import molass.Backward.PreviewParams
        reload(molass.Backward.PreviewParams)
        import molass_legacy.SerialAnalyzer.StageExtrapolation
        reload(molass_legacy.SerialAnalyzer.StageExtrapolation)
    from molass.Backward.SerialDataProxy import SerialDataProxy
    from molass.Backward.PreviewParams import make_preview_params
    from molass_legacy.SerialAnalyzer.StageExtrapolation import prepare_extrapolation, do_extrapolation, clean_tempfolders

    if len(ri.pairedranges) > 0:
        controller.logger.info('Starting LRF report generation...')
        controller.ri = ri
        controller.applied_ranges = ri.pairedranges
        controller.qvector = ri.ssd.xr.qv
        sd = SerialDataProxy(ri.ssd, ri.concentration)
        controller.preview_params = make_preview_params(sd=sd, paired_ranges=ri.list_ranges)
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