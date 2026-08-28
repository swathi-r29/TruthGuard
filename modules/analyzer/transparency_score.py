from typing import Dict, List, Any

def calculate_transparency_score(
    metrics: Dict[str, Any],
    charges: List[Dict[str, Any]],
    page_count: int
) -> Dict[str, Any]:
    """
    Computes the Debt Detox Transparency Score (0-100) based on six educational factors:
    1. Information Completeness (Max: 15)
    2. Prepayment Conditions (Max: 15)
    3. Penalty Exposure (Max: 15)
    4. Fee Clarity (Max: 20)
    5. Contract Complexity (Max: 15)
    6. Additional Charges (Max: 20)
    """
    
    # 1. Information Completeness (Max: 15)
    # Check presence of Principal, Rate, Tenure
    info_completeness = 0
    if metrics.get("loan_amount", 0) > 0:
        info_completeness += 5
    if metrics.get("interest_rate_annual", 0) > 0:
        info_completeness += 5
    if metrics.get("tenure_months", 0) > 0:
        info_completeness += 5
        
    # 2. Prepayment Conditions (Max: 15)
    # Prepayment penalties or lock-ins reduce this score
    prepayment_conditions = 15
    has_foreclosure = any(c["canonical_name"] == "foreclosure_charge" for c in charges)
    has_prepayment = any(c["canonical_name"] == "prepayment_charge" for c in charges)
    has_lock_in = any(c["canonical_name"] == "lock_in_period" for c in charges)
    
    if has_foreclosure:
        prepayment_conditions -= 7
    if has_prepayment:
        prepayment_conditions -= 5
    if has_lock_in:
        prepayment_conditions -= 3
    prepayment_conditions = max(0, prepayment_conditions)
    
    # 3. Penalty Exposure (Max: 15)
    # Penalties for late payments, bounce charges, default interest
    penalty_exposure = 15
    has_late = any(c["canonical_name"] == "late_payment_fee" for c in charges)
    has_bounce = any(c["canonical_name"] == "bounce_charge" for c in charges)
    has_default = any(c["canonical_name"] == "default_penalty" for c in charges)
    
    if has_late:
        penalty_exposure -= 5
    if has_bounce:
        penalty_exposure -= 5
    if has_default:
        penalty_exposure -= 5
    penalty_exposure = max(0, penalty_exposure)
    
    # 4. Fee Clarity (Max: 20)
    # Deduct points if charges are mentioned but their values are unknown or not clearly stated
    fee_clarity = 20
    unclear_charges = sum(1 for c in charges if c["source"] == "keyword_reference" or c["value"] is None)
    fee_clarity -= unclear_charges * 4
    
    # Check if GST is mentioned without rate
    has_gst_without_rate = any(c["canonical_name"] == "gst_tax_references" and c["value"] is None for c in charges)
    if has_gst_without_rate:
        fee_clarity -= 4
        
    fee_clarity = max(0, fee_clarity)
    
    # 5. Contract Complexity (Max: 15)
    # Shorter contracts are typically easier for consumers to read
    contract_complexity = 15
    if page_count > 15:
        contract_complexity -= 10
    elif page_count > 8:
        contract_complexity -= 7
    elif page_count > 3:
        contract_complexity -= 4
    elif page_count > 1:
        contract_complexity -= 2
    contract_complexity = max(0, contract_complexity)
    
    # 6. Additional Charges (Max: 20)
    # Count how many extra fees (ADDITIONAL_COST or OPTIONAL_COST) are added to the debt
    additional_charges_score = 20
    additional_cost_count = sum(1 for c in charges if c["classification"] in ["ADDITIONAL_COST", "OPTIONAL_COST"])
    
    additional_charges_score -= additional_cost_count * 4
    additional_charges_score = max(0, additional_charges_score)
    
    # Sum it up
    total_score = (
        info_completeness +
        prepayment_conditions +
        penalty_exposure +
        fee_clarity +
        contract_complexity +
        additional_charges_score
    )
    
    return {
        "score": total_score,
        "breakdown": {
            "information_completeness": info_completeness,
            "prepayment_conditions": prepayment_conditions,
            "penalty_exposure": penalty_exposure,
            "fee_clarity": fee_clarity,
            "contract_complexity": contract_complexity,
            "additional_charges": additional_charges_score
        }
    }
