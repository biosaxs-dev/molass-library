"""
    Reports.Controller.py
"""
import os
import logging
from molass_legacy._MOLASS.SerialSettings import set_setting

class Controller:
    """
    Controller class for managing report generation in MOLASS.

    This class corresponds to the legacy SerialExecuter class in molass_legacy.SerialAnalyzer.SerialController.
    """
    def __init__(self, env_info, parallel=False):
        self.logger = logging.getLogger(__name__)
        cwd = os.getcwd()
        self.work_folder = os.path.join(cwd, 'report_folder')
        if not os.path.exists( self.work_folder ):
            os.makedirs( self.work_folder )
        self.temp_folder = os.path.join(self.work_folder, '.temp')
        self.make_temp_folder()
        self.logger.info('Controller initialized with temp_folder=%s', self.temp_folder)
        self.env_info = env_info
        self.excel_is_available = self.env_info.excel_is_available
        self.excel_version = self.env_info.excel_version
        self.atsas_is_available = self.env_info.atsas_is_available
        self.more_multicore = parallel and os.cpu_count() > 4
        self.using_averaged_files = False
        self.maintenance_mode = False
        self.use_simpleguinier = 1
        self.log_memory_usage = 0
        self.range_type = 4  # 4:'Decomposed Elution Range', See molass_lagacy.SerialSettings.py
        averaged_data_folder = os.path.join(self.work_folder, 'averaged')
        set_setting('averaged_data_folder', averaged_data_folder)
        
        if self.excel_is_available:
            if self.more_multicore:
                from molass_legacy.ExcelProcess.ExcelTeller import ExcelTeller
                self.teller = ExcelTeller(log_folder=self.temp_folder)
                self.logger.info('teller created with log_folder=%s', self.temp_folder)
                self.excel_client = None
            else:
                from molass_legacy.KekLib.ExcelCOM import CoInitialize, ExcelComClient
                self.teller = None
                CoInitialize()
                self.excel_client = ExcelComClient()
            self.result_wb = None
        else:
            from openpyxl import Workbook
            self.excel_client = None
            self.result_wb = Workbook()

    def make_temp_folder( self ):
        from molass_legacy.KekLib.BasicUtils import clear_dirs_with_retry
        try:
            clear_dirs_with_retry([self.temp_folder])
        except Exception as exc:
            from molass_legacy.KekLib.ExceptionTracebacker import  ExceptionTracebacker
            etb = ExceptionTracebacker()
            self.logger.error( etb )
            raise exc
    
    def stop(self):
        if self.teller is None:
            self.cleanup()
        else:
            self.teller.stop()
    
    def cleanup(self):
        from molass_legacy.KekLib.ExcelCOM import CoUninitialize
        self.excel_client.quit()
        self.excel_client = None
        CoUninitialize()

    def stop_check(self):
        """
        Check if the controller should stop.
        """
        from molass_legacy.KekLib.ProgressInfo import on_stop_raise
        def log_closure(cmd):
            # this closure is expected to be called only in cancel operations
            self.logger.info("cmd=%s", str(cmd))
        on_stop_raise(cleanup=self.error_cleanup, log_closure=log_closure)
    
    def cleanup(self):
        self.logger.info("Cleanup started. This may take some time (not more than a few minutes). Please be patient.")

        if self.more_multicore:
            self.teller.stop()   # must be done before the removal below of the temp books

        if self.excel_is_available:
            if self.more_multicore:
                pass
            else:
                from molass_legacy.KekLib.ExcelCOM import CoUninitialize
                self.excel_client.quit()
                self.excel_client = None
                CoUninitialize()

            for path in self.temp_books + self.temp_books_atsas:
                os.remove( path )

        self.logger.info("Cleanup done.")

    def error_cleanup(self):
        from molass_legacy.KekLib.ExcelCOM import cleanup_created_excels
        self.cleanup()
        cleanup_created_excels()
