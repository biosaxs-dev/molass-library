"""
    Test.TestSettings.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import os

ROOT_DATAFOLDER = r"D:\PyTools\Data"

def get_diskdrive():
    return os.path.abspath(__file__)[0]

def set_diskdrive():
    global ROOT_DATAFOLDER
    temp = list(ROOT_DATAFOLDER)
    temp[0] = get_diskdrive()
    ROOT_DATAFOLDER = ''.join(temp)

set_diskdrive()

def get_datafolder(subfolder=None):
    if subfolder is None:
        return ROOT_DATAFOLDER
    else:
        return os.path.join(ROOT_DATAFOLDER, subfolder)