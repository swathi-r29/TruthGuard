from typing import List, Dict

def calculate_total_interest(principal: float, emi: float, tenure_months: int) -> float:
    """
    Computes total interest as: (EMI * Tenure) - Principal
    """
    if principal <= 0 or emi <= 0 or tenure_months <= 0:
        return 0.0
        
    total_repayment = emi * tenure_months
    total_interest = total_repayment - principal
    return round(max(0.0, total_interest), 2)

def generate_amortization_schedule(
    principal: float, 
    rate_annual: float, 
    tenure_months: int, 
    emi: float,
    interest_type: str = "reducing_balance"
) -> List[Dict[str, float]]:
    """
    Generates a month-by-month amortization schedule.
    """
    schedule = []
    balance = principal
    
    if principal <= 0 or tenure_months <= 0 or emi <= 0:
        return schedule
        
    is_flat = interest_type.strip().lower() == "flat_rate"
    r = (rate_annual / 12.0) / 100.0 if not is_flat else 0.0
    flat_interest_monthly = (principal * (rate_annual / 100.0) / 12.0) if is_flat else 0.0
    
    for m in range(1, tenure_months + 1):
        if balance <= 0:
            break
            
        if is_flat:
            interest_payment = flat_interest_monthly
            principal_payment = emi - interest_payment
        else:
            interest_payment = balance * r
            principal_payment = emi - interest_payment
            
        # Adjust final month payment to prevent negative balance or small rounding residues
        if m == tenure_months or balance < principal_payment:
            principal_payment = balance
            if not is_flat:
                interest_payment = balance * r
            emi = principal_payment + interest_payment
            
        balance_next = balance - principal_payment
        
        schedule.append({
            "month": m,
            "opening_balance": round(balance, 2),
            "emi": round(emi, 2),
            "principal_paid": round(principal_payment, 2),
            "interest_paid": round(interest_payment, 2),
            "closing_balance": round(max(0.0, balance_next), 2)
        })
        
        balance = balance_next
        if balance <= 0:
            break
            
    return schedule
