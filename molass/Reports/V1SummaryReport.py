"""
Reports.V1SummaryReport.py
"""
from time import time

from molass_legacy.SerialAnalyzer.StageSummary import do_summary_stage

def make_summary_report(punit, controller, kwargs):
    """
    Create a summary report for the given controller and run info.
    This function is a wrapper around the do_summary_stage function.
    
    Parameters
    ----------
    punit : ProgressUnit
        The progress unit to track the progress of the report generation.
    controller : Controller
        The controller containing the data and settings for the report.
    kwargs : dict
        Additional keyword arguments for configuration.
    Returns
    -------
    None
    """
    start_time = time()
    controller.logger.info("Generating summary report...")

    # Call the summary stage function to generate the report
    do_summary_stage(controller)

    controller.logger.info("Summary report generation completed.")
    controller.seconds_summary = int(time() - start_time)
    punit.all_done()