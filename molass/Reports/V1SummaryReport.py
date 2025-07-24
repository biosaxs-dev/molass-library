"""
Reports.V1SummaryReport.py
"""
from time import time

from molass_legacy.SerialAnalyzer.StageSummary import do_summary_stage

def make_summary_report(punit, controller, kwargs):
    """
    Create a summary report for the given controller and run info.
    This function is a wrapper around the do_summary_stage function.
    """
    start_time = time()
    controller.logger.info("Generating summary report...")

    # Call the summary stage function to generate the report
    do_summary_stage(controller)

    controller.logger.info("Summary report generation completed.")
    controller.seconds_summary = int(time() - start_time)
    punit.all_done()