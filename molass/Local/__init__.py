"""
This module contains the functions that are used to manage local settings.
"""

MAX_NUM_LEVELS = 5

def get_local_settings(filename='local_settings.py', debug=False):
    """
    Locate and get the local settings from the local_settings.py file.

    the local_settings.py is supposed to be in one of the upper directories
    relative to this code file. The function will search for the file in the
    directories above this code file and will return the settings as a dictionary.
    """

    import os
    import sys

    # Get the path to the current working directory
    work_dir = os.getcwd()

    # Get the directory of the current file
    found = False
    for n in range(MAX_NUM_LEVELS):
        work_dir = os.path.dirname(work_dir)
        local_settings_file = os.path.join(work_dir, filename)
        if debug:
            print([n], local_settings_file)
        if os.path.exists(local_settings_file):
            found = True
            break

    if not found:
        raise FileNotFoundError('The local_settings.py file was not found.')

    locals_ = {}
    exec(open(local_settings_file).read(), {}, locals_)  # it seems that locals option is required for Python 3.13+.
    return locals_['LocalSettings']