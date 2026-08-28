from .pdf_processor import extract_text_from_pdf
from .ocr_processor import extract_text_from_image, extract_text_from_scanned_pdf, TesseractNotInstalledError
from .text_cleaner import clean_text

def process_document(file_bytes: bytes, file_name: str) -> dict:
    """
    Processes a PDF or image document and returns a structured dictionary representing the document data.
    Conforms to the following format:
    {
        "success": bool,
        "file_name": str,
        "file_type": str,
        "total_pages": int,
        "ocr_used": bool,
        "pages": [{"page_number": int, "text": str}],
        "full_text": str,
        "error": str (optional)
    }
    """
    # 1. Validation
    if not file_name:
        return {
            "success": False,
            "error": "File name is missing or empty.",
            "file_name": "",
            "file_type": "",
            "total_pages": 0,
            "ocr_used": False,
            "pages": [],
            "full_text": ""
        }
        
    ext = file_name.split('.')[-1].lower()
    
    if ext not in ['pdf', 'png', 'jpg', 'jpeg']:
        return {
            "success": False,
            "error": f"Unsupported file type: .{ext}. Supported types: PDF, PNG, JPG, JPEG.",
            "file_name": file_name,
            "file_type": ext,
            "total_pages": 0,
            "ocr_used": False,
            "pages": [],
            "full_text": ""
        }
        
    if not file_bytes or len(file_bytes) == 0:
        return {
            "success": False,
            "error": "The uploaded file is empty or missing content.",
            "file_name": file_name,
            "file_type": ext,
            "total_pages": 0,
            "ocr_used": False,
            "pages": [],
            "full_text": ""
        }
        
    # File size limit check (e.g. 20MB)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    if len(file_bytes) > MAX_FILE_SIZE:
        return {
            "success": False,
            "error": f"File exceeds the maximum size limit of 20MB (Size: {len(file_bytes)/(1024*1024):.2f}MB).",
            "file_name": file_name,
            "file_type": ext,
            "total_pages": 0,
            "ocr_used": False,
            "pages": [],
            "full_text": ""
        }

    pages = []
    ocr_used = False
    
    try:
        if ext == 'pdf':
            import fitz
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to parse PDF document. It may be corrupted. Error: {str(e)}",
                    "file_name": file_name,
                    "file_type": ext,
                    "total_pages": 0,
                    "ocr_used": False,
                    "pages": [],
                    "full_text": ""
                }
                
            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                return {
                    "success": False,
                    "error": "The PDF document contains no pages.",
                    "file_name": file_name,
                    "file_type": ext,
                    "total_pages": 0,
                    "ocr_used": False,
                    "pages": [],
                    "full_text": ""
                }
                
            for idx in range(total_pages):
                page = doc[idx]
                page_text = page.get_text("text", sort=True)
                cleaned_text = clean_text(page_text)
                
                # Check if page has sufficient text. If not, trigger OCR fallback for this page
                if len(cleaned_text.strip()) < 50:
                    try:
                        # Render page as PNG image bytes
                        pix = page.get_pixmap(dpi=300)
                        png_bytes = pix.tobytes("png")
                        
                        ocr_text = extract_text_from_image(png_bytes)
                        cleaned_text = clean_text(ocr_text)
                        ocr_used = True
                    except TesseractNotInstalledError as t_err:
                        doc.close()
                        return {
                            "success": False,
                            "error": str(t_err),
                            "file_name": file_name,
                            "file_type": ext,
                            "total_pages": 0,
                            "ocr_used": False,
                            "pages": [],
                            "full_text": ""
                        }
                    except Exception as e:
                        # If image conversion or unexpected OCR error occurs, log it and keep whatever text was there (or empty)
                        import logging
                        logging.error(f"Error during page-level OCR on page {idx + 1}: {e}")
                
                pages.append({
                    "page_number": idx + 1,
                    "text": cleaned_text
                })
            
            doc.close()
            
        elif ext in ['png', 'jpg', 'jpeg']:
            try:
                # Validate image is openable and not corrupted
                from PIL import Image
                import io
                Image.open(io.BytesIO(file_bytes)).verify()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to parse image file. It may be corrupted. Error: {str(e)}",
                    "file_name": file_name,
                    "file_type": ext,
                    "total_pages": 0,
                    "ocr_used": False,
                    "pages": [],
                    "full_text": ""
                }
                
            try:
                text = extract_text_from_image(file_bytes)
                cleaned_text = clean_text(text)
                ocr_used = True
                pages.append({
                    "page_number": 1,
                    "text": cleaned_text
                })
            except TesseractNotInstalledError as t_err:
                return {
                    "success": False,
                    "error": str(t_err),
                    "file_name": file_name,
                    "file_type": ext,
                    "total_pages": 0,
                    "ocr_used": False,
                    "pages": [],
                    "full_text": ""
                }
                
        # Calculate full_text
        full_text = "\n\n".join(page["text"] for page in pages)
        
        return {
            "success": True,
            "file_name": file_name,
            "file_type": ext,
            "total_pages": len(pages),
            "ocr_used": ocr_used,
            "pages": pages,
            "full_text": full_text
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"An unexpected error occurred during document processing: {str(e)}",
            "file_name": file_name,
            "file_type": ext,
            "total_pages": 0,
            "ocr_used": False,
            "pages": [],
            "full_text": ""
        }

