import unittest
from unittest.mock import patch, MagicMock
import fitz
from modules.document_processor import process_document
from modules.ai_extraction import DocumentExtractor
from modules.charge_detection import detect_charges
from modules.financial_engine import calculate_real_cost_metrics
from modules.analyzer import calculate_transparency_score, calculate_effective_rates

class TestValidationPipeline(unittest.TestCase):
    
    def setUp(self):
        # Create a synthetic document matching DebtDetox_Validation_Loan_Agreement.pdf
        self.doc = fitz.open()
        
        # Page 1: Loan Overview and Main Terms
        page1 = self.doc.new_page()
        page1.insert_text((72, 72), (
            "DEBT DETOX VALIDATION BANK LTD.\n"
            "PERSONAL LOAN AGREEMENT\n\n"
            "This personal loan agreement is executed between the Lender and Borrower JANE DOE.\n"
            "SECTION 1: KEY LOAN DETAILS\n"
            "- Sanctioned Principal Amount: Rs. 2,00,000 (Rupees Two Lakhs Only)\n"
            "- Stated Interest Rate: 18.0% per annum on a reducing balance basis.\n"
            "- Tenure of Loan: 24 months.\n"
            "- Equated Monthly Installment (EMI): Rs. 9,984.82 per month.\n"
            "- Current Outstanding Principal: Rs. 2,00,000.\n"
            "\n"
            "The loan shall be repaid in 24 monthly installments of Rs. 9,984.82 each."
        ))
        
        # Page 2: Detailed Charges Schedule
        page2 = self.doc.new_page()
        page2.insert_text((72, 72), (
            "SECTION 2: SCHEDULE OF CHARGES\n"
            "- Processing Fee: 2% of the sanctioned principal loan amount.\n"
            "- Documentation Charges: Rs. 750 fixed stamp duty and administrative fee.\n"
            "- Credit Shield Insurance Cover: Rs. 3,500 one-time premium.\n"
            "- GST: 18% on processing and documentation fees.\n"
            "- Foreclosure Charge: 4% of outstanding principal if closed before 12 months, "
            "and 2% of outstanding principal if closed after 12 months.\n"
            "- Late Payment Fee: Rs. 500 flat penalty per default month.\n"
            "- Bounce Charge: Rs. 450 flat fee per payment instrument return/ECS bounce."
        ))
        
        self.pdf_bytes = self.doc.write()
        self.doc.close()

    @patch('modules.ai_extraction.extractor.OllamaClient')
    def test_validation_document_survives_pipeline(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        
        # Mock responses page-by-page
        def mock_generate_json(prompt, system_prompt):
            if "Page 1" in prompt:
                return {
                    "document_type": {"value": "personal_loan", "unit": None, "page": 1, "evidence": "PERSONAL LOAN AGREEMENT", "confidence": "high"},
                    "lender_name": {"value": "Debt Detox Validation Bank Ltd.", "unit": None, "page": 1, "evidence": "DEBT DETOX VALIDATION BANK LTD.", "confidence": "high"},
                    "borrower_name": {"value": "Jane Doe", "unit": None, "page": 1, "evidence": "JANE DOE", "confidence": "high"},
                    "loan_amount": {"value": "2,00,000", "unit": "INR", "page": 1, "evidence": "Sanctioned Principal Amount: Rs. 2,00,000", "confidence": "high"},
                    "outstanding_principal": {"value": "2,00,000", "unit": "INR", "page": 1, "evidence": "Current Outstanding Principal: Rs. 2,00,000", "confidence": "high"},
                    "interest_rate": {"value": "18.0", "unit": "percent", "page": 1, "evidence": "Stated Interest Rate: 18.0% per annum", "confidence": "high"},
                    "interest_type": {"value": "reducing_balance", "unit": None, "page": 1, "evidence": "reducing balance basis", "confidence": "high"},
                    "rate_basis": {"value": "annual", "unit": None, "page": 1, "evidence": "per annum", "confidence": "high"},
                    "tenure": {"value": "24", "unit": "months", "page": 1, "evidence": "Tenure of Loan: 24 months", "confidence": "high"},
                    "emi": {"value": "9,984.82", "unit": "INR", "page": 1, "evidence": "Equated Monthly Installment (EMI): Rs. 9,984.82", "confidence": "high"},
                    "number_of_installments": {"value": "24", "unit": "months", "page": 1, "evidence": "repaid in 24 monthly installments", "confidence": "high"}
                }
            else:
                return {
                    "processing_fee_percentage": {"value": "2.0", "unit": "percent", "page": 2, "evidence": "Processing Fee: 2% of the sanctioned principal", "confidence": "high"},
                    "documentation_fee": {"value": "750", "unit": "INR", "page": 2, "evidence": "Documentation Charges: Rs. 750", "confidence": "high"},
                    "insurance": {"value": "3,500", "unit": "INR", "page": 2, "evidence": "Credit Shield Insurance Cover: Rs. 3,500", "confidence": "high"},
                    "gst_tax_references": {"value": "18.0", "unit": "percent", "page": 2, "evidence": "GST: 18% on processing and documentation fees", "confidence": "high"},
                    "foreclosure_charge": {"value": "4% before 12 months, 2% after 12 months", "unit": "percent", "page": 2, "evidence": "Foreclosure Charge: 4% of outstanding principal if closed before 12 months, and 2% of outstanding principal if closed after 12 months", "confidence": "high"},
                    "late_payment_fee": {"value": "500", "unit": "INR", "page": 2, "evidence": "Late Payment Fee: Rs. 500 flat", "confidence": "high"},
                    "bounce_charge": {"value": "450", "unit": "INR", "page": 2, "evidence": "Bounce Charge: Rs. 450 flat", "confidence": "high"}
                }
                
        mock_client.generate_json.side_effect = mock_generate_json
        mock_client_class.return_value = mock_client
        
        # --- EXECUTE PIPELINE ---
        
        # 1. Document processing
        doc_data = process_document(self.pdf_bytes, "DebtDetox_Validation_Loan_Agreement.pdf")
        self.assertTrue(doc_data["success"])
        pages = doc_data["pages"]
        self.assertEqual(len(pages), 2)
        
        # 2. AI Extraction
        extractor = DocumentExtractor()
        extracted = extractor.extract_from_pages(pages)
        
        self.assertEqual(extracted.loan_amount.value, 200000.0)
        self.assertEqual(extracted.outstanding_principal.value, 200000.0)
        self.assertEqual(extracted.interest_rate.value, 18.0)
        self.assertEqual(extracted.tenure.value, 24.0)
        self.assertEqual(extracted.emi.value, 9984.82)
        
        # 3. Charge detection
        charges = detect_charges(extracted, pages)
        
        # Assert each expected charge exists with correct values and units
        charges_dict = {c["canonical_name"]: c for c in charges}
        
        self.assertIn("processing_fee", charges_dict)
        self.assertEqual(charges_dict["processing_fee"]["value"], 2.0)
        self.assertEqual(charges_dict["processing_fee"]["unit"], "percent")
        
        self.assertIn("insurance", charges_dict)
        self.assertEqual(charges_dict["insurance"]["value"], 3500.0)
        self.assertIn(charges_dict["insurance"]["unit"], ["INR", "currency"])
        
        self.assertIn("documentation_fee", charges_dict)
        self.assertEqual(charges_dict["documentation_fee"]["value"], 750.0)
        self.assertIn(charges_dict["documentation_fee"]["unit"], ["INR", "currency"])
        
        self.assertIn("gst_tax_references", charges_dict)
        self.assertEqual(charges_dict["gst_tax_references"]["value"], 18.0)
        self.assertEqual(charges_dict["gst_tax_references"]["unit"], "percent")
        
        # Foreclosure charge should be preserved as string value containing 4% and 2%
        self.assertIn("foreclosure_charge", charges_dict)
        self.assertIn("4%", charges_dict["foreclosure_charge"]["value"])
        self.assertIn("2%", charges_dict["foreclosure_charge"]["value"])
        
        self.assertIn("late_payment_fee", charges_dict)
        self.assertEqual(charges_dict["late_payment_fee"]["value"], 500.0)
        
        self.assertIn("bounce_charge", charges_dict)
        self.assertEqual(charges_dict["bounce_charge"]["value"], 450.0)
        
        # 4. Financial engine calculations
        metrics = calculate_real_cost_metrics(
            principal=extracted.loan_amount.value,
            interest_rate_annual=extracted.interest_rate.value,
            tenure_months=int(extracted.tenure.value),
            charges=charges,
            override_emi=extracted.emi.value,
            tax_rate_percent=18.0,
            outstanding_principal=extracted.outstanding_principal.value or 0.0 if hasattr(extracted, 'outstanding_principal') and extracted.outstanding_principal else None
        )
        
        # Expected EMI: 9,984.82
        self.assertEqual(metrics["emi"], 9984.82)
        # Expected upfront fees: 2% of 2,00,000 (Processing Fee = 4000) + 750 (Documentation Fee) = 4750
        self.assertEqual(metrics["upfront_fees"], 4750.0)
        # Expected optional fees: Insurance premium = 3500
        self.assertEqual(metrics["optional_fees"], 3500.0)
        # Expected GST/taxes: 18% of (4000 + 750) = 18% of 4750 = 855.0
        self.assertEqual(metrics["taxes_on_fees"], 855.0)
        # Expected disbursement: 2,00,000 - 4750 - 855 = 1,94,395.0
        self.assertEqual(metrics["net_disbursed_amount"], 194395.0)
        
        # 5. Effective Rate (APR)
        rate_results = calculate_effective_rates(
            net_disbursed=metrics["net_disbursed_amount"],
            emi=metrics["emi"],
            tenure_months=metrics["tenure_months"]
        )
        self.assertIsNotNone(rate_results["effective_annual_cost_rate"])
        self.assertGreater(rate_results["effective_annual_cost_rate"], 18.0)
        
        # 6. Transparency Score
        transparency = calculate_transparency_score(metrics, charges, len(pages))
        self.assertGreater(transparency["score"], 0)
        self.assertLessEqual(transparency["score"], 100)

if __name__ == "__main__":
    unittest.main()
