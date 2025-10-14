"""
    DataUtils.FolderWalker.py

    Utility functions to walk through folders and find those containing specific data files.
"""
import os

def default_iswanted(nodes):
    """Determine if a folder is wanted based on the presence of .dat files.
    A folder is considered wanted if it contains more than 10 .dat files.

    Parameters
    ----------
    nodes : list of str
        List of file and folder names in the directory.

    Returns
    -------
    bool
        True if the folder is wanted, False otherwise.
    """
    dat_count = 0
    for k, node in enumerate(nodes):
        if k > 20:
            return False
        if node[-4:].lower() == '.dat':
            dat_count += 1
        if dat_count > 10:
            return True
    return False

def default_filter(folder):
    """Default filter to exclude folders with '_micro' in their names.

    Parameters
    ----------
    folder : str
        The folder path.

    Returns
    -------
    bool
        True if the folder is wanted, False otherwise.
    """
    return folder.find('_micro') > 0

def walk_folders(folder, level=0, depth=3, iswanted=default_iswanted, filter=default_filter):
    """Walk through folders up to a certain depth and yield those that are wanted.
    
    Parameters
    ----------
    folder : str
        The root folder to start walking from.
    level : int, optional
        The current depth level (default is 0).
    depth : int, optional
        The maximum depth to walk (default is 3).
    iswanted : function, optional
        A function that takes a list of nodes and returns True if the folder is wanted (default is default_iswanted).
    filter : function, optional
        A function that takes a folder path and returns True if the folder should be excluded (default is default_filter).

    Yields
    ------
    str
        The path of the wanted folder.
    """
    if not filter(folder):
        # see https://stackoverflow.com/questions/6266561/how-to-write-python-generator-function-that-never-yields-anything
        yield from []
    
    nodes = os.listdir(folder)
    if iswanted(nodes):
        yield folder
    else:
        if level < depth:
            for node in sorted(nodes):
                path = os.path.join(folder, node)
                if os.path.isdir(path):
                    # see https://stackoverflow.com/questions/38254304/python-can-generators-be-recursive
                    yield from walk_folders(path, level=level+1, depth=depth, iswanted=iswanted)