"""
DataUtils.ZipFolder.py

This module is used to zip a folder
"""
import os
import zipfile

def zip_folder(folder, zip_file):
    # Zip a folder including the folder name
    # suggested by GitHub Copilot or https://stackoverflow.com/a/1855118

    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.join(folder, '..'))
                zipf.write(file_path, arcname)