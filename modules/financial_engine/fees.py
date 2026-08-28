from typing import Optional

def calculate_fee_value(principal: float, value: Optional[float], unit: Optional[str]) -> float:
    """
    Computes the absolute value of a fee.
    If the fee is percentage-based, returns principal * percentage / 100.
    Otherwise, returns the fixed fee amount.
    """
    if value is None or value <= 0:
        return 0.0
        
    unit_str = str(unit).strip().lower() if unit else "currency"
    
    if "percent" in unit_str or unit_str == "%":
        return round(principal * (value / 100.0), 2)
        
    return round(value, 2)
