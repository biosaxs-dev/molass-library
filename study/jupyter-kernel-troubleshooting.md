# Jupyter Kernel Troubleshooting Guide

## Problem: "ipykernel package required" Error Loop

### Symptoms
- VS Code shows: "Running cells with 'Python X.XX' requires the ipykernel package to be installed or requires an update"
- Clicking "Install" causes an installation loop
- Error persists even after installing ipykernel
- Kernel crashes with import errors like: `ImportError: zmq Cython backend has not been compiled`

### Root Cause
Multiple Python installations on the same system with ambiguous Jupyter kernel specifications, causing:
- Kernel starts with one Python version
- But tries to import modules from a different Python version
- Results in version mismatch and import failures

---

## Diagnosis Steps

### 1. Check Python Installations
```powershell
where.exe python
```
This shows all Python executables in your PATH. Look for multiple versions.

### 2. Verify Which Python You're Using
```powershell
python -V
```

### 3. Check ipykernel Installation
```powershell
# For system Python
python -m pip show ipykernel

# For specific Python installation
& "C:\Program Files\Python313\python.exe" -m pip show ipykernel
```

### 4. List Jupyter Kernel Specs
```powershell
# Using default Python
python -m jupyter kernelspec list

# Using specific Python
& "C:\Program Files\Python313\python.exe" -m jupyter kernelspec list
```

### 5. Inspect Kernel Configuration
```powershell
# Check the kernel.json file
Get-Content "C:\Users\<USERNAME>\AppData\Roaming\Python\share\jupyter\kernels\python3\kernel.json"
```

Look for the `"argv"` field - if it just says `"python"` instead of a full path, that's the problem!

---

## Solution

### Step 1: Update Kernel Spec to Use Explicit Path

**Replace the generic kernel spec:**

```powershell
# Create updated kernel.json with explicit Python path
$json = @'
{
 "argv": [
  "C:\\Program Files\\Python313\\python.exe",
  "-m",
  "ipykernel_launcher",
  "-f",
  "{connection_file}"
 ],
 "display_name": "Python 3.13.11",
 "language": "python",
 "metadata": {
  "debugger": true
 }
}
'@

# Write to kernel spec file
$json | Out-File -Encoding utf8 "C:\Users\$env:USERNAME\AppData\Roaming\Python\share\jupyter\kernels\python3\kernel.json"
```

**Important:** Replace `C:\\Program Files\\Python313\\python.exe` with your actual Python path. Use double backslashes (`\\`) in the JSON.

### Step 2: Clear Jupyter and VS Code Caches

```powershell
# Clear Jupyter runtime cache
Remove-Item -Path "$env:APPDATA\jupyter\runtime\*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Jupyter runtime cache cleared"

# Clear VS Code Jupyter extension cache
Remove-Item -Path "$env:APPDATA\Code - Insiders\User\globalStorage\ms-toolsai.jupyter\*" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "VS Code Jupyter cache cleared"

# For regular VS Code (not Insiders)
Remove-Item -Path "$env:APPDATA\Code\User\globalStorage\ms-toolsai.jupyter\*" -Recurse -Force -ErrorAction SilentlyContinue
```

### Step 3: Reinstall ipykernel (if needed)

```powershell
# Install/reinstall ipykernel with correct Python
& "C:\Program Files\Python313\python.exe" -m pip install --upgrade --force-reinstall ipykernel pyzmq jupyter-client
```

### Step 4: Register the Kernel (Optional)

```powershell
# Register Python as a Jupyter kernel with a specific name
& "C:\Program Files\Python313\python.exe" -m ipykernel install --user --name python313 --display-name "Python 3.13"
```

### Step 5: Restart VS Code

1. Close VS Code completely
2. Reopen VS Code
3. Open your notebook

### Step 6: Select the Correct Kernel

When the error dialog appears:

❌ **DO NOT** click "Install"  
✅ **DO** click "Change Kernel"

Then:
1. Select "Select Another Kernel..."
2. Choose "Python Environments..."
3. Select the one showing your Python path (e.g., `C:\Program Files\Python313\python.exe`)
4. Click "Allow" when prompted

**Note for VS Code Insiders:** If Python kernels don't appear in the initial picker:
1. First select any available kernel (e.g., a conda environment) to start Jupyter
2. Click the kernel name in the top-right corner
3. Select "Select Another Kernel..."
4. Choose "Existing Jupyter Server..."
5. Your Python kernel should now appear in the list

---

## Optional: Configure VS Code to Prefer Specific Python

Add to VS Code settings (File → Preferences → Settings → Edit settings.json):

```json
{
    "jupyter.kernels.filter": [
        {
            "path": "C:\\Program Files\\Python313\\python.exe",
            "type": "pythonEnvironment"
        }
    ]
}
```

---

## Verification

After fixing, verify the kernel works:

```powershell
# Test kernel directly
& "C:\Program Files\Python313\python.exe" -m ipykernel_launcher --version

# Verify imports work
& "C:\Program Files\Python313\python.exe" -c "import ipykernel; import zmq; print('Success!')"
```

In VS Code:
1. Open a notebook
2. Create a new cell with: `import sys; print(sys.executable)`
3. Run the cell
4. Verify it shows your intended Python path

---

## Common Mistakes to Avoid

1. ❌ **Clicking "Install"** in the error dialog → Creates installation loop
2. ❌ **Using relative paths** in kernel.json → Ambiguous resolution
3. ❌ **Not clearing caches** → Old connections persist
4. ❌ **Installing into wrong Python** → Mismatch continues
5. ❌ **Not using double backslashes** in JSON paths → Invalid JSON

---

## Platform-Specific Notes

### Windows
- Use double backslashes `\\` in JSON paths
- PowerShell commands shown above
- AppData location: `C:\Users\<USERNAME>\AppData\Roaming`

### Linux/macOS
```bash
# Update kernel spec
nano ~/.local/share/jupyter/kernels/python3/kernel.json

# Change "python" to full path like:
# "/usr/bin/python3.13" or "/opt/homebrew/bin/python3"

# Clear caches
rm -rf ~/.local/share/jupyter/runtime/*
rm -rf ~/.config/Code/User/globalStorage/ms-toolsai.jupyter/*

# Reinstall
/usr/bin/python3.13 -m pip install --upgrade --force-reinstall ipykernel
```

---

## Prevention

To avoid this issue in the future:

1. **Use virtual environments** for projects instead of system Python
2. **Always specify full paths** in kernel specs when multiple Python versions exist
3. **Register kernels explicitly** with unique names:
   ```powershell
   python -m ipykernel install --user --name myenv --display-name "My Project (Python 3.13)"
   ```
4. **Document which Python** each project uses
5. **Prefer "Change Kernel"** over "Install" in VS Code dialogs

---

## Troubleshooting Checklist

- [ ] Multiple Python installations identified
- [ ] Kernel spec inspected (check for `"python"` vs full path)
- [ ] ipykernel installed in correct Python
- [ ] Jupyter cache cleared
- [ ] VS Code cache cleared
- [ ] VS Code completely restarted
- [ ] Kernel manually selected via "Change Kernel"
- [ ] Test cell executed successfully

---

## Related Issues

This solution also fixes:
- `ModuleNotFoundError: No module named 'ipykernel'`
- `ImportError: DLL load failed` (Windows)
- `The kernel died. Error: ...` with import errors
- Kernel crashes immediately after starting
- "Jupyter server not started" when kernel is the issue

---

## Additional Resources

- [Jupyter Kernel Specs Documentation](https://jupyter-client.readthedocs.io/en/stable/kernels.html)
- [IPython Installation Guide](https://ipython.readthedocs.io/en/stable/install/kernel_install.html)
- [VS Code Python Environments](https://code.visualstudio.com/docs/python/environments)

---

**Last Updated:** December 27, 2025  
**Tested On:** Windows 11, VS Code Insiders, Python 3.13.11
