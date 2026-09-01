import unittest
from modules.analyzer.compliance import check_regulatory_compliance

class TestRegulatoryCompliance(unittest.TestCase):
    def setUp(self):
        self.default_metrics = {
            "loan_amount": 200000.0,
            "interest_rate_annual": 18.0,
            "tenure_months": 24,
            "emi": 9984.82,
            "real_apr": 18.0,
            "net_disbursed_amount": 200000.0,
            "upfront_fees": 0.0,
            "taxes_on_fees": 0.0
        }
        self.default_charges = []

    def test_usury_critical_alert(self):
        # Scenario: real APR is above 36%
        metrics = self.default_metrics.copy()
        metrics["real_apr"] = 38.5
        
        alerts = check_regulatory_compliance(metrics, self.default_charges)
        critical_alerts = [a for a in alerts if a["severity"] == "CRITICAL"]
        
        self.assertEqual(len(critical_alerts), 1)
        self.assertIn("Predatory Interest Rate", critical_alerts[0]["title"])

    def test_hidden_markup_warning(self):
        # Scenario: real APR (22%) is > 3% above nominal (18%)
        metrics = self.default_metrics.copy()
        metrics["real_apr"] = 22.0
        
        alerts = check_regulatory_compliance(metrics, self.default_charges)
        markup_alerts = [a for a in alerts if "Hidden Cost Markup" in a["title"]]
        
        self.assertEqual(len(markup_alerts), 1)
        self.assertEqual(markup_alerts[0]["severity"], "WARNING")

    def test_excessive_processing_fee_warning(self):
        # Scenario: processing fee is 4.0% (> 3.0%)
        metrics = self.default_metrics.copy()
        charges = [
            {
                "canonical_name": "processing_fee",
                "original_name": "Processing Fee",
                "value": 4.0,
                "unit": "percent",
                "classification": "ADDITIONAL_COST"
            }
        ]
        
        alerts = check_regulatory_compliance(metrics, charges)
        pf_alerts = [a for a in alerts if "Excessive Processing Fee" in a["title"]]
        
        self.assertEqual(len(pf_alerts), 1)
        self.assertEqual(pf_alerts[0]["severity"], "WARNING")

    def test_prepayment_penalty_warning(self):
        # Scenario: foreclosure charges are present in the contract
        charges = [
            {
                "canonical_name": "foreclosure_charge",
                "original_name": "Foreclosure Charge",
                "value": "4% of outstanding principal",
                "unit": "percent",
                "classification": "CONDITIONAL_COST"
            }
        ]
        
        alerts = check_regulatory_compliance(self.default_metrics, charges)
        prepayment_alerts = [a for a in alerts if "Early Debt Payoff Penalties" in a["title"]]
        
        self.assertEqual(len(prepayment_alerts), 1)

    def test_high_default_penalty_warning(self):
        # Scenario: late payment fee flat ₹750 (> ₹500)
        charges = [
            {
                "canonical_name": "late_payment_fee",
                "original_name": "Late Payment Fee",
                "value": 750.0,
                "unit": "INR",
                "classification": "PENALTY"
            }
        ]
        
        alerts = check_regulatory_compliance(self.default_metrics, charges)
        penalty_alerts = [a for a in alerts if "High Default/Penalty Fees" in a["title"]]
        
        self.assertEqual(len(penalty_alerts), 1)
        self.assertEqual(penalty_alerts[0]["severity"], "WARNING")
        self.assertIn("exceeds ₹500 standard", penalty_alerts[0]["description"])

if __name__ == "__main__":
    unittest.main()
