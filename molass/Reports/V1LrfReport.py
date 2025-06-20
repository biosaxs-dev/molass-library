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
        import molass_legacy.SerialAnalyzer.StageExtrapolation
        reload(molass_legacy.SerialAnalyzer.StageExtrapolation)
    from molass_legacy.SerialAnalyzer.StageExtrapolation import prepare_extrapolation, do_extrapolation, clean_tempfolders

    if len(ri.ranges) > 0:
        controller.logger.info('Starting LRF report generation...')
        controller.ri = ri
        controller.applied_ranges = ri.ranges
        convert_to_guinier_result_array(controller, ri.rg_info)
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

def convert_to_guinier_result_array(controller, rg_info):
    from molass_legacy.AutorgKek.LightObjects import LightIntensity, LightResult
    controller.logger.info('Converting to Guinier result array...')
    
    guinier_result_array = []
    for k, (mo_result, at_result) in enumerate(zip(rg_info[0].results, rg_info[1].results)):
        light_intensity = LightIntensity(mo_result.intensity)
        light_result    = LightResult(mo_result)
        guinier_result_array.append([light_intensity, light_result, at_result])

    controller.gu_result_array = guinier_result_array
    controller.logger.info('Conversion to Guinier result array completed.')