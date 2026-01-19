# Tools

This directory contains utility scripts used for preparing materials for the modeling vs model-free SEC-SAXS discussion.

---

## Python Environment Policy

**This project uses the GLOBAL Python 3.13.11 environment** - NO virtual environments (.venv).

### Rationale:
- Simple analysis/discussion project with minimal dependencies
- Single-user workstation with controlled global environment
- `pypdf` already installed in global Python
- Avoids complexity of venv management for lightweight work

### Windows-Specific Python Execution Notes

⚠️ **CRITICAL for Copilot/Future Users:**

1. **Correct Python Executable:**
   ```powershell
   & "C:\Program Files\Python313\python.exe" script.py
   ```
   - Windows Store Python launcher (`C:\Windows\System32\python`) is in PATH but not functional for our purposes
   - Always use the **full path** with `&` call operator in PowerShell

2. **PowerShell Syntax:**
   - Paths with spaces require quotes AND the `&` operator
   - ❌ WRONG: `"C:\Program Files\Python313\python.exe" script.py` (syntax error)
   - ✅ CORRECT: `& "C:\Program Files\Python313\python.exe" script.py`

3. **Checking Python Location:**
   ```powershell
   where.exe python
   # Output shows:
   # C:\Windows\System32\python          ← Windows Store launcher (avoid)
   # C:\Program Files\Python313\python.exe ← USE THIS
   ```

4. **Output Buffering Issue:**
   - Python output may not appear in terminal due to PowerShell buffering
   - Add `flush=True` to all `print()` statements for reliable output
   - Use `-u` flag for unbuffered output: `python -u script.py`

---

## `read_pdfs.py`

Python script to extract text content from PDF papers in the `reference_papers/` folder.

**Requirements:** `pypdf` (already installed in Python 3.13.11 global environment)

**Usage:**
```powershell
cd E:\GitHub\modeling-vs-model_free
& "C:\Program Files\Python313\python.exe" tools\read_pdfs.py
```

**Output:** `tools/extracted_papers.txt` - Full text extraction of both reference papers for analysis and discussion preparation.

### Papers Processed:
- **Paper 1:** Meisburger et al. (2021) - REGALS method for model-free SEC-SAXS deconvolution
- **Paper 2:** Chure & Cremer (2024) - hplc-py for model-based chromatogram quantification
