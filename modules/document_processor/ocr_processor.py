import io
import logging
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps
import pytesseract
from .text_cleaner import clean_text

class TesseractNotInstalledError(Exception):
    """Raised when the tesseract binary is not installed or not found on PATH."""
    pass

_tesseract_verified = None

def verify_tesseract():
    """Verifies that tesseract is available in the environment."""
    global _tesseract_verified
    if _tesseract_verified is not None:
        if not _tesseract_verified:
            raise TesseractNotInstalledError(
                "Tesseract OCR is not found on your system. Please install Tesseract "
                "and add it to your system PATH, or specify the binary location in the TESSERACT_CMD environment variable."
            )
        return

    try:
        pytesseract.get_tesseract_version()
        _tesseract_verified = True
    except Exception as e:
        _tesseract_verified = False
        logging.error(f"Tesseract is not installed or not configured correctly: {e}")
        raise TesseractNotInstalledError(
            "Tesseract OCR is not found on your system. Please install Tesseract "
            "and add it to your system PATH, or specify the binary location in the TESSERACT_CMD environment variable."
        )

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Applies image processing steps (grayscale, dynamic autocontrast, contrast boosting,
    sharpness enhancement) to optimize text clarity and preserve financial numbers/tables for OCR.
    """
    # 1. Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')
    
    # 2. Rescale image if low resolution to improve small print accuracy
    if image.width < 1800:
        factor = max(2.0, 1800.0 / image.width)
        new_size = (int(image.width * factor), int(image.height * factor))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        
    # 3. Dynamic autocontrast to balance histogram
    image = ImageOps.autocontrast(image, cutoff=1)
    
    # 4. Moderate contrast boost to preserve faint text without clipping fine print
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.8)
    
    # 5. Sharpness enhancement to make numbers, decimals, and symbols crisp
    sharpener = ImageEnhance.Sharpness(image)
    image = sharpener.enhance(1.6)
    
    return image

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Runs Tesseract OCR on a raw image stream after advanced preprocessing.
    """
    verify_tesseract()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = preprocess_image_for_ocr(image)
        # Try page segmentation mode 6 (uniform block of text) with fallback to default
        try:
            text = pytesseract.image_to_string(image, config='--psm 6 --oem 3')
            if len(text.strip()) < 10:
                text = pytesseract.image_to_string(image, config='--psm 3 --oem 3')
        except Exception:
            text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error during OCR extraction of image: {e}")
        raise e

def extract_text_from_scanned_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Converts a scanned PDF into page images, preprocesses them, and runs OCR on each page.
    Returns: list of dicts: [{"page_number": 1, "text": "..."}]
    """
    verify_tesseract()
    pages = []
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for idx, page in enumerate(doc):
            # Render page to PNG pixmap at 300 DPI (better OCR accuracy for small print)
            pix = page.get_pixmap(dpi=300)
            png_bytes = pix.tobytes("png")
            
            # Load into Pillow, preprocess, and perform OCR
            ocr_text = extract_text_from_image(png_bytes)
            cleaned_text = clean_text(ocr_text)
            
            pages.append({
                "page_number": idx + 1,
                "text": cleaned_text
            })
            
        doc.close()
    except Exception as e:
        logging.error(f"Error during OCR extraction of PDF: {e}")
        raise e
        
    return pages

