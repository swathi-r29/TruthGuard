from typing import Dict, List, Any

def simulate_loan_payoff(
    balance: float,
    rate_annual: float,
    current_emi: float,
    extra_monthly: float = 0.0,
    one_time_payment: float = 0.0,
    one_time_month: int = 1
) -> Dict[str, Any]:
    """
    Simulates normal vs. accelerated payoff schedules.
    Returns months saved, interest saved, and complete schedules.
    """
    if balance <= 0 or current_emi <= 0:
        return {
            "error": "Balance and EMI must be greater than zero.",
            "success": False
        }
        
    monthly_rate = (rate_annual / 12.0) / 100.0
    
    # Safety Check: Negative amortization (EMI doesn't cover interest)
    monthly_interest_accruing = balance * monthly_rate
    if current_emi <= monthly_interest_accruing:
        return {
            "error": f"Negative amortization detected: Your monthly EMI (₹{current_emi:,.2f}) is lower than "
                     f"or equal to the monthly interest accrual (₹{monthly_interest_accruing:,.2f}). "
                     f"Your debt will grow rather than shrink. Increase your monthly payment.",
            "success": False
        }

    # 1. Normal Payoff Schedule
    normal_schedule = []
    curr_balance = balance
    total_normal_interest = 0.0
    month = 0
    
    while curr_balance > 0.009 and month < 600:  # Max 50 years to prevent infinite loops
        month += 1
        interest_charge = curr_balance * monthly_rate
        principal_payment = current_emi - interest_charge
        
        if curr_balance < principal_payment:
            principal_payment = curr_balance
            
        emi = principal_payment + interest_charge
        total_normal_interest += interest_charge
        curr_balance_next = curr_balance - principal_payment
        
        normal_schedule.append({
            "month": month,
            "opening_balance": round(curr_balance, 2),
            "payment": round(emi, 2),
            "interest": round(interest_charge, 2),
            "principal": round(principal_payment, 2),
            "closing_balance": round(max(0.0, curr_balance_next), 2)
        })
        curr_balance = curr_balance_next
        
    normal_months = month
    
    # 2. Accelerated Payoff Schedule
    accelerated_schedule = []
    curr_balance = balance
    total_acc_interest = 0.0
    month = 0
    
    while curr_balance > 0.009 and month < 600:
        month += 1
        interest_charge = curr_balance * monthly_rate
        
        # Calculate payment for this month
        actual_payment = current_emi + extra_monthly
        
        # Add one-time payment if applicable
        if one_time_payment > 0 and month == one_time_month:
            actual_payment += one_time_payment
            
        principal_payment = actual_payment - interest_charge
        
        if curr_balance < principal_payment:
            principal_payment = curr_balance
            
        emi = principal_payment + interest_charge
        total_acc_interest += interest_charge
        curr_balance_next = curr_balance - principal_payment
        
        accelerated_schedule.append({
            "month": month,
            "opening_balance": round(curr_balance, 2),
            "payment": round(emi, 2),
            "interest": round(interest_charge, 2),
            "principal": round(principal_payment, 2),
            "closing_balance": round(max(0.0, curr_balance_next), 2)
        })
        curr_balance = curr_balance_next
        
    accelerated_months = month
    
    # 3. Calculate Savings
    months_saved = max(0, normal_months - accelerated_months)
    interest_saved = max(0.0, total_normal_interest - total_acc_interest)
    
    return {
        "success": True,
        "normal_months": normal_months,
        "normal_total_interest": round(total_normal_interest, 2),
        "normal_total_repayment": round(balance + total_normal_interest, 2),
        "normal_schedule": normal_schedule,
        "accelerated_months": accelerated_months,
        "accelerated_total_interest": round(total_acc_interest, 2),
        "accelerated_total_repayment": round(balance + total_acc_interest, 2),
        "accelerated_schedule": accelerated_schedule,
        "months_saved": months_saved,
        "interest_saved": round(interest_saved, 2)
    }
