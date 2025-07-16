"""
Reports.V1GuinierReport.py

This module contains the functions to generate the reports the Guinier Analysis.
"""
import os
from importlib import reload
from time import sleep

WRITE_TO_TEMPFILE = False

def make_guinier_report(punit, controller, ri, kwargs):
    debug = kwargs.get('debug')
    if debug:
        import molass_legacy.Reports.GuinierAnalysisResultBook
        reload(molass_legacy.Reports.GuinierAnalysisResultBook)
        import molass.Reports.Migrating
        reload(molass.Reports.Migrating)
    from molass_legacy.Reports.GuinierAnalysisResultBook import GuinierAnalysisResultBook
    from molass.Reports.Migrating import make_gunier_row_values

    if controller.excel_is_available:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
    else:
        wb = controller.result_wb
        ws = wb.create_sheet('Guinier Analysis')

    mo_rgcurve, at_rgcurve = ri.rgcurves
    x, y = ri.mapped_curve.get_xy()
    num_rows = len(y)

    if WRITE_TO_TEMPFILE:
        fh = open("temp.csv", "w")
    else:
        fh = None
    num_steps = len(punit)
    cycle = len(y)//num_steps
    rows = []
    for i in range(num_rows):
        sleep(0.1)
        j = mo_rgcurve.index_dict.get(i)
        if j is None:
            mo_result = None
        else:
            mo_result = mo_rgcurve.results[j]
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
    book = GuinierAnalysisResultBook(wb, ws, rows, j0, parent=controller)
 
    if controller.excel_is_available:
        bookfile = ri.bookfile
        bookpath = os.path.abspath(bookfile)
        print("Saving Guinier Analysis Report to", bookpath)
        book.save(bookpath)
        sleep(0.1)
        book.add_annonations(bookpath, ri.list_ranges, debug=debug)

    punit.all_done()