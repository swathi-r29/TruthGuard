import unittest
from modules.ai_extraction.schemas import LoanExtractionResult, ExtractedField
from modules.charge_detection import classify_charge, detect_charges

class TestCharges(unittest.TestCase):
    
    def test_classify_charge(self):
        self.assertEqual(classify_charge("loan_amount"), "BASE_COST")
        self.assertEqual(classify_charge("processing_fee"), "ADDITIONAL_COST")
        self.assertEqual(classify_charge("processing_fee_percentage"), "ADDITIONAL_COST")
        self.assertEqual(classify_charge("foreclosure_charge"), "CONDITIONAL_COST")
        self.assertEqual(classify_charge("late_payment_fee"), "PENALTY")
        self.assertEqual(classify_charge("gst_tax_references"), "TAX")
        self.assertEqual(classify_charge("insurance"), "OPTIONAL_COST")
        self.assertEqual(classify_charge("unknown_random_fee"), "OTHER")

    def test_detect_charges_hybrid(self):
        # 1. Mock extracted result
        extracted = LoanExtractionResult(
            loan_amount=ExtractedField(value=100000.0, unit="INR", page=1, confidence="high"),
            interest_rate=ExtractedField(value=12.0, unit="percent", page=1, confidence="high"),
            processing_fee=ExtractedField(value=2000.0, unit="INR", page=1, confidence="high")
        )
        
        # 2. Mock pages (one containing a late fee and foreclosure charge in text, but AI missed it)
        pages = [
            {"page_number": 1, "text": "Loan agreement details. Amount: 1,00,000 INR. Interest: 12.0% per annum."},
            {"page_number": 2, "text": "A late payment fee of 300 INR applies for delays. Foreclosure charge is applicable on early closure."}
        ]
        
        charges = detect_charges(extracted, pages)
        
        # Verify AI extracted charges
        ai_extracted_keys = [c["canonical_name"] for c in charges if c["source"] == "ai_extraction"]
        self.assertIn("loan_amount", ai_extracted_keys)
        self.assertIn("interest_rate", ai_extracted_keys)
        self.assertIn("processing_fee", ai_extracted_keys)
        
        # Verify keyword detected charges (AI missed but regex caught)
        kw_detected = [c for c in charges if c["source"] == "keyword_reference"]
        kw_names = [c["canonical_name"] for c in kw_detected]
        
        # Should detect late_payment_fee and foreclosure_charge
        self.assertIn("late_payment_fee", kw_names)
        self.assertIn("foreclosure_charge", kw_names)
        
        # Verify keyword charge properties
        late_charge = next(c for c in kw_detected if c["canonical_name"] == "late_payment_fee")
        self.assertIsNone(late_charge["value"])
        self.assertEqual(late_charge["page"], 2)
        self.assertIn("late payment fee", late_charge["evidence"].lower())

if __name__ == "__main__":
    unittest.main()
