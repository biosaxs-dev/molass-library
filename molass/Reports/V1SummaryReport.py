"""
Reports.V1SummaryReport.py
"""

from molass_legacy.SerialAnalyzer.StageSummary import do_summary_stage

def make_summary_report(punit, controller, ri, kwargs):
    """
    Create a summary report for the given controller and run info.
    This function is a wrapper around the do_summary_stage function.
    """
    controller.logger.info("Generating summary report...")
    
    # Call the summary stage function to generate the report
    do_summary_stage(controller)
    
    punit.all_done()
    controller.logger.info("Summary report generation completed.")