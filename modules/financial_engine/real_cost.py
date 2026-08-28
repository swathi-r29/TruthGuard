from typing import List, Dict, Any, Optional
from .emi import calculate_reducing_emi, calculate_flat_emi
from .interest import calculate_total_interest
from .fees import calculate_fee_value
from .taxes import calculate_tax_on_charges

def calculate_real_cost_metrics(
    principal: float,
    interest_rate_annual: float,
    tenure_months: int,
    charges: List[Dict[str, Any]],
    interest_type: str = "reducing_balance",
    override_emi: Optional[float] = None,
    tax_rate_percent: float = 0.0,
    outstanding_principal: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes all deterministic financial metrics for the loan agreement.
    Categorizes costs into scheduled, upfront, recurring, and conditional.
    """
    # 1. Determine EMI
    if override_emi and override_emi > 0:
        emi = override_emi
    else:
        if interest_type == "flat_rate":
            emi = calculate_flat_emi(principal, interest_rate_annual, tenure_months)
        else:
            emi = calculate_reducing_emi(principal, interest_rate_annual, tenure_months)
            
    # 2. Base calculations
    total_repayment = emi * tenure_months
    total_interest = max(0.0, total_repayment - principal)
    
    # 3. Compile fees
    upfront_fees = 0.0
    mandatory_recurring = 0.0
    optional_fees = 0.0
    taxes_on_fees = 0.0
    
    additional_costs_list = []
    conditional_costs_list = []
    penalties_list = []
    optional_costs_list = []
    
    for c in charges:
        name = c.get("original_name", c.get("canonical_name", ""))
        val = c.get("value")
        unit = c.get("unit")
        basis = c.get("basis")
        evidence = c.get("evidence", "")
        page = c.get("page", 1)
        classification = c.get("classification", "OTHER")
        
        # Calculate absolute value if numeric
        absolute_value = 0.0
        if val is not None and isinstance(val, (int, float)):
            # If basis is outstanding_principal, calculate fee based on outstanding principal (if provided and > 0, else principal)
            calc_outstanding = outstanding_principal if (outstanding_principal is not None and outstanding_principal > 0) else principal
            fee_base = calc_outstanding if basis == "outstanding_principal" else principal
            absolute_value = calculate_fee_value(fee_base, val, unit)
            
        charge_summary = {
            "name": name,
            "raw_value": val,
            "unit": unit,
            "basis": basis,
            "absolute_value": absolute_value,
            "page": page,
            "evidence": evidence,
            "classification": classification
        }
        
        if classification == "ADDITIONAL_COST":
            # Check if recurring
            if basis == "monthly":
                mandatory_recurring += absolute_value * tenure_months
                additional_costs_list.append(charge_summary)
            elif basis == "annual":
                years = max(1, round(tenure_months / 12))
                mandatory_recurring += absolute_value * years
                additional_costs_list.append(charge_summary)
            else:
                # Assume upfront
                upfront_fees += absolute_value
                additional_costs_list.append(charge_summary)
                
        elif classification == "TAX":
            taxes_on_fees += absolute_value
            
        elif classification == "CONDITIONAL_COST":
            conditional_costs_list.append(charge_summary)
            
        elif classification == "PENALTY":
            penalties_list.append(charge_summary)
            
        elif classification == "OPTIONAL_COST":
            optional_fees += absolute_value
            optional_costs_list.append(charge_summary)
            
    # 4. Calculate default/configured taxes if applicable references are found
    # If the user provides a custom tax rate (or if we found tax references but no rate, we can apply the rate)
    if tax_rate_percent > 0:
        taxes_on_fees = calculate_tax_on_charges(upfront_fees, tax_rate_percent)
        
    # 5. Net disbursement calculation (amount borrower actually receives)
    # Deduct upfront mandatory fees and taxes from principal
    upfront_deductions = upfront_fees + taxes_on_fees
    net_disbursed_amount = max(0.0, principal - upfront_deductions)
    
    # 6. Total guaranteed cost (Interest + upfront fees + upfront taxes + recurring fees)
    total_scheduled_fees = upfront_fees + taxes_on_fees + mandatory_recurring
    scheduled_total_cost = total_interest + total_scheduled_fees
    total_scheduled_repayment = total_repayment + mandatory_recurring
    
    return {
        "loan_amount": round(principal, 2),
        "interest_rate_annual": interest_rate_annual,
        "tenure_months": tenure_months,
        "emi": round(emi, 2),
        "total_scheduled_repayment": round(total_scheduled_repayment, 2),
        "total_interest": round(total_interest, 2),
        "upfront_fees": round(upfront_fees, 2),
        "taxes_on_fees": round(taxes_on_fees, 2),
        "mandatory_recurring_fees": round(mandatory_recurring, 2),
        "optional_fees": round(optional_fees, 2),
        "net_disbursed_amount": round(net_disbursed_amount, 2),
        "scheduled_total_cost": round(scheduled_total_cost, 2),
        "additional_costs": additional_costs_list,
        "conditional_costs": conditional_costs_list,
        "penalties": penalties_list,
        "optional_costs": optional_costs_list
    }
