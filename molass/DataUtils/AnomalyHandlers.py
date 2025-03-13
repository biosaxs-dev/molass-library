"""
    DataUtils.AnomalyHandlers.py
"""

def remove_bubbles_impl(xr_data, from_, to_, debug=False):
    """
    ported from SerialData.exclude_intensities
    """
    if debug:
        print("remove_bubbles_impl:", from_, to_ )

    M = xr_data.M
    E = xr_data.E
    size = M.shape[1]
    excluded = []
    if from_ == 0:
        j = to_ + 1
        for i in range( from_, j ):
            M[:,i] = M[:,j]
            E[:,i] = E[:,j]
            excluded.append(i)
    elif to_ == size - 1:
        j = from_ - 1
        for i in range( from_, size ):
            M[:,i] = M[:,j]
            E[:,i] = E[:,j]
            excluded.append(i)
    else:
        lower = from_ - 1
        upper = to_ + 1
        lower_M = M[:,lower]
        upper_M = M[:,upper]
        lower_E = E[:,lower]
        upper_E = E[:,upper]
        width = upper - lower
        for i in range(1, width):
            w = i/width
            M[:,lower+i] = (1 - w) * lower_M + w * upper_M
            E[:,lower+i] = (1 - w) * lower_E + w * upper_E
            excluded.append(lower+i)
    if debug:
        print("excluded=", excluded)

def detect_and_remove_bubbles(xr_data, debug=False):
    if debug:
        from importlib import reload
        import SerialAnalyzer.AbnormalityCheck
        reload(SerialAnalyzer.AbnormalityCheck)
    from molass_legacy.SerialAnalyzer.AbnormalityCheck import bubble_check_impl
    curve = xr_data.get_icurve()
    to_be_removed = bubble_check_impl(curve.y, debug=debug)
    if debug:
        print("detect_and_remove_bubbles: to_be_removed=", to_be_removed)

    if len(to_be_removed) > 0:
        ret_data = xr_data.copy()
        from_ = None
        for i in to_be_removed:
            if from_ is None:
                from_ = i
            else:
                if i > last + 1:
                    remove_bubbles_impl(ret_data, from_, last)
                    from_ = i

            last = i
        if from_ is not None:
            remove_bubbles_impl(ret_data, from_, last)
    else:
        ret_data = xr_data

    return ret_data, to_be_removed