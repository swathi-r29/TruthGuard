import unittest
from unittest.mock import patch, MagicMock
import io
import fitz  # PyMuPDF
from PIL import Image
from modules.document_processor import process_document
from modules.document_processor.ocr_processor import TesseractNotInstalledError
from modules.document_processor.text_cleaner import clean_text

class TestDocumentProcessor(unittest.TestCase):
    
    def setUp(self):
        import modules.document_processor.ocr_processor as ocr
        ocr._tesseract_verified = None

    def test_text_cleaner(self):
        text = "Hello    World!   \n\n\n\nNew Paragraph with spaces.   "
        cleaned = clean_text(text)
        self.assertEqual(cleaned, "Hello World!\n\nNew Paragraph with spaces.")

    def test_text_cleaner_preserves_financials(self):
        # Test cleaning preserves important financial info
        text = "Loan Amount: ₹2,00,000 \n Interest Rate: 18.5% \n Foreclosure Fee: Rs. 5,000 (4%)"
        cleaned = clean_text(text)
        self.assertIn("₹2,00,000", cleaned)
        self.assertIn("18.5%", cleaned)
        self.assertIn("Rs. 5,000", cleaned)
        self.assertIn("4%", cleaned)

    def test_test_a_text_pdf(self):
        """Test A — Text PDF: success = True, ocr_used = False, text extracted, page numbers preserved."""
        # Create in-memory PDF with enough text to avoid triggering OCR fallback (> 50 chars)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), 
            "LENDER: DEBT DETOX SAMPLE BANK AGREEMENT. "
            "Loan Amount: Rs. 2,00,000. "
            "Interest Rate: 18% per annum. "
            "This is a standard text-based PDF document page used for automated testing purposes."
        )
        pdf_bytes = doc.write()
        doc.close()

        res = process_document(pdf_bytes, "loan.pdf")
        self.assertTrue(res["success"])
        self.assertEqual(res["file_name"], "loan.pdf")
        self.assertEqual(res["file_type"], "pdf")
        self.assertEqual(res["total_pages"], 1)
        self.assertFalse(res["ocr_used"])
        self.assertEqual(len(res["pages"]), 1)
        self.assertEqual(res["pages"][0]["page_number"], 1)
        self.assertIn("Rs. 2,00,000", res["pages"][0]["text"])
        self.assertIn("18%", res["pages"][0]["text"])
        self.assertIn("Rs. 2,00,000", res["full_text"])

    def test_test_b_multi_page_pdf(self):
        """Test B — Multi-page PDF: correct total_pages, every page preserved, correct page numbering."""
        # Create multi-page PDF where each page has > 50 chars to avoid OCR fallback
        doc = fitz.open()
        p1 = doc.new_page()
        p1.insert_text((72, 72), "Page One Contents: Loan Agreement details and definitions. This page contains introductory terms.")
        p2 = doc.new_page()
        p2.insert_text((72, 72), "Page Two Contents: Terms & Conditions, payment schedules, and list of applicable processing fees.")
        p3 = doc.new_page()
        p3.insert_text((72, 72), "Page Three Contents: Signatures, witness fields, and execution clauses for both lender and borrower.")
        pdf_bytes = doc.write()
        doc.close()

        res = process_document(pdf_bytes, "agreement.pdf")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_pages"], 3)
        self.assertEqual(len(res["pages"]), 3)
        self.assertEqual(res["pages"][0]["page_number"], 1)
        self.assertEqual(res["pages"][1]["page_number"], 2)
        self.assertEqual(res["pages"][2]["page_number"], 3)
        self.assertIn("Page One", res["pages"][0]["text"])
        self.assertIn("Page Two", res["pages"][1]["text"])
        self.assertIn("Page Three", res["pages"][2]["text"])

    @patch('modules.document_processor.ocr_processor.pytesseract.get_tesseract_version')
    @patch('modules.document_processor.ocr_processor.pytesseract.image_to_string')
    def test_test_c_scanned_pdf(self, mock_image_to_string, mock_get_tesseract_version):
        """Test C — Scanned PDF: OCR activated, text extracted, ocr_used = True."""
        mock_get_tesseract_version.return_value = "0.3.13"
        mock_image_to_string.return_value = "Scanned Page OCR Text: Interest Rate: 18%."

        # Create a PDF page that will have insufficient selectable text (empty text)
        doc = fitz.open()
        doc.new_page()  # Blank page
        pdf_bytes = doc.write()
        doc.close()

        res = process_document(pdf_bytes, "scanned_doc.pdf")
        self.assertTrue(res["success"])
        self.assertTrue(res["ocr_used"])
        self.assertEqual(res["total_pages"], 1)
        self.assertIn("Interest Rate: 18%", res["pages"][0]["text"])
        mock_image_to_string.assert_called_once()

    @patch('modules.document_processor.ocr_processor.pytesseract.get_tesseract_version')
    @patch('modules.document_processor.ocr_processor.pytesseract.image_to_string')
    def test_test_d_image(self, mock_image_to_string, mock_get_tesseract_version):
        """Test D — Image: OCR activated, text extracted for PNG/JPG."""
        mock_get_tesseract_version.return_value = "0.3.13"
        mock_image_to_string.return_value = "OCR Text from Image: Rs. 2,00,000 and 18%."

        # Create a small valid image in memory
        img = Image.new("RGB", (50, 50), color="white")
        img_io = io.BytesIO()
        img.save(img_io, format="PNG")
        img_bytes = img_io.getvalue()

        # Test PNG
        res_png = process_document(img_bytes, "screenshot.png")
        self.assertTrue(res_png["success"])
        self.assertTrue(res_png["ocr_used"])
        self.assertEqual(res_png["total_pages"], 1)
        self.assertIn("Rs. 2,00,000", res_png["pages"][0]["text"])

        # Test JPG
        img_io_jpg = io.BytesIO()
        img.save(img_io_jpg, format="JPEG")
        jpg_bytes = img_io_jpg.getvalue()
        res_jpg = process_document(jpg_bytes, "photo.jpg")
        self.assertTrue(res_jpg["success"])
        self.assertTrue(res_jpg["ocr_used"])
        self.assertIn("18%", res_jpg["pages"][0]["text"])

    def test_test_e_invalid_empty_or_corrupted(self):
        """Test E — Empty/invalid document: graceful failure, human-readable error."""
        # Test 1: Empty file
        res_empty = process_document(b"", "empty.pdf")
        self.assertFalse(res_empty["success"])
        self.assertIn("empty", res_empty["error"].lower())

        # Test 2: Unsupported extension
        res_unsupported = process_document(b"some content", "text.txt")
        self.assertFalse(res_unsupported["success"])
        self.assertIn("unsupported", res_unsupported["error"].lower())

        # Test 3: Corrupted PDF
        res_corrupt_pdf = process_document(b"random bytes that do not make a pdf", "corrupt.pdf")
        self.assertFalse(res_corrupt_pdf["success"])
        self.assertIn("corrupted", res_corrupt_pdf["error"].lower())

        # Test 4: Corrupted Image
        res_corrupt_img = process_document(b"random bytes that do not make an image", "corrupt.jpg")
        self.assertFalse(res_corrupt_img["success"])
        self.assertIn("corrupted", res_corrupt_img["error"].lower())

    @patch('modules.document_processor.ocr_processor.pytesseract.get_tesseract_version')
    def test_test_e_tesseract_unavailable(self, mock_get_tesseract_version):
        """Test E (continued) — Tesseract unavailable: returns human-readable error instead of crashing."""
        # Force verify_tesseract to raise an exception indicating it is not installed
        mock_get_tesseract_version.side_effect = Exception("tesseract executable not found")

        # Create a small valid image in memory
        img = Image.new("RGB", (50, 50), color="white")
        img_io = io.BytesIO()
        img.save(img_io, format="PNG")
        img_bytes = img_io.getvalue()

        # Processing should fail gracefully
        res = process_document(img_bytes, "doc.png")
        self.assertFalse(res["success"])
        self.assertIn("Tesseract OCR is not found", res["error"])

    def test_test_f_financial_text_preservation(self):
        """Test F — Financial text preservation: values, symbols, terminology survive extraction and cleaning."""
        doc = fitz.open()
        page = doc.new_page()
        financial_content = (
            "DEBT DETOX SAMPLE BANK\n"
            "Personal Loan Agreement\n"
            "Loan Amount: Rs. 2,00,000\n"
            "Interest Rate: 18% per annum\n"
            "Processing Fee: 2% of sanctioned amount\n"
            "Insurance Premium: Rs. 3,500\n"
            "Foreclosure Charge: 4% of outstanding principal\n"
            "Late Payment Fee: Rs. 500 per occurrence\n"
            "GST: Applicable on eligible charges"
        )
        page.insert_text((72, 72), financial_content)
        pdf_bytes = doc.write()
        doc.close()

        res = process_document(pdf_bytes, "synthetic_loan.pdf")
        self.assertTrue(res["success"])
        
        text = res["full_text"]
        self.assertIn("Rs. 2,00,000", text)
        self.assertIn("18%", text)
        self.assertIn("2%", text)
        self.assertIn("Rs. 3,500", text)
        self.assertIn("4%", text)
        self.assertIn("Rs. 500", text)
        self.assertIn("Foreclosure Charge", text)
        self.assertIn("Late Payment Fee", text)

    @patch('modules.document_processor.ocr_processor.pytesseract.get_tesseract_version')
    @patch('modules.document_processor.ocr_processor.pytesseract.image_to_string')
    def test_scanned_multipage_pdf(self, mock_image_to_string, mock_get_tesseract_version):
        """Test multi-page scanned PDF triggers OCR on all pages and preserves page structure."""
        mock_get_tesseract_version.return_value = "0.3.13"
        mock_image_to_string.side_effect = [
            "Scanned Page 1: Loan Amount ₹5,00,000.",
            "Scanned Page 2: Late Payment Penalty Rs. 1,000."
        ]

        doc = fitz.open()
        doc.new_page()  # Blank page 1
        doc.new_page()  # Blank page 2
        pdf_bytes = doc.write()
        doc.close()

        res = process_document(pdf_bytes, "scanned_multipage.pdf")
        self.assertTrue(res["success"])
        self.assertTrue(res["ocr_used"])
        self.assertEqual(res["total_pages"], 2)
        self.assertEqual(len(res["pages"]), 2)
        self.assertIn("₹5,00,000", res["pages"][0]["text"])
        self.assertIn("Rs. 1,000", res["pages"][1]["text"])

    @patch('modules.document_processor.ocr_processor.pytesseract.get_tesseract_version')
    @patch('modules.document_processor.ocr_processor.pytesseract.image_to_string')
    def test_jpeg_and_png_image_inputs(self, mock_image_to_string, mock_get_tesseract_version):
        """Test JPEG, JPG, and PNG image input handling."""
        mock_get_tesseract_version.return_value = "0.3.13"
        mock_image_to_string.return_value = "Extracted Image Content: Processing Fee 1.5%."

        img = Image.new("RGB", (100, 100), color="white")
        
        # Test JPEG
        img_io_jpeg = io.BytesIO()
        img.save(img_io_jpeg, format="JPEG")
        res_jpeg = process_document(img_io_jpeg.getvalue(), "scan.jpeg")
        self.assertTrue(res_jpeg["success"])
        self.assertTrue(res_jpeg["ocr_used"])
        self.assertEqual(res_jpeg["file_type"], "jpeg")
        self.assertIn("1.5%", res_jpeg["full_text"])

        # Test PNG
        img_io_png = io.BytesIO()
        img.save(img_io_png, format="PNG")
        res_png = process_document(img_io_png.getvalue(), "scan.png")
        self.assertTrue(res_png["success"])
        self.assertTrue(res_png["ocr_used"])
        self.assertEqual(res_png["file_type"], "png")
        self.assertIn("1.5%", res_png["full_text"])

if __name__ == "__main__":
    unittest.main()

