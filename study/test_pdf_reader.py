"""
Test script to verify PDF reading capabilities
"""

def test_pypdf():
    """Test pypdf package"""
    try:
        import pypdf
        print(f"✓ pypdf version: {pypdf.__version__}")
        print(f"  Available: PdfReader, PdfWriter")
        return True, 'pypdf'
    except ImportError as e:
        print(f"✗ pypdf not available: {e}")
        return False, None

def test_pypdf2():
    """Test PyPDF2 package (alternative)"""
    try:
        import PyPDF2
        print(f"✓ PyPDF2 version: {PyPDF2.__version__}")
        print(f"  Available: PdfReader, PdfWriter")
        return True, 'PyPDF2'
    except ImportError as e:
        print(f"✗ PyPDF2 not available: {e}")
        return False, None

def test_pdfplumber():
    """Test pdfplumber package (alternative)"""
    try:
        import pdfplumber
        print(f"✓ pdfplumber version: {pdfplumber.__version__}")
        print(f"  Available: Higher-level text extraction")
        return True, 'pdfplumber'
    except ImportError as e:
        print(f"✗ pdfplumber not available: {e}")
        return False, None

def test_pymupdf():
    """Test PyMuPDF/fitz package (alternative)"""
    try:
        import fitz
        print(f"✓ PyMuPDF (fitz) version: {fitz.version[0]}")
        print(f"  Available: Fast PDF processing with images")
        return True, 'pymupdf'
    except ImportError as e:
        print(f"✗ PyMuPDF not available: {e}")
        return False, None

if __name__ == "__main__":
    print("=" * 60)
    print("Testing PDF Reading Packages")
    print("=" * 60)
    
    results = []
    
    print("\n1. Testing pypdf:")
    results.append(test_pypdf())
    
    print("\n2. Testing PyPDF2 (alternative):")
    results.append(test_pypdf2())
    
    print("\n3. Testing pdfplumber (alternative):")
    results.append(test_pdfplumber())
    
    print("\n4. Testing PyMuPDF/fitz (alternative):")
    results.append(test_pymupdf())
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    available = [pkg for success, pkg in results if success]
    
    if available:
        print(f"\n✓ Available packages: {', '.join(available)}")
        print(f"\nRecommendation: Using '{available[0]}' for PDF reading")
        
        if available[0] == 'pypdf':
            print("\nBasic usage example:")
            print("  from pypdf import PdfReader")
            print("  reader = PdfReader('file.pdf')")
            print("  text = reader.pages[0].extract_text()")
    else:
        print("\n✗ No PDF reading packages found.")
        print("\nTo install pypdf, run:")
        print("  pip install pypdf")
