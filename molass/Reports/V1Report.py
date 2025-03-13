"""
    Reports.V1Report.py
"""
from importlib import reload
import threading
from tqdm import tqdm
from openpyxl import Workbook
from molass.Reports.ReportInfo import ReportInfo

def make_v1report_impl(controller, ssd, bookfile=None, conc_info=None, rg_info=None, lr_info=None, ranges=None, debug=False):
    if debug:
        import molass.Progress.ProgessUtils
        reload(molass.Progress.ProgessUtils)
        import molass.LowRank.PairedRange
        reload(molass.LowRank.PairedRange)
        import molass.Reports.V1GuinierReport
        reload(molass.Reports.V1GuinierReport)
    from molass.Progress.ProgessUtils import ProgressSet
    from molass.LowRank.PairedRange import convert_to_flatranges
    from molass.Reports.V1GuinierReport import make_guinier_report

    if bookfile is None:
        bookfile = "book1.xlsx"

    if conc_info is None:
        conc_info = ssd.make_conc_info()

    if rg_info is None:
        mo_rgcurve = ssd.compute_rgcurve()
        at_rgcurve = ssd.compute_rgcurve_atsas()
        rg_info = (mo_rgcurve, at_rgcurve)

    if lr_info is None:
        from molass.LowRank.CoupledAdjuster import make_lowrank_info_impl
        lr_info = ssd.quick_lowrank_info()

    if ranges is None:
        ranges = lr_info.make_v1report_ranges()

    ranges = convert_to_flatranges(ranges)

    if debug:
        print("make_v1report_impl: ranges=", ranges)

    wb = Workbook()
    ws = wb.active
    ri = ReportInfo(ssd=ssd,
                    conc_info=conc_info,
                    rg_info=rg_info,
                    lr_info=lr_info,
                    ranges=ranges,
                    wb=wb, ws=ws,
                    bookfile=bookfile)
 
    ps = ProgressSet()

    pu = ps.add_unit(10)
    kwargs = {}
    kwargs['debug'] = debug

    tread1 = threading.Thread(target=make_guinier_report, args=[controller, pu, ri, kwargs])
    tread1.start()

    with tqdm(ps) as t:
        for j, ret in enumerate(t):
            t.set_description(str(([j], ret)))

    tread1.join()