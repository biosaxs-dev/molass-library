"""
Reports.V1LrfReport.py

This module contains the functions to generate the reports for the LRF Analysis.
"""
import os
from importlib import reload
from time import time, sleep

WRITE_TO_TEMPFILE = False

def prepare_controller_for_lrf(controller, kwargs):
    """
    Prepare the controller for LRF report generation.
    This function sets up the controller with the necessary data and parameters
    for the LRF report generation process.
    """
    debug = kwargs.get('debug')
    if debug:
        import molass.Backward.SerialDataProxy
        reload(molass.Backward.SerialDataProxy)
        import molass.Backward.MappedInfoProxy
        reload(molass.Backward.MappedInfoProxy)
        import molass.Backward.PreviewParams
        reload(molass.Backward.PreviewParams)
    from molass.Backward.SerialDataProxy import SerialDataProxy
    from molass_legacy.DataStructure.AnalysisRangeInfo import report_ranges_from_analysis_ranges
    from molass_legacy._MOLASS.SerialSettings import set_setting
    from molass.Backward.PreviewParams import make_preview_params
    from molass.Backward.MappedInfoProxy import make_mapped_info
    set_setting('conc_dependence', 1)           # used in ExtrapolationSolver.py
    set_setting('mapper_cd_color_info', controller.decomposition.get_cd_color_info())
    concentration_datatype = kwargs['concentration_datatype'] 
    set_setting('concentration_datatype', concentration_datatype)    # 0: XR model, 1: XR data, 2: UV model, 3: UV data

    ssd = controller.ssd
    controller.logger.info('Starting LRF report generation...')
    controller.applied_ranges = controller.pairedranges # for compatibility with legacy code
    controller.qvector = ssd.xr.qv
    sd = SerialDataProxy(ssd, controller.decomposition.mapped_curve, debug=debug)
    controller.serial_data = sd
    controller.xr_j0 = sd.xr_j0
    # task: xr_j0 can be incompatible when xr_j0 > 0. Remove xr_j0 eventually.
    controller.report_ranges = report_ranges_from_analysis_ranges(controller.xr_j0, controller.applied_ranges)
    print("applied ranges:", controller.applied_ranges)
    print("report ranges:", controller.report_ranges)
    mapping = ssd.get_mapping()
    controller.mapped_info = make_mapped_info(controller.ssd, mapping)
    controller.preview_params = make_preview_params(mapping, sd, controller.pairedranges)
    controller.known_info_list = None
    controller.zx_summary_list = []
    controller.zx_summary_list2 = []
    controller.temp_books_atsas = []
    controller.datafiles = ssd.datafiles
    # controller.c_vector = sd.mc_vector  # task: unify c_vector and mc_vector
    controller.prepare_averaged_data()  # c_vector is set here

    convert_to_guinier_result_array(controller, controller.rgcurves)

def make_lrf_report(punit, controller, kwargs):
    """
    Make a report for the LRF Analysis.

    Migrated from molass_legacy.StageExtrapolation.control_extrapolation().
    """
    debug = kwargs.get('debug')
    if debug:
        import molass_legacy.SerialAnalyzer.StageExtrapolation
        reload(molass_legacy.SerialAnalyzer.StageExtrapolation)
    from molass_legacy.SerialAnalyzer.StageExtrapolation import prepare_extrapolation, do_extrapolation, clean_tempfolders

    start_time = time()

    if len(controller.pairedranges) > 0:
        prepare_controller_for_lrf(controller, kwargs)
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

    if debug:
        if controller.conc_tracker is not None:
            savepath = os.path.join(controller.work_folder, 'tracked_concentrations.png')
            controller.conc_tracker.plot(savepath=savepath)
    controller.seconds_extrapolation = int(time() - start_time)
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