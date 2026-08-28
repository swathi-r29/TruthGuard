import fitz  # PyMuPDF
from .text_cleaner import clean_text

def extract_text_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Extracts text page-by-page from a standard PDF file using PyMuPDF.
    Returns: list of dicts: [{"page_number": 1, "text": "..."}]
    """
    pages = []
    
    try:
        # Open PDF from bytes stream
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for idx, page in enumerate(doc):
            page_text = page.get_text("text", sort=True)
            cleaned_text = clean_text(page_text)
            
            pages.append({
                "page_number": idx + 1,
                "text": cleaned_text
            })
            
        doc.close()
    except Exception as e:
        # Handle exceptions gracefully and return whatever pages were processed or raise
        import logging
        logging.error(f"Error extracting text from PDF: {e}")
        raise e
        
    return pages
