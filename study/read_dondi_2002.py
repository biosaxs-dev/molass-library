"""
PDF Reader for analyzing chromatography papers
"""
from pypdf import PdfReader
import re

def read_pdf(pdf_path):
    """Read all pages from a PDF file"""
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    
    all_text = []
    for i in range(num_pages):
        page_text = reader.pages[i].extract_text()
        all_text.append({
            'page': i + 1,
            'text': page_text
        })
    
    return all_text, num_pages

def search_in_pdf(pages_data, keyword, context_chars=300):
    """Search for keyword in PDF and return context"""
    results = []
    for page_data in pages_data:
        text = page_data['text']
        page_num = page_data['page']
        
        # Case insensitive search
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        matches = pattern.finditer(text)
        
        for match in matches:
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end]
            results.append({
                'page': page_num,
                'context': context,
                'position': match.start()
            })
    
    return results

if __name__ == "__main__":
    # Read Dondi 2002 paper
    pdf_path = r"E:\GitHub\molass-library\study\2002, Francesco Dondi.pdf"
    
    print("Reading PDF...")
    pages, num_pages = read_pdf(pdf_path)
    print(f"Loaded {num_pages} pages\n")
    
    # Search for GEC-related content
    keywords = [
        "GEC",
        "General Equation of Chromatography",
        "monopore",
        "mono-pore"
    ]
    
    print("=" * 80)
    print("Searching for GEC Monopore Model")
    print("=" * 80)
    
    for keyword in keywords:
        results = search_in_pdf(pages, keyword, context_chars=200)
        if results:
            print(f"\n\nKeyword: '{keyword}' - Found {len(results)} occurrences")
            print("-" * 80)
            for i, result in enumerate(results[:3]):  # Show first 3 occurrences
                print(f"\n[Page {result['page']}, Occurrence {i+1}]")
                print(result['context'])
