import unittest
from modules.debt_strategy import rank_debts, simulate_loan_payoff, compare_debt_metrics

class TestDebtStrategy(unittest.TestCase):
    
    def setUp(self):
        self.debts = [
            {"name": "Credit Card", "balance": 50000.0, "interest_rate": 36.0, "emi": 2000.0},
            {"name": "Personal Loan", "balance": 200000.0, "interest_rate": 12.0, "emi": 6500.0},
            {"name": "BNPL", "balance": 10000.0, "interest_rate": 15.0, "emi": 1000.0}
        ]

    def test_ranking_avalanche(self):
        # Avalanche: highest interest rate first (Credit Card [36%] -> BNPL [15%] -> Personal Loan [12%])
        ranked = rank_debts(self.debts, "avalanche")
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["name"], "Credit Card")
        self.assertEqual(ranked[1]["name"], "BNPL")
        self.assertEqual(ranked[2]["name"], "Personal Loan")
        self.assertEqual(ranked[0]["priority_rank"], 1)

    def test_ranking_snowball(self):
        # Snowball: smallest balance first (BNPL [10k] -> Credit Card [50k] -> Personal Loan [200k])
        ranked = rank_debts(self.debts, "snowball")
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["name"], "BNPL")
        self.assertEqual(ranked[1]["name"], "Credit Card")
        self.assertEqual(ranked[2]["name"], "Personal Loan")

    def test_compare_debt_metrics(self):
        compared = compare_debt_metrics(self.debts)
        self.assertEqual(len(compared), 3)
        # Credit card annual interest cost: 50,000 * 0.36 = 18,000
        self.assertEqual(compared[0]["annual_interest_cost"], 18000.0)

    def test_payoff_simulator(self):
        # Simulate loan payoff for Personal Loan: 2,00,000 at 12% annual rate with 6,500 EMI and 1,500 extra monthly
        result = simulate_loan_payoff(
            balance=200000.0,
            rate_annual=12.0,
            current_emi=6500.0,
            extra_monthly=1500.0
        )
        
        self.assertTrue(result["success"])
        self.assertGreater(result["months_saved"], 0)
        self.assertGreater(result["interest_saved"], 0.0)
        
        # Verify negative amortization is caught
        failed_result = simulate_loan_payoff(
            balance=200000.0,
            rate_annual=12.0,
            current_emi=1000.0  # 1000 is less than monthly interest of 200000 * 0.01 = 2000!
        )
        self.assertFalse(failed_result["success"])
        self.assertIn("Negative amortization", failed_result["error"])

if __name__ == "__main__":
    unittest.main()
