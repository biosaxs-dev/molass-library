"""
    Reports.V1Report.py
"""
from importlib import reload
import threading
from tqdm import tqdm
from molass.Reports.ReportInfo import ReportInfo

def make_v1report_impl(ssd, **kwargs):
    """

    """ 
    from molass.Progress.ProgessUtils import ProgressSet
    ps = ProgressSet()

    pu = ps.add_unit(10)
    pu_list = [pu]

    tread1 = threading.Thread(target=make_v1report_runner, args=[pu_list, ssd, kwargs])
    tread1.start()
 
    with tqdm(ps) as t:
        for j, ret in enumerate(t):
            t.set_description(str(([j], ret)))

    tread1.join()

def make_v1report_runner(pu_list, ssd, kwargs):
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.PairedRange
        reload(molass.LowRank.PairedRange)
        import molass.Reports.V1GuinierReport
        reload(molass.Reports.V1GuinierReport)
        import molass.Reports.Controller
        reload(molass.Reports.Controller)
    from molass.LowRank.PairedRange import convert_to_flatranges
    from molass.Reports.V1GuinierReport import make_guinier_report
    from molass.Reports.Controller import Controller

    controller = Controller()

    bookfile = kwargs.get('bookfile', "book1.xlsx")
    conc_info = kwargs.get('conc_info', None)
    rg_info = kwargs.get('rg_info', None)
    lr_info = kwargs.get('lr_info', None)
    ranges = kwargs.get('ranges', None)
 

    if conc_info is None:
        conc_info = ssd.make_conc_info()

    if rg_info is None:
        mo_rgcurve = ssd.xr.compute_rgcurve()
        at_rgcurve = ssd.xr.compute_rgcurve_atsas()
        rg_info = (mo_rgcurve, at_rgcurve)

    if lr_info is None:
        from molass.LowRank.CoupledAdjuster import make_lowrank_info_impl
        lr_info = ssd.quick_lowrank_info()

    if ranges is None:
        ranges = lr_info.make_v1report_ranges()

    ranges = convert_to_flatranges(ranges)

    if debug:
        print("make_v1report_impl: ranges=", ranges)

    ri = ReportInfo(ssd=ssd,
                    conc_info=conc_info,
                    rg_info=rg_info,
                    lr_info=lr_info,
                    ranges=ranges,
                    bookfile=bookfile)

    make_guinier_report(pu_list[0], controller, ri, kwargs)
