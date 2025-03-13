"""
    Reports.Controller.py

"""
import os
import logging

class Controller:
    def __init__(self, parallel=False):
        self.logger = logging.getLogger(__name__)
        self.temp_folder = ".temp"
        self.make_temp_folder()
        self.more_multicore = parallel and os.cpu_count() > 4
        if self.more_multicore:
            from ExcelProcess.ExcelTeller import ExcelTeller
            self.teller = ExcelTeller(log_folder=self.temp_folder)
            self.logger.info('teller created with log_folder=%s', self.temp_folder)
            self.excel_client = None
        else:
            from KekLib.ExcelCOM import CoInitialize, ExcelComClient
            self.teller = None
            CoInitialize()
            self.excel_client = ExcelComClient()

    def make_temp_folder( self ):
        from KekLib.BasicUtils import clear_dirs_with_retry
        try:
            clear_dirs_with_retry([self.temp_folder])
        except Exception as exc:
            from KekLib.ExceptionTracebacker import  ExceptionTracebacker
            etb = ExceptionTracebacker()
            self.logger.error( etb )
            raise exc
    
    def stop(self):
        if self.teller is None:
            self.cleanup()
        else:
            self.teller.stop()
    
    def cleanup(self):
        from KekLib.ExcelCOM import CoUninitialize
        self.excel_client.quit()
        self.excel_client = None
        CoUninitialize()

    def make_v1report(self, ssd, *args, **kwargs):
        """ssd.ake_excel_report(lw_info, rgcurve, rgcurve_atsas)

        Parameters
        ----------
        None
        """
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.Reports.V1Report
            reload(molass.Reports.V1Report)
        from  molass.Reports.V1Report import make_v1report_impl
        make_v1report_impl(self, ssd, *args, **kwargs)