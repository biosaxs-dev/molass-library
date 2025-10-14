"""
This script is used to simplify the process of updating in usual cases
after the initial setup of the documentation.
It is assumed to be run from the docs directory as follows.

.. code-block:: bat

    python tools/UsualUpdate.py

This script performs the following tasks:

1. Checks if the current directory is the docs directory.
2. Checks if the source directory exists and is not empty.
3. Otherwise, generates the initial documentation into the source directory.
4. Makes HTML documentation.
5. Deploys the documentation to GitHub Pages.

"""

import os
import subprocess
import shutil

def main():
    """
    Main function to update the documentation.
    """
    # Get the current working directory
    current_dir = os.getcwd()

    # Check if the current directory is the docs directory
    if os.path.basename(current_dir) != "docs":
        print("Please run this script from the docs directory.")
        return

    # Resolve executable paths
    sphinx_apidoc = shutil.which("sphinx-apidoc")
    make = shutil.which("make")
    ghp_import = shutil.which("ghp-import")

    if not sphinx_apidoc or not make or not ghp_import:
        print("One or more required executables (sphinx-apidoc, make, ghp-import) not found in PATH.")
        return

    # Check if the source directory exists and is not empty
    source_dir = os.path.join(current_dir, "source")
    if os.path.exists(source_dir) and os.listdir(source_dir):
        print("The source directory exists and is not empty.")
        # Proceed with your logic for a non-empty source directory
    else:
        print("The source directory is empty or does not exist.")
        # Execute the sphinx-apidoc command to generate the initial documentation
        subprocess.run([sphinx_apidoc, "--output-dir", "source", "../molass", "--separate", "--module-first"])
        subprocess.run([sphinx_apidoc, "--output-dir", "source", "tools", "--separate", "--module-first"])
        print("Initial documentation generated for molass and tools.")

    # Make HTML documentation
    subprocess.run([make, "html"])
    print("HTML documentation generated.")

    # Deploy the documentation to GitHub Pages
    subprocess.run([ghp_import, "-n", "-p", "-f", "_build/html"])
    print("Documentation deployed to GitHub Pages.")

if __name__ == "__main__":
    main()