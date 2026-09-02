"""
Unit & Integration Tests for Debt Detox 4 Core Enhancements.
"""

import unittest
from pathlib import Path
from modules.active_loan import set_active_loan, get_active_loan
from modules.explanation.negotiation import generate_dispute_letter
from modules.reporting.pdf_generator import generate_pdf_audit_report
from modules.document_processor import process_document
from modules.charge_detection import detect_charges
from modules.financial_engine import calculate_real_cost_metrics

class TestEnhancements(unittest.TestCase):

    def setUp(self):
        self.dummy_session = {}
        self.sample_charges = [
            {
                "canonical_name": "processing_fee",
                "original_name": "Processing Fee",
                "value": 2.5,
                "unit": "percent",
                "basis": "loan_amount",
                "page": 1,
                "evidence": "Processing Fee: 2.5% of principal loan amount",
                "classification": "BASE_COST",
                "is_mandatory": True,
                "is_conditional": False
            },
            {
                "canonical_name": "foreclosure_charge",
                "original_name": "Foreclosure Charge",
                "value": 4.0,
                "unit": "percent",
                "basis": "outstanding_principal",
                "page": 1,
                "evidence": "a prepayment charge of 4% of outstanding principal",
                "classification": "PENALTY",
                "is_mandatory": False,
                "is_conditional": True
            }
        ]
        self.sample_metrics = calculate_real_cost_metrics(
            principal=300000.0,
            interest_rate_annual=14.5,
            tenure_months=36,
            charges=self.sample_charges,
            tax_rate_percent=18.0
        )

    def test_active_loan_sync(self):
        """Test active loan state synchronization."""
        active_loan = set_active_loan(
            st_session=self.dummy_session,
            doc_name="Apex_Personal_Loan.pdf",
            doc_type="pdf",
            total_pages=1,
            ocr_used=False,
            extracted=None,
            charges=self.sample_charges,
            metrics=self.sample_metrics,
            audit_status="VERIFIED"
        )
        self.assertIsNotNone(active_loan)
        self.assertEqual(active_loan["doc_name"], "Apex_Personal_Loan.pdf")
        self.assertEqual(active_loan["metrics"]["loan_amount"], 300000.0)

        retrieved = get_active_loan(self.dummy_session)
        self.assertEqual(retrieved["doc_name"], "Apex_Personal_Loan.pdf")
        self.assertTrue(len(retrieved["compliance_alerts"]) > 0)

    def test_dispute_letter_generation(self):
        """Test dispute letter generator with dynamic values."""
        active_loan = set_active_loan(
            st_session=self.dummy_session,
            doc_name="Apex_Personal_Loan.pdf",
            doc_type="pdf",
            total_pages=1,
            ocr_used=False,
            extracted=None,
            charges=self.sample_charges,
            metrics=self.sample_metrics
        )
        letter = generate_dispute_letter(
            active_loan=active_loan,
            selected_charges=["processing_fee", "foreclosure_charge"],
            borrower_name="Alice Doe"
        )
        self.assertIn("Alice Doe", letter)
        self.assertIn("300,000.00", letter)
        self.assertIn("Processing Fee", letter)
        self.assertIn("Foreclosure Charge", letter)
        self.assertIn("FORMAL REQUEST FOR FEE WAIVER", letter)

    def test_pdf_report_generation(self):
        """Test reportlab PDF Audit Report generation."""
        active_loan = set_active_loan(
            st_session=self.dummy_session,
            doc_name="Apex_Personal_Loan.pdf",
            doc_type="pdf",
            total_pages=1,
            ocr_used=False,
            extracted=None,
            charges=self.sample_charges,
            metrics=self.sample_metrics,
            transparency={"score": 85, "rating": "VERIFIED"}
        )
        pdf_bytes = generate_pdf_audit_report(active_loan)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_sample_documents_exist(self):
        """Verify that Instant Demo sample PDFs exist and process cleanly."""
        sample_dir = Path("sample_documents")
        self.assertTrue(sample_dir.exists())
        apex_pdf = sample_dir / "apex_personal_loan_agreement.pdf"
        self.assertTrue(apex_pdf.exists())

        with open(apex_pdf, "rb") as f:
            pdf_bytes = f.read()

        doc_res = process_document(pdf_bytes, "apex_personal_loan_agreement.pdf")
        self.assertTrue(doc_res["success"])
        self.assertGreater(doc_res["total_pages"], 0)

if __name__ == "__main__":
    unittest.main()
