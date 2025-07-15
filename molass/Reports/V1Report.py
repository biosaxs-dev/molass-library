"""
    Reports.V1Report.py
"""
from importlib import reload
import threading
from tqdm import tqdm
from molass.Reports.ReportInfo import ReportInfo

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

    def run(self, pu):
        if self.rgcurves is None:
            mo_rgcurve = self.ssd.xr.compute_rgcurve()
            at_rgcurve = self.ssd.xr.compute_rgcurve_atsas()
            self.rgcurves = (mo_rgcurve, at_rgcurve)
            pu.step_done()

        if self.decomposition is None:
            self.decomposition = self.ssd.quick_decomposition()
            pu.step_done()

        if self.pairedranges is None:
            self.pairedranges = self.decomposition.get_pairedranges(debug=True)
            pu.step_done()

        pu.all_done()

def make_v1report_impl(ssd, **kwargs):
    """

    """
    from molass.PackageUtils.PyWin32Utils import check_pywin32_postinstall
    if not check_pywin32_postinstall():
        print("\nPlease run (possibly as administrator) the following command to fix the issue:")
        print("python -m pywin32_postinstall -install\n")
        raise RuntimeError("pywin32 post-installation has not been run or is incomplete.")

    from molass.Progress.ProgessUtils import ProgressSet
    ps = ProgressSet()

    preproc = PreProcessing(ssd, **kwargs)

    pu_list = []
    pu = ps.add_unit(len(preproc))  # Preprocessing
    pu_list.append(pu)
    pu = ps.add_unit(10)    # Guinier Analysis
    pu_list.append(pu)
    pu = ps.add_unit(10)    # Peak Side LRF Analysis
    pu_list.append(pu)

    tread1 = threading.Thread(target=make_v1report_runner, args=[pu_list, preproc, ssd, kwargs])
    tread1.start()
 
    with tqdm(ps) as t:
        for j, ret in enumerate(t):
            t.set_description(str(([j], ret)))

    tread1.join()

def make_v1report_runner(pu_list, preproc, ssd, kwargs):
    debug = kwargs.get('debug', False)
    from molass.Reports.Controller import Controller
    if debug:
        import molass.LowRank.PairedRange
        reload(molass.LowRank.PairedRange)
        import molass.Reports.V1GuinierReport
        reload(molass.Reports.V1GuinierReport)
        import molass.Reports.V1LrfReport
        reload(molass.Reports.V1LrfReport)
    from molass.LowRank.PairedRange import convert_to_list_pairedranges
    from molass.Reports.V1GuinierReport import make_guinier_report
    from molass.Reports.V1LrfReport import make_lrf_report


    controller = Controller()

    bookfile = kwargs.get('bookfile', "book1.xlsx")

    preproc.run(pu_list[0])

    list_ranges = convert_to_list_pairedranges(preproc.pairedranges)

    if debug:
        print("make_v1report_impl: ranges=", list_ranges)

    ri = ReportInfo(ssd=ssd,
                    rgcurves=preproc.rgcurves,
                    decomposition=preproc.decomposition,
                    pairedranges=preproc.pairedranges,      # used in LRF report
                    list_ranges=list_ranges,                # used in Guinier report
                    bookfile=bookfile)

    make_guinier_report(pu_list[1], controller, ri, kwargs)

    make_lrf_report(pu_list[2], controller, ri, kwargs)
