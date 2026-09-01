import unittest
from unittest.mock import patch, MagicMock
import requests
from modules.ai_extraction import clean_numeric_value, DocumentExtractor, OllamaClient
from modules.ai_extraction.client import (
    OllamaClientError, 
    OllamaConnectionError, 
    OllamaModelNotFoundError
)
from modules.ai_extraction.schemas import LoanExtractionResult

class TestExtraction(unittest.TestCase):
    
    def test_clean_numeric_value(self):
        # Numeric fields
        self.assertEqual(clean_numeric_value("5,00,000", "loan_amount"), 500000.0)
        self.assertEqual(clean_numeric_value("₹ 1,500.50", "processing_fee"), 1500.50)
        self.assertEqual(clean_numeric_value("18.5%", "interest_rate"), 18.5)
        self.assertEqual(clean_numeric_value("18", "interest_rate"), 18.0)
        self.assertEqual(clean_numeric_value("null", "emi"), None)
        self.assertEqual(clean_numeric_value(None, "emi"), None)
        
        # New text variations on numeric fields
        self.assertEqual(clean_numeric_value("Rs. 2,00,000", "loan_amount"), 200000.0)
        self.assertEqual(clean_numeric_value("INR 2,00,000", "loan_amount"), 200000.0)
        self.assertEqual(clean_numeric_value("2 percent", "processing_fee_percentage"), 2.0)
        self.assertEqual(clean_numeric_value("Rs 750", "documentation_fee"), 750.0)
        self.assertEqual(clean_numeric_value("2% of loan amount", "processing_fee_percentage"), 2.0)
        self.assertEqual(clean_numeric_value("24 months", "tenure"), 24.0)
        self.assertEqual(clean_numeric_value("Rs. 750/-", "documentation_fee"), 750.0)
        self.assertEqual(clean_numeric_value("500.00", "other_charge"), 500.0)
        
        # String fields should preserve text
        self.assertEqual(clean_numeric_value("Personal Loan", "document_type"), "Personal Loan")
        self.assertEqual(clean_numeric_value("4% before 12 months, 2% after", "foreclosure_charge"), "4% before 12 months, 2% after")

    def test_merge_results(self):
        extractor = DocumentExtractor()
        
        # Scenario: Data extracted from different pages
        page1 = {
            "loan_amount": {
                "value": "2,00,000",
                "unit": "INR",
                "page": 1,
                "evidence": "loan amount of 2,00,000",
                "confidence": "high"
            },
            "interest_rate": {
                "value": None
            }
        }
        
        page2 = {
            "interest_rate": {
                "value": "12.5",
                "unit": "percent",
                "page": 2,
                "evidence": "interest rate 12.5%",
                "confidence": "high"
            },
            "loan_amount": {
                "value": None
            },
            "other_charges": [
                {
                    "name": "Documentation Fee",
                    "value": "500",
                    "unit": "INR",
                    "page": 2,
                    "evidence": "Documentation fee of 500 INR"
                }
            ]
        }
        
        merged = extractor.merge_results([page1, page2])
        
        # Verify merged fields are populated correctly and numeric values cleaned
        self.assertEqual(merged.loan_amount.value, 200000.0)
        self.assertEqual(merged.loan_amount.page, 1)
        self.assertEqual(merged.loan_amount.confidence, "high")
        
        self.assertEqual(merged.interest_rate.value, 12.5)
        self.assertEqual(merged.interest_rate.page, 2)
        self.assertEqual(merged.interest_rate.confidence, "high")
        
        self.assertEqual(len(merged.other_charges), 1)
        self.assertEqual(merged.other_charges[0].name, "Documentation Fee")
        self.assertEqual(merged.other_charges[0].value, 500.0)

    @patch('modules.ai_extraction.client.requests.get')
    def test_client_check_connection_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        self.assertTrue(client.check_connection())
        mock_get.assert_called_with("http://localhost:11434/api/tags", timeout=3)

    @patch('modules.ai_extraction.client.requests.get')
    def test_client_check_connection_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection refused")
        
        client = OllamaClient()
        client.provider = "ollama"
        self.assertFalse(client.check_connection())

    @patch('modules.ai_extraction.client.requests.get')
    def test_client_check_model_available_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "gemma2:2b"}]
        }
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        client.model = "gemma2:2b"
        self.assertTrue(client.check_model_available())

    @patch('modules.ai_extraction.client.requests.get')
    def test_client_check_model_available_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:latest"}]
        }
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        client.model = "gemma2:2b"
        self.assertFalse(client.check_model_available())

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_client_generate_json_success(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"lender_name": {"value": "Debt Detox Bank", "confidence": "high"}}'
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        res = client.generate_json("Test Prompt", "System Prompt")
        self.assertEqual(res["lender_name"]["value"], "Debt Detox Bank")
        self.assertEqual(res["lender_name"]["confidence"], "high")

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.OllamaClient.check_model_available')
    @patch('modules.ai_extraction.client.requests.post')
    def test_client_generate_json_missing_model(self, mock_post, mock_check_model, mock_check_conn):
        mock_check_conn.return_value = True
        mock_check_model.return_value = False
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        with self.assertRaises(OllamaModelNotFoundError):
            client.generate_json("Test Prompt")

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_client_generate_json_timeout(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        client = OllamaClient()
        client.provider = "ollama"
        with self.assertRaises(OllamaClientError) as context:
            client.generate_json("Test Prompt")
        self.assertIn("timed out", str(context.exception))

    @patch('modules.ai_extraction.client.requests.get')
    def test_client_generate_json_connection_refused(self, mock_get):
        # check_connection raises exception
        mock_get.side_effect = requests.exceptions.RequestException("Refused")
        
        client = OllamaClient()
        client.provider = "ollama"
        with self.assertRaises(OllamaConnectionError):
            client.generate_json("Test Prompt")

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_client_generate_json_invalid_json_returned(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is raw conversational text and not JSON"
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "ollama"
        with self.assertRaises(OllamaClientError) as context:
            client.generate_json("Test Prompt")
        self.assertIn("was not valid JSON", str(context.exception))

    @patch('modules.ai_extraction.client.requests.get')
    def test_gemini_client_check_connection_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = "test-api-key"
        client.model = "gemini-1.5-flash"
        self.assertTrue(client.check_connection())
        mock_get.assert_called_with("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash?key=test-api-key", headers={"x-goog-api-key": "test-api-key"}, timeout=3)

    @patch('modules.ai_extraction.client.requests.get')
    def test_gemini_client_check_connection_no_key(self, mock_get):
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = ""
        self.assertFalse(client.check_connection())

    @patch('modules.ai_extraction.client.requests.get')
    def test_gemini_client_check_connection_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection refused")
        
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = "test-api-key"
        self.assertFalse(client.check_connection())

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_gemini_client_generate_json_success(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"lender_name": {"value": "Gemini Bank", "confidence": "high"}}'}
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = "test-api-key"
        res = client.generate_json("Test Prompt", "System Prompt")
        self.assertEqual(res["lender_name"]["value"], "Gemini Bank")
        self.assertEqual(res["lender_name"]["confidence"], "high")

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_gemini_client_generate_json_unauthorized(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = "invalid-key"
        with self.assertRaises(OllamaConnectionError):
            client.generate_json("Test Prompt")

    @patch('modules.ai_extraction.client.OllamaClient.check_connection')
    @patch('modules.ai_extraction.client.requests.post')
    def test_gemini_client_generate_json_bad_request(self, mock_post, mock_check_conn):
        mock_check_conn.return_value = True
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid model name"}
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        client.provider = "gemini"
        client.api_key = "test-key"
        with self.assertRaises(OllamaClientError) as context:
            client.generate_json("Test Prompt")
        self.assertIn("Invalid model name", str(context.exception))

    @patch('modules.ai_extraction.extractor.OllamaClient.check_connection')
    @patch('modules.ai_extraction.extractor.OllamaClient.generate_json')
    def test_extractor_extract_from_pages_skips_errors(self, mock_generate, mock_check_conn):
        mock_check_conn.return_value = True
        
        # Make page 1 raise an error, but page 2 succeeds
        mock_generate.side_effect = [
            OllamaClientError("Timeout on page 1"),
            {"lender_name": {"value": "Jane's Bank", "page": 2, "confidence": "high"}}
        ]
        
        pages = [
            {"page_number": 1, "text": "This is page 1 with some text"},
            {"page_number": 2, "text": "This is page 2 with lender info Jane's Bank"}
        ]
        
        extractor = DocumentExtractor()
        extractor.client.provider = "ollama"
        merged = extractor.extract_from_pages(pages)
        
        # Verify that page 1 did not abort the whole extraction and page 2 details are present
        self.assertEqual(merged.lender_name.value, "Jane's Bank")
        self.assertEqual(merged.lender_name.page, 2)

    def test_custom_user_document_regex_extraction(self):
        extractor = DocumentExtractor()
        pages = [
            {
                "page_number": 1,
                "text": (
                    "HDFC BANK LIMITED - LOAN SANCTION LETTER\n"
                    "Sanction Amount: ₹ 5,00,000/-\n"
                    "Rate of Interest: 11.5% p.a. reducing balance\n"
                    "Tenure (Months): 48\n"
                    "Monthly EMI: ₹ 13,048\n"
                    "Processing fee is 1.5%\n"
                    "Late payment fee: ₹ 500 flat\n"
                    "Bounce Charge: ₹ 450 per instance"
                )
            }
        ]
        result = extractor.extract_via_regex("\n\n".join(p["text"] for p in pages), pages)
        self.assertEqual(result.loan_amount.value, 500000.0)
        self.assertEqual(result.interest_rate.value, 11.5)
        self.assertEqual(result.tenure.value, 48.0)
        self.assertEqual(result.emi.value, 13048.0)
        self.assertEqual(result.processing_fee_percentage.value, 1.5)
        self.assertEqual(result.late_payment_fee.value, 500.0)
        self.assertEqual(result.bounce_charge.value, 450.0)

    def test_zero_interest_bnpl_custom_document(self):
        extractor = DocumentExtractor()
        pages = [
            {
                "page_number": 1,
                "text": (
                    "ZestMoney BNPL Consumer Finance Agreement\n"
                    "Funded Amount: ₹ 40,000\n"
                    "0% Interest Promo Loan\n"
                    "Repayment Period: 4 Months\n"
                    "Processing Fee: ₹ 299"
                )
            }
        ]
        result = extractor.extract_via_regex("\n\n".join(p["text"] for p in pages), pages)
        self.assertEqual(result.loan_amount.value, 40000.0)
        self.assertEqual(result.interest_rate.value, 0.0)
        self.assertEqual(result.tenure.value, 4.0)
        self.assertEqual(result.emi.value, 10000.0)  # Solved via Financial Solver (40000 / 4)

    def test_financial_solver_derives_missing_rate(self):
        extractor = DocumentExtractor()
        pages = [
            {
                "page_number": 1,
                "text": (
                    "Personal Finance Agreement\n"
                    "Principal Amount: Rs. 1,00,000\n"
                    "Loan Period: 12 months\n"
                    "Equated Monthly Installment: Rs. 8,885"
                )
            }
        ]
        result = extractor.extract_via_regex("\n\n".join(p["text"] for p in pages), pages)
        self.assertEqual(result.loan_amount.value, 100000.0)
        self.assertEqual(result.tenure.value, 12.0)
        self.assertEqual(result.emi.value, 8885.0)
        self.assertIsNotNone(result.interest_rate.value)
        self.assertAlmostEqual(result.interest_rate.value, 12.0, delta=1.0)

if __name__ == "__main__":
    unittest.main()

