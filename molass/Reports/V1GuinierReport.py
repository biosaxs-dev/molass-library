"""
Reports.V1GuinierReport.py

This module contains the functions to generate the reports for the Guinier
Analysis Report.
"""
from importlib import reload
from time import sleep

WRITE_TO_TEMPFILE = False

def make_guinier_report(controller, punit, ri, kwargs):
    debug = kwargs.get('debug')
    if debug:
        import Reports.GuinierAnalysisResultBook
        reload(Reports.GuinierAnalysisResultBook)
        import molass.Reports.Migrating
        reload(molass.Reports.Migrating)
        import molass.Reports.Controller
        reload(molass.Reports.Controller)
    from Reports.GuinierAnalysisResultBook import GuinierAnalysisResultBook
    from molass.Reports.Migrating import make_gunier_row_values
    from molass.Reports.Controller import Controller

    wb = ri.wb
    ws = ri.ws
    ssd = ri.ssd
    mo_rgcurve, at_rgcurve = ri.rg_info
    x, y = ri.conc_info.curve.get_xy()
    num_rows = len(x)

    row_list = []

    if WRITE_TO_TEMPFILE:
        fh = open("temp.csv", "w")
    else:
        fh = None
    num_steps = len(punit)
    cycle = len(x)//num_steps
    rows = []
    for i in range(num_rows):
        sleep(0.1)
        j = mo_rgcurve.index_dict.get(i)
        if j is None:
            mo_result = None
        else:
            mo_result = mo_rgcurve.results[j]
            mo_quality = mo_result.quality_object
        k = at_rgcurve.index_dict.get(i)
        if k is None:
            at_result = None
        else:
            at_result = at_rgcurve.results[k]

        values = make_gunier_row_values(mo_result, at_result, return_selected=True)

        conc = y[i]
        values = [None, None, conc] + values

        if fh is not None:
            fh.write(','.join(["" if v is None else "%g" % v for v in values]) + "\n")

        rows.append(values)

        if i % cycle == 0:
            punit.step_done()

    if fh is not None:
        fh.close()

    j0 = int(x[0])
    controller = Controller()
    book = GuinierAnalysisResultBook(wb, ws, rows, j0, parent=controller)
    ranges = ri.ranges

    bookfile = ri.bookfile
    book.save(bookfile)
    book.add_annonations(bookfile, ri.ranges)

    punit.all_done()