import sys
from pathlib import Path

try:
    from pypdf import PdfReader
    print("pypdf imported successfully", flush=True)
    
    # Define base path (script is in tools/, reference_papers/ is at root)
    base_path = Path(__file__).parent.parent
    ref_papers = base_path / 'reference_papers'
    
    # Papers to extract (for understanding EFA, REGALS, EFAMIX, CHROMIX)
    papers = [
        '1988, Marcel Maeder.pdf',  # Original EFA paper
        '1991, H.R. Keller.pdf',     # EFA development
        '2018, Alejandro Panjkovich.pdf',  # CHROMIXS
        '2021, Petr V. Konarev.pdf',  # EFAMIX
        '2021, Steve P. Meisburger.pdf',  # REGALS
        '2024, Jesse B. Hopkins.pdf'  # BioXTAS RAW
    ]
    
    extracted_texts = []
    
    for paper_file in papers:
        paper_path = ref_papers / paper_file
        if not paper_path.exists():
            print(f"WARNING: {paper_file} not found, skipping...", flush=True)
            continue
            
        print(f"Reading {paper_file}...", flush=True)
        reader = PdfReader(str(paper_path))
        text = '\n'.join([page.extract_text() for page in reader.pages])
        print(f"  {len(reader.pages)} pages, {len(text)} chars", flush=True)
        
        extracted_texts.append((paper_file, text))
    
    # Write to file in tools folder
    output_path = base_path / 'tools' / 'extracted_papers.txt'
    print(f"Writing to {output_path}...", flush=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, (paper_file, text) in enumerate(extracted_texts, 1):
            f.write(f"PAPER {i}: {paper_file[:-4]}\n")  # Remove .pdf extension
            f.write("=" * 80 + "\n\n")
            f.write(text)
            f.write("\n\n\n")
    
    print(f"SUCCESS! Extracted {len(extracted_texts)} papers to tools/extracted_papers.txt", flush=True)
    
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
