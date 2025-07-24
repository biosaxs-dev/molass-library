"""
Reports.V1GuinierReport.py

This module contains the functions to generate the reports the Guinier Analysis.
"""
import os
from importlib import reload
from time import time, sleep

WRITE_TO_TEMPFILE = False

def make_guinier_report(punit, controller, kwargs):
    debug = kwargs.get('debug')
    if debug:
        import molass_legacy.Reports.GuinierAnalysisResultBook
        reload(molass_legacy.Reports.GuinierAnalysisResultBook)
        import molass.Reports.Migrating
        reload(molass.Reports.Migrating)
    from molass_legacy.Reports.GuinierAnalysisResultBook import GuinierAnalysisResultBook
    from molass.Reports.Migrating import make_gunier_row_values

    guinier_only = kwargs.get('guinier_only', False)    
    start_time = time()

    if controller.excel_is_available:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
    else:
        wb = controller.result_wb
        ws = wb.create_sheet('Guinier Analysis')

    mo_rgcurve, at_rgcurve = controller.rgcurves
    mapped_curve = controller.decomposition.mapped_curve
    assert mapped_curve is not None, "Mapped curve must be provided for Guinier analysis."
    concfactor = controller.ssd.get_concfactor()  # ensure concfactor is set
    # conc_factor?
    x, y = (mapped_curve * concfactor).get_xy()
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

    if guinier_only:
        temp_book = controller.bookpath
    else:
        temp_book = controller.temp_folder + '/--serial_analysis-temp.xlsx'

    if controller.excel_is_available:
        print("Saving Guinier Analysis Report to", temp_book)
        book.save(temp_book)
        sleep(0.1)
        ranges = []
        for range_ in controller.pairedranges:
            fromto_list = range_.get_fromto_list()
            ranges.append([fromto_list[0][0], fromto_list[-1][1]])
        book.add_annotations(temp_book, ranges, debug=debug)

    if not guinier_only:
        controller.temp_books.append(temp_book)
    controller.seconds_guinier = int(time() - start_time)
    punit.all_done()