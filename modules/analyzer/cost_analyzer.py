from typing import Dict, Any, Optional

def solve_monthly_irr(net_disbursed: float, monthly_outflow: float, tenure_months: int) -> Optional[float]:
    """
    Solves for the monthly Internal Rate of Return (IRR) using bisection search.
    Solves: Net Disbursed = Sum_{t=1}^n [Monthly Outflow / (1 + IRR)^t]
    """
    if net_disbursed <= 0 or monthly_outflow <= 0 or tenure_months <= 0:
        return None
        
    total_repayments = monthly_outflow * tenure_months
    if total_repayments <= net_disbursed:
        # If total repayments are less than or equal to net received, interest rate is 0 or negative
        return 0.0
        
    # Bisection search parameters
    low = 0.0
    high = 2.0  # Cap search at 200% monthly interest rate
    tolerance = 1e-9
    max_iterations = 200
    
    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        # Compute Net Present Value of outflows
        npv = 0.0
        for t in range(1, tenure_months + 1):
            npv += monthly_outflow / ((1 + mid) ** t)
            
        diff = npv - net_disbursed
        
        if abs(diff) < tolerance:
            return mid
            
        if diff > 0:
            # Need a higher rate to reduce NPV
            low = mid
        else:
            # Need a lower rate to increase NPV
            high = mid
            
    return low

def calculate_effective_rates(net_disbursed: float, emi: float, tenure_months: int) -> Dict[str, Any]:
    """
    Calculates the nominal and effective annual rate based on monthly cash flows.
    Returns: {
        "nominal_annual_cost_rate": float or None,
        "effective_annual_cost_rate": float or None,
        "status": str
    }
    """
    irr_monthly = solve_monthly_irr(net_disbursed, emi, tenure_months)
    
    if irr_monthly is None:
        return {
            "nominal_annual_cost_rate": None,
            "effective_annual_cost_rate": None,
            "status": "Effective annual cost could not be reliably calculated from the available document information."
        }
        
    nominal_annual = irr_monthly * 12.0 * 100.0
    effective_annual = (((1.0 + irr_monthly) ** 12.0) - 1.0) * 100.0
    
    return {
        "nominal_annual_cost_rate": round(nominal_annual, 2),
        "effective_annual_cost_rate": round(effective_annual, 2),
        "status": "Success"
    }
