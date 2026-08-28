def calculate_tax_on_charges(charges_total: float, tax_rate_percent: float) -> float:
    """
    Calculates tax amount on a sum of charges using a given percentage.
    """
    if charges_total <= 0 or tax_rate_percent <= 0:
        return 0.0
        
    return round(charges_total * (tax_rate_percent / 100.0), 2)
