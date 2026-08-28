def calculate_reducing_emi(principal: float, rate_annual: float, tenure_months: int) -> float:
    """
    Calculates the Equated Monthly Installment (EMI) using the reducing balance method.
    Formula: EMI = [P x r x (1+r)^n] / [((1+r)^n) - 1]
    where r is monthly interest rate, n is tenure in months.
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0
        
    if rate_annual <= 0:
        return principal / tenure_months
        
    r = (rate_annual / 12.0) / 100.0
    n = float(tenure_months)
    
    try:
        emi = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        return round(emi, 2)
    except ZeroDivisionError:
        return round(principal / tenure_months, 2)

def calculate_flat_emi(principal: float, rate_annual: float, tenure_months: int) -> float:
    """
    Calculates flat-rate loan EMI: Interest is calculated on the initial principal throughout.
    Formula: Total Interest = P x (R/100) x (Tenure in Years)
             EMI = (P + Total Interest) / Tenure in Months
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0
        
    if rate_annual <= 0:
        return principal / tenure_months
        
    years = tenure_months / 12.0
    total_interest = principal * (rate_annual / 100.0) * years
    emi = (principal + total_interest) / tenure_months
    return round(emi, 2)
