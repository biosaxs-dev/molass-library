"""
    DataUtils.FolderWalker.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import os

def default_iswanted(nodes):
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
    return folder.find('_micro') > 0

def walk_folders(folder, level=0, depth=3, iswanted=default_iswanted, filter=default_filter):
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