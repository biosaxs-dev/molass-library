"""
    Reports.Controller.py
"""
import os
from molass_legacy.KekLib.ChangeableLogger import Logger
from molass_legacy._MOLASS.SerialSettings import get_setting, set_setting
from molass_legacy.SerialAnalyzer.SerialController import SerialExecuter

class Controller(SerialExecuter):
    """
    Controller class for managing report generation in MOLASS.

    This class corresponds to the legacy SerialExecuter class in molass_legacy.SerialAnalyzer.SerialController.

    Inherits from SerialExecuter to use the following methods:
        save_smoothed_data
    """
    def __init__(self, env_info, ssd, preproc, kwargs):
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.Backward.ConcTracker
            reload(molass.Backward.ConcTracker)
        from molass.Backward.ConcTracker import ConcTracker

        jupyter = kwargs.get('jupyter', False)
        report_folder = kwargs.get('report_folder', None)
        bookname = kwargs.get('bookname', None)
        parallel = kwargs.get('parallel', False)
        track_concentration = kwargs.get('track_concentration', False)
        self.ssd = ssd
        self.rgcurves = preproc.rgcurves
        self.pairedranges = preproc.pairedranges

        self.decomposition = preproc.decomposition
        self.concentration_datatype = kwargs.get('concentration_datatype', 2)  # Default to UV model
        conc_factor = ssd.get_concfactor()  # Ensure concfactor is set
        if track_concentration:
            self.conc_tracker = ConcTracker(self.decomposition, conc_factor, self.concentration_datatype, jupyter=jupyter, debug=debug)
        else:
            self.conc_tracker = None
        if report_folder is None:
            cwd = os.getcwd()
            report_folder = os.path.join(cwd, 'report_folder')
        self.work_folder = report_folder
        if not os.path.exists( self.work_folder ):
            os.makedirs( self.work_folder )
        # self.logger = logging.getLogger(__name__)
        self.logger = Logger(os.path.join(self.work_folder, 'molass.log'))
        self.temp_folder = os.path.join(self.work_folder, '.temp')
        self.make_temp_folder()
        self.logger.info('Controller initialized with temp_folder=%s', self.temp_folder)
        if bookname is None:
            bookname = "analysis_report.xlsx"
        if os.path.isabs(bookname):
            bookpath = bookname
        else:
            bookpath = os.path.join(self.work_folder, bookname)
        self.env_info = env_info
        self.bookpath= bookpath
        self.book_file = bookpath   # for compatibility with legacy code
        self.excel_is_available = self.env_info.excel_is_available
        self.excel_version = self.env_info.excel_version
        self.atsas_is_available = self.env_info.atsas_is_available
        self.more_multicore = parallel and os.cpu_count() > 4
        self.using_averaged_files = False
        self.maintenance_mode = False
        self.use_simpleguinier = 1
        self.log_memory_usage = 0
        self.range_type = 4  # 4:'Decomposed Elution Range', See molass_lagacy.SerialSettings.py
        self.zx = True
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

        self.seconds_correction = 0     # used in molass_legacy\Reports\SummaryBook.py
        self.seconds_guinier = 0        # used in molass_legacy\Reports\SummaryBook.py
        self.seconds_extrapolation = 0  # used in molass_legacy\Reports\SummaryBook.py
        self.seconds_summary = 0        # used in molass_legacy\Reports\SummaryBook.py
        self.num_peaks_to_exec = 0      # used in molass_legacy\SerialAnalyzer\StageSummary.py
        self.input_smoothing = 1
        self.doing_sec = True

    def prepare_averaged_data(self):
        self.using_averaged_files = False
        if self.input_smoothing == 1:
            num_curves_averaged = get_setting( 'num_curves_averaged' )
            intensity_array_, average_slice_array, c_vector = self.serial_data.get_averaged_data( num_curves_averaged )
            assert c_vector is not None
            if False:
                import numpy as np
                np.savetxt(os.path.join(self.work_folder, 'c_vector.csv'), c_vector, fmt='%.6e', delimiter=',')

            # save
            save_averaged_data = get_setting( 'save_averaged_data' )
            if save_averaged_data == 1:
                self.using_averaged_files = True        # TODO: check consistency
                self.save_smoothed_data( intensity_array_, average_slice_array )
        else:
            assert False

        if self.doing_sec:
            self.c_vector = c_vector
        else:
            assert False

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
