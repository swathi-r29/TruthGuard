import unittest
from modules.financial_engine import (
    calculate_reducing_emi,
    calculate_flat_emi,
    calculate_total_interest,
    generate_amortization_schedule,
    calculate_fee_value,
    calculate_tax_on_charges,
    calculate_real_cost_metrics
)

class TestFinancialEngine(unittest.TestCase):
    
    def test_reducing_emi(self):
        # 100,000 principal at 12% annual rate (1% monthly) for 12 months
        # EMI = 100000 * 0.01 * (1.01^12) / (1.01^12 - 1) = 8884.88
        emi = calculate_reducing_emi(100000.0, 12.0, 12)
        self.assertAlmostEqual(emi, 8884.88, places=2)
        
        # Zero interest loan
        zero_emi = calculate_reducing_emi(12000.0, 0.0, 12)
        self.assertEqual(zero_emi, 1000.0)

    def test_flat_emi(self):
        # 100,000 principal at 12% annual rate flat for 12 months (1 year)
        # Interest = 100000 * 0.12 * 1 = 12000
        # EMI = (100000 + 12000) / 12 = 9333.33
        emi = calculate_flat_emi(100000.0, 12.0, 12)
        self.assertAlmostEqual(emi, 9333.33, places=2)

    def test_total_interest(self):
        interest = calculate_total_interest(100000.0, 8884.88, 12)
        self.assertAlmostEqual(interest, 6618.56, places=2) # (8884.88 * 12) - 100000

    def test_amortization_schedule(self):
        schedule = generate_amortization_schedule(10000.0, 12.0, 5, 2060.40)
        self.assertEqual(len(schedule), 5)
        
        # Check that closing balance of final month is 0.0
        self.assertEqual(schedule[-1]["closing_balance"], 0.0)
        
        # Check sum of principal paid is equal to initial principal (approximately)
        total_principal_paid = sum(m["principal_paid"] for m in schedule)
        self.assertAlmostEqual(total_principal_paid, 10000.0, places=1)

    def test_fee_value(self):
        # Percentage fee
        self.assertEqual(calculate_fee_value(500000.0, 2.0, "percent"), 10000.0)
        # Fixed fee
        self.assertEqual(calculate_fee_value(500000.0, 1500.0, "INR"), 1500.0)

    def test_tax_on_charges(self):
        tax = calculate_tax_on_charges(10000.0, 18.0)
        self.assertEqual(tax, 1800.0)

    def test_real_cost_metrics(self):
        charges = [
            {"original_name": "Processing Fee", "value": 2.0, "unit": "percent", "classification": "ADDITIONAL_COST"},
            {"original_name": "Late Payment Penalty", "value": 500.0, "unit": "INR", "classification": "PENALTY"}
        ]
        
        metrics = calculate_real_cost_metrics(
            principal=100000.0,
            interest_rate_annual=12.0,
            tenure_months=12,
            charges=charges,
            tax_rate_percent=18.0 # 18% GST on processing fee
        )
        
        # Processing fee = 2% of 100,000 = 2000
        self.assertEqual(metrics["upfront_fees"], 2000.0)
        # Tax on fee = 18% of 2000 = 360
        self.assertEqual(metrics["taxes_on_fees"], 360.0)
        # Net disbursed = 100,000 - 2000 - 360 = 97640
        self.assertEqual(metrics["net_disbursed_amount"], 97640.0)
        # Total interest (approx) = 6618.56
        # Scheduled total cost = interest + fees + taxes = 6618.56 + 2000 + 360 = 8978.56
        self.assertAlmostEqual(metrics["scheduled_total_cost"], 8978.56, delta=5.0)
        
        # Late fee should be under penalties and separate from guaranteed costs
        self.assertEqual(len(metrics["penalties"]), 1)
        self.assertEqual(metrics["penalties"][0]["name"], "Late Payment Penalty")

if __name__ == "__main__":
    unittest.main()
