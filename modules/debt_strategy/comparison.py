from typing import List, Dict, Any

def compare_debt_metrics(debts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Standardizes and calculates key comparison metrics for a list of debts.
    Adds derived comparison fields:
      - 'annual_interest_cost': balance * interest_rate / 100
      - 'monthly_interest_cost': balance * (interest_rate / 12) / 100
    """
    comparison_list = []
    
    for d in debts:
        balance = float(d.get("balance", 0.0))
        rate = float(d.get("interest_rate", 0.0))
        
        # Calculate interest costs
        annual_interest = balance * (rate / 100.0)
        monthly_interest = annual_interest / 12.0
        
        comparison_list.append({
            "name": d.get("name", "Unnamed Debt"),
            "balance": round(balance, 2),
            "interest_rate": round(rate, 2),
            "emi": round(float(d.get("emi", 0.0)), 2),
            "annual_interest_cost": round(annual_interest, 2),
            "monthly_interest_cost": round(monthly_interest, 2),
            "penalty_exposure": d.get("penalty_exposure", "Standard"),
            "fees_detected": d.get("fees_detected", "None")
        })
        
    return comparison_list
