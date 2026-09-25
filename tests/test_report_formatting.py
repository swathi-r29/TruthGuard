"""
Unit Tests for Download Report Clean Formatting.
Verifies that markdown reports are cleanly formatted without excessive blank lines (\n\n\n+),
repeated horizontal spaces, or unwanted section padding.
"""

import unittest
import re
from modules.reporting.report_generator import generate_markdown_report, clean_report_formatting

class TestReportFormatting(unittest.TestCase):

    def setUp(self):
        self.sample_metrics = {
            "loan_amount": 200000.0,
            "interest_rate_annual": 18.0,
            "tenure_months": 24,
            "emi": 9984.80,
            "upfront_fees": 4000.0,
            "taxes_on_fees": 720.0,
            "net_disbursed_amount": 195280.0,
            "total_scheduled_repayment": 239635.20,
            "total_interest": 39635.20,
            "scheduled_total_cost": 44355.20
        }
        self.sample_charges = [
            {
                "canonical_name": "processing_fee",
                "original_name": "Processing Fee",
                "value": 2.0,
                "unit": "percent",
                "basis": "loan_amount",
                "page": 1,
                "evidence": "Processing fee of 2% applicable upfront",
                "classification": "BASE_COST"
            }
        ]
        self.sample_transparency = {
            "score": 82,
            "breakdown": {
                "information_completeness": 14,
                "prepayment_conditions": 12,
                "penalty_exposure": 12,
                "fee_clarity": 18,
                "contract_complexity": 12,
                "additional_charges": 14
            }
        }

    def test_clean_report_formatting_collapses_excessive_newlines(self):
        """Test clean_report_formatting collapses 3 or more newlines into 2."""
        raw_text = "Header 1\n\n\n\n\nParagraph text line 1.\n\n\n\nParagraph text line 2."
        cleaned = clean_report_formatting(raw_text)
        self.assertNotIn("\n\n\n", cleaned)
        self.assertIn("Header 1\n\nParagraph text line 1.\n\nParagraph text line 2.", cleaned)

    def test_clean_report_formatting_collapses_repeated_horizontal_spaces(self):
        """Test clean_report_formatting collapses multiple horizontal spaces."""
        raw_text = "Loan   Amount:    Rs.   2,00,000   "
        cleaned = clean_report_formatting(raw_text)
        self.assertEqual(cleaned, "Loan Amount: Rs. 2,00,000")

    def test_generate_markdown_report_structure_and_no_excessive_gaps(self):
        """Test generate_markdown_report produces a clean report without stacked empty lines."""
        report = generate_markdown_report(
            metrics=self.sample_metrics,
            charges=self.sample_charges,
            transparency=self.sample_transparency,
            recommendations=["Review processing fee waiver option."],
            document_text="This is page 1.\n\n\n\nThis is page 2 text."
        )

        # Check absence of 3+ consecutive newlines
        self.assertNotIn("\n\n\n", report)

        # Check required section headers
        self.assertIn("# DEBT DETOX REPORT", report)
        self.assertIn("## 1. Loan Overview & Calculations", report)
        self.assertIn("## 2. Debt Detox Transparency Score: 82/100", report)
        self.assertIn("## 3. Detected Charges List", report)
        self.assertIn("## 4. Key Actions & Recommendations", report)
        self.assertIn("## 6. Extracted Document Text", report)

        # Check financial table values formatted cleanly
        self.assertIn("₹200,000.00", report)
        self.assertIn("18.0%", report)

if __name__ == "__main__":
    unittest.main()
