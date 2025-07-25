"""
    Reports.V1Report.py
"""
import os
from importlib import reload
import threading
from tqdm import tqdm
from molass_legacy._MOLASS.SerialSettings import set_setting

ALLOWED_KEYS = {'rgcurves', 'ranges', 'decomposition',
                'debug', 'guinier_only', 'prepare_lrf_only', 'concentration_datatype',
                'report_folder', 'bookname', 'jupyter', 'parallel', 'track_concentration'}
class PreProcessing:
    """
    A class to prepare the V1 report.
    This class is used to prepare the V1 report by running the necessary steps in a separate thread.
    It uses a progress set to track the progress of the report generation.
    """
    def __init__(self, ssd, **kwargs):
        self.ssd = ssd
        self.kwargs = kwargs
        self.num_steps = 0
        self.rgcurves = kwargs.get('rgcurves', None)
        if self.rgcurves is None:
            self.num_steps += 2
        self.decomposition = kwargs.get('decomposition', None)
        if self.decomposition is None:
            self.num_steps += 1
        self.pairedranges = kwargs.get('pairedranges', None)
        if self.pairedranges is None:
            self.num_steps += 1

    def __len__(self):
        return self.num_steps

    def run(self, pu, debug=False):
        if self.rgcurves is None:
            mo_rgcurve = self.ssd.xr.compute_rgcurve()
            at_rgcurve = self.ssd.xr.compute_rgcurve_atsas()
            self.rgcurves = (mo_rgcurve, at_rgcurve)
            pu.step_done()

        if self.decomposition is None:
            self.decomposition = self.ssd.quick_decomposition()
            pu.step_done()

        if self.pairedranges is None:
            self.pairedranges = self.decomposition.get_pairedranges()
            pu.step_done()

        pu.all_done()

def make_v1report(ssd, **kwargs):
    """

    """
    from molass_legacy.Env.EnvInfo import get_global_env_info
    from molass.PackageUtils.PyWin32Utils import check_pywin32_postinstall
    if not check_pywin32_postinstall():
        print("\nPlease run (possibly as administrator) the following command to fix the issue:")
        print("python -m pywin32_postinstall -install\n")
        raise RuntimeError("pywin32 post-installation has not been run or is incomplete.")
    from molass.Progress.ProgessUtils import ProgressSet
    if not set(kwargs).issubset(ALLOWED_KEYS):
        raise TypeError(f"Unknown keyword arguments: {set(kwargs) - ALLOWED_KEYS}")
    debug = kwargs.get('debug', False)
    guinier_only = kwargs.get('guinier_only', False)
    prepare_lrf_only = kwargs.get('prepare_lrf_only', False)
    concentration_datatype = kwargs.get('concentration_datatype', 2)  # Default to UV model
    kwargs['concentration_datatype'] = concentration_datatype

    env_info = get_global_env_info()    # do this here in the main thread to avoid issues with the reporting thread
    preproc = PreProcessing(ssd, **kwargs)
    timeout = 5 if prepare_lrf_only else 60
    ps = ProgressSet(timeout=timeout)
    pu_list = []
    pu = ps.add_unit(len(preproc))  # Preprocessing
    pu_list.append(pu)
    pu = ps.add_unit(10)    # Guinier Analysis
    pu_list.append(pu)
    if not guinier_only:
        pu = ps.add_unit(10)    # Peak Side LRF Analysis
        pu_list.append(pu)
        pu = ps.add_unit(10)    # Summary Report
        pu_list.append(pu)

    tread1 = threading.Thread(target=make_v1report_runner, args=[pu_list, ssd, preproc, env_info, kwargs])
    tread1.start()
 
    with tqdm(ps) as t:
        for j, ret in enumerate(t):
            t.set_description(str(([j], ret)))

    tread1.join()

def make_v1report_runner(pu_list, ssd, preproc, env_info, kwargs):
    debug = kwargs.get('debug', False)
    guinier_only = kwargs.get('guinier_only', False)
    
    if debug:
        import molass.Reports.Controller
        reload(molass.Reports.Controller)
        import molass.LowRank.PairedRange
        reload(molass.LowRank.PairedRange)
        import molass.Reports.V1GuinierReport
        reload(molass.Reports.V1GuinierReport)
        import molass.Reports.V1LrfReport
        reload(molass.Reports.V1LrfReport)
    from molass.Reports.Controller import Controller
    from molass.Reports.V1GuinierReport import make_guinier_report
    from molass.Reports.V1LrfReport import make_lrf_report
    from molass.Reports.V1SummaryReport import make_summary_report

    preproc.run(pu_list[0], debug=debug)

    controller = Controller(env_info, ssd, preproc, kwargs)
    controller.seconds_correction = ssd.time_required_total - ssd.time_initialized

    prepare_lrf_only = kwargs.get('prepare_lrf_only', False)
    if prepare_lrf_only:
        from molass.Reports.V1LrfReport import prepare_controller_for_lrf
        print("Preparing controller for LRF report... with prepare_lrf_only=True")
        prepare_controller_for_lrf(controller, kwargs)
        return

    controller.temp_books = []
    make_guinier_report(pu_list[1], controller, kwargs)
    if not guinier_only:
        make_lrf_report(pu_list[2], controller, kwargs)
        make_summary_report(pu_list[3], controller, kwargs)