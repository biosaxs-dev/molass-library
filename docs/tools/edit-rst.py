import os

docs_dir = "."  # Path to your docs directory

for root, _, files in os.walk(docs_dir):
    for file in files:
        if file.endswith(".rst"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.readlines()

            # Update the title line
            updated_content = []
            for line in content:
                if line.strip().startswith("molass."):
                    line = line.replace("molass.", "")
                updated_content.append(line)

            # Write the updated content back to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(updated_content)