import io
import logging
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
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
    Applies image processing steps (grayscale, contrast enhancement, thresholding)
    to optimize text clarity for Tesseract OCR.
    """
    # 1. Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')
    
    # 2. Resize to double resolution if it's a small image (to improve small print accuracy)
    if image.width < 1500:
        factor = 2.0
        new_size = (int(image.width * factor), int(image.height * factor))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        
    # 3. Boost contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # 4. Binarization (thresholding) to create sharp black-and-white image
    image = image.point(lambda p: 255 if p > 127 else 0, '1')
    
    return image

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Runs Tesseract OCR on a raw image stream after preprocessing.
    """
    verify_tesseract()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = preprocess_image_for_ocr(image)
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
            image = Image.open(io.BytesIO(png_bytes))
            image = preprocess_image_for_ocr(image)
            text = pytesseract.image_to_string(image)
            cleaned_text = clean_text(text)
            
            pages.append({
                "page_number": idx + 1,
                "text": cleaned_text
            })
            
        doc.close()
    except Exception as e:
        logging.error(f"Error during OCR extraction of PDF: {e}")
        raise e
        
    return pages
