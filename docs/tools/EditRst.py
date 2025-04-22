"""
This script edits all .rst files in the docs directory to update the title lines.

See also: `"Modify *.rst files" <LINK1_>`__.

.. _LINK1: https://nshimizu0721.github.io/molass-develop/chapters/07/documentation.html#modify-rst-files

"""
import os

docs_dir = "./source"

for root, _, files in os.walk(docs_dir):
    for file in files:
        if file.endswith(".rst"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.readlines()

            # Update the title line
            updated_content = []
            for line in content:
                if line.startswith("molass."):
                    line = line.replace("molass.", "").replace(" package", "").replace(" module", "")
                elif line.startswith("Subpackages"):
                    line = line.replace("Subpackages", "Submodules")
                updated_content.append(line)

            # Write the updated content back to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(updated_content)

print("All .rst files have been updated.")
# This script will walk through all the .rst files in the docs directory and update the title lines as specified.