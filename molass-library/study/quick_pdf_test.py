import sys
print(f"Python version: {sys.version}")

try:
    import pypdf
    print(f"pypdf is installed: version {pypdf.__version__}")
except ImportError:
    print("pypdf is NOT installed")

try:
    import PyPDF2
    print(f"PyPDF2 is installed: version {PyPDF2.__version__}")
except ImportError:
    print("PyPDF2 is NOT installed")
