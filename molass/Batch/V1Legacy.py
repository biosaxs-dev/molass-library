"""
    Batch.V1Legacy.py

    This module contains the functions that are used to run the
    fully automatic batch like _MOLASS V1.

    Copyright (c) 2025, SAXS Team, KEK-PF
"""

def run_fullyautomatic_v1(in_folder, out_folder):
    """
    Run V1 legacy batch

    Parameters
    ---------- 
    in_folder : str
        The input folder
    out_folder : str
        The output folder
    """
    
    from molass.Batch.V1Result import V1Result
    return V1Result()