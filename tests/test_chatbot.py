"""
Unit & Integration Tests for AI Loan Assistant Strict Document Grounding.
Verifies that the chatbot ONLY answers questions directly present in the uploaded document,
and strictly returns "This information is not available in the uploaded document" for any outside queries.
"""

import unittest
from ui.chatbot import query_ai_chatbot

class TestAILoanAssistant(unittest.TestCase):

    def setUp(self):
        self.refusal_msg = "This information is not available in the uploaded document"
        self.sample_context = """
Document Name: Apex_Loan_Agreement.pdf
Sanctioned Amount: ₹300000.0
Nominal Interest Rate: 14.5% p.a.
Tenure: 36 Months
Stated EMI: ₹10323.50

Extracted Charges:
- processing_fee: 2.5 percent (loan_amount) [Evidence: Processing Fee: 2.5% of principal loan amount]
- foreclosure_charge: 4.0 percent (outstanding_principal) [Evidence: a prepayment charge of 4% of outstanding principal]

Regulatory Warnings:
None

Document Text:
This Personal Loan Agreement is made between Apex Bank (Lender) and Alice Doe (Borrower).
The principal loan amount sanctioned is Rs. 3,00,000 at an interest rate of 14.5% per annum for a tenure of 36 months.
Late Payment Fee: A late fee of Rs. 500 per month will be charged for delayed EMIs.
Processing Fee: 2.5% deducted upfront.
Foreclosure Charge: 4% on early repayment.
"""

    def test_no_document_loaded_refusal(self):
        """Test refusal response when no document is uploaded or analyzed."""
        ans1 = query_ai_chatbot("What is my interest rate?", "", [])
        self.assertEqual(ans1, self.refusal_msg)

        ans2 = query_ai_chatbot("How do I manage my debt?", "No active document analyzed. Please guide the user to upload their document.", [])
        self.assertEqual(ans2, self.refusal_msg)

    def test_valid_document_queries(self):
        """Test Q&A fetching details strictly present in the uploaded document."""
        # Query interest rate
        ans_rate = query_ai_chatbot("What is the interest rate for this loan?", self.sample_context, [])
        self.assertIn("14.5%", ans_rate)

        # Query processing fee
        ans_fee = query_ai_chatbot("What is the processing fee?", self.sample_context, [])
        self.assertIn("2.5", ans_fee)

        # Query foreclosure / penalty
        ans_penalty = query_ai_chatbot("Is there any foreclosure penalty?", self.sample_context, [])
        self.assertIn("4", ans_penalty)

    def test_out_of_document_query_refusal(self):
        """Test refusal when query asks for information not present in the document."""
        # Query about unmentioned topic
        ans_weather = query_ai_chatbot("What is the weather today?", self.sample_context, [])
        self.assertEqual(ans_weather, self.refusal_msg)

        # Query about unmentioned insurance policy details
        ans_insurance = query_ai_chatbot("Does this agreement cover pet insurance or health coverage?", self.sample_context, [])
        self.assertEqual(ans_insurance, self.refusal_msg)

        # Query asking for general outside financial advice
        ans_advice = query_ai_chatbot("How should I invest in the stock market?", self.sample_context, [])
        self.assertEqual(ans_advice, self.refusal_msg)

    def test_general_debt_management_query_refusal(self):
        """Test general debt management questions return refusal message when not in contract text."""
        ans_manage = query_ai_chatbot("How do I reduce my debt overall?", self.sample_context, [])
        self.assertEqual(ans_manage, self.refusal_msg)

        ans_snowball = query_ai_chatbot("Explain the debt avalanche method", self.sample_context, [])
        self.assertEqual(ans_snowball, self.refusal_msg)

if __name__ == "__main__":
    unittest.main()
