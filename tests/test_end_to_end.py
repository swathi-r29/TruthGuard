import unittest
from unittest.mock import patch, MagicMock
import fitz
from modules.document_processor import process_document
from modules.ai_extraction import DocumentExtractor
from modules.ai_extraction.schemas import LoanExtractionResult
from modules.charge_detection import detect_charges
from modules.financial_engine import calculate_real_cost_metrics
from modules.analyzer import calculate_transparency_score, calculate_effective_rates

class TestEndToEndIntegration(unittest.TestCase):
    
    def setUp(self):
        # 1. Create a realistic synthetic personal loan document in memory
        self.doc = fitz.open()
        page = self.doc.new_page()
        page.insert_text((72, 72), (
            "PERSONAL LOAN AGREEMENT\n\n"
            "This agreement is made between Apex Lending Services (Lender) and John Doe (Borrower).\n"
            "1. Loan Principal Amount: INR 3,00,000.\n"
            "2. Interest Rate: 15.5% per annum on a reducing balance basis.\n"
            "3. Tenure: 24 months.\n"
            "4. Equated Monthly Installment (EMI): INR 14,615.50.\n"
            "5. Fees and Charges:\n"
            "   - Processing Fee: 2% of the Loan Amount.\n"
            "   - Documentation fee of INR 1,000 applies.\n"
            "   - Prepayment or early closure: A foreclosure charge of 3% is applicable.\n"
            "   - Late payment charges: INR 500 per month for delays.\n"
            "   - Check/Auto-debit bounce: INR 450 per event."
        ))
        self.pdf_bytes = self.doc.write()
        self.doc.close()

    @patch('modules.ai_extraction.extractor.OllamaClient')
    def test_pipeline_success(self, mock_client_class):
        # Setup mock client behavior to return schema-conforming dictionary
        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        
        # Exact mock response conforming to LoanExtractionResult structure
        mock_client.generate_json.return_value = {
            "document_type": {"value": "personal_loan", "unit": None, "page": 1, "evidence": "PERSONAL LOAN AGREEMENT", "confidence": "high"},
            "lender_name": {"value": "Apex Lending Services", "unit": None, "page": 1, "evidence": "Apex Lending Services (Lender)", "confidence": "high"},
            "borrower_name": {"value": "John Doe", "unit": None, "page": 1, "evidence": "John Doe (Borrower)", "confidence": "high"},
            "loan_amount": {"value": "3,00,000", "unit": "INR", "page": 1, "evidence": "Loan Principal Amount: INR 3,00,000", "confidence": "high"},
            "interest_rate": {"value": "15.5", "unit": "percent", "page": 1, "evidence": "Interest Rate: 15.5% per annum", "confidence": "high"},
            "interest_type": {"value": "reducing_balance", "unit": None, "page": 1, "evidence": "reducing balance basis", "confidence": "high"},
            "rate_basis": {"value": "annual", "unit": None, "page": 1, "evidence": "per annum", "confidence": "high"},
            "tenure": {"value": "24", "unit": "months", "page": 1, "evidence": "Tenure: 24 months", "confidence": "high"},
            "emi": {"value": "14,615.50", "unit": "INR", "page": 1, "evidence": "Equated Monthly Installment (EMI): INR 14,615.50", "confidence": "high"},
            "processing_fee_percentage": {"value": "2", "unit": "percent", "page": 1, "evidence": "Processing Fee: 2% of the Loan Amount", "confidence": "high"},
            "documentation_fee": {"value": "1,000", "unit": "INR", "page": 1, "evidence": "documentation fee of INR 1,000 applies", "confidence": "high"},
            "foreclosure_charge": {"value": "3", "unit": "percent", "basis": "outstanding_principal", "page": 1, "evidence": "foreclosure charge of 3% is applicable", "confidence": "high"},
            "late_payment_fee": {"value": "500", "unit": "INR", "page": 1, "evidence": "Late payment charges: INR 500 per month", "confidence": "high"}
            # Let the AI miss the bounce charge of 450 to test the hybrid keyword detector!
        }
        
        mock_client_class.return_value = mock_client
        
        # --- Run Pipeline ---
        
        # 1. Document processing
        doc_data = process_document(self.pdf_bytes, "agreement.pdf")
        self.assertTrue(doc_data["success"])
        pages = doc_data["pages"]
        self.assertEqual(len(pages), 1)
        self.assertIn("PERSONAL LOAN AGREEMENT", pages[0]["text"])
        
        # 2. AI Extraction
        extractor = DocumentExtractor()
        extracted = extractor.extract_from_pages(pages)
        self.assertEqual(extracted.loan_amount.value, 300000.0)
        self.assertEqual(extracted.interest_rate.value, 15.5)
        
        # 3. Hybrid Charge detection
        charges = detect_charges(extracted, pages)
        
        # Check that processing_fee, documentation_fee, foreclosure_charge, late_payment_fee are detected
        keys = [c["canonical_name"] for c in charges]
        self.assertIn("processing_fee", keys)
        self.assertIn("documentation_fee", keys)
        self.assertIn("foreclosure_charge", keys)
        self.assertIn("late_payment_fee", keys)
        
        # Bounce charge was missed by LLM, check that hybrid keyword matcher caught it!
        self.assertIn("bounce_charge", keys)
        bounce = next(c for c in charges if c["canonical_name"] == "bounce_charge")
        self.assertEqual(bounce["source"], "keyword_reference")
        self.assertIsNone(bounce["value"])
        
        # 4. Financial Calculations
        metrics = calculate_real_cost_metrics(
            principal=extracted.loan_amount.value,
            interest_rate_annual=extracted.interest_rate.value,
            tenure_months=int(extracted.tenure.value),
            charges=charges,
            override_emi=extracted.emi.value,
            tax_rate_percent=18.0, # Apply standard 18% GST on processing fees + documentation fees
            outstanding_principal=extracted.outstanding_principal.value or 0.0 if hasattr(extracted, 'outstanding_principal') and extracted.outstanding_principal else None
        )
        
        # Upfront fee = 2% of 300,000 (Processing fee) + 1,000 (Doc fee) = 6,000 + 1,000 = 7,000
        self.assertEqual(metrics["upfront_fees"], 7000.0)
        # Taxes = 18% of 7000 = 1260.0
        self.assertEqual(metrics["taxes_on_fees"], 1260.0)
        # Net disbursed = 300,000 - 7000 - 1260 = 291740.0
        self.assertEqual(metrics["net_disbursed_amount"], 291740.0)
        
        # 5. Effective annual borrowing cost rate
        rate_results = calculate_effective_rates(
            net_disbursed=metrics["net_disbursed_amount"],
            emi=metrics["emi"],
            tenure_months=metrics["tenure_months"]
        )
        self.assertIsNotNone(rate_results["effective_annual_cost_rate"])
        # Because fees are deducted upfront, effective rate should be higher than 15.5%
        self.assertGreater(rate_results["effective_annual_cost_rate"], 15.5)
        
        # 6. Transparency Score calculation
        score_results = calculate_transparency_score(metrics, charges, len(pages))
        self.assertGreater(score_results["score"], 0)
        self.assertLessEqual(score_results["score"], 100)

if __name__ == "__main__":
    unittest.main()
