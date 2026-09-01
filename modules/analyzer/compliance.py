from typing import Dict, List, Any

def check_regulatory_compliance(
    metrics: Dict[str, Any],
    charges: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Analyzes loan metrics and charges against standard consumer protection regulations.
    Returns a list of alerts, categorized by severity (CRITICAL, WARNING, INFO).
    """
    alerts = []
    
    # 1. Usury Check
    real_apr = metrics.get("real_apr", 0.0)
    if real_apr > 36.0:
        alerts.append({
            "severity": "CRITICAL",
            "title": "Predatory Interest Rate (Usury Limit)",
            "description": f"The calculated Effective APR of {real_apr:.2f}% exceeds the 36% consumer protection threshold widely recognized as predatory.",
            "impact": "Exorbitant cost that will trap you in a high-interest debt spiral.",
            "law_reference": "CFPB Usury Guidelines / Consumer Protection Caps"
        })
    elif real_apr > 24.0:
        alerts.append({
            "severity": "WARNING",
            "title": "High Interest Rate Warning",
            "description": f"The calculated Effective APR of {real_apr:.2f}% is high, indicating standard credit lines might be overpriced.",
            "impact": "Significantly higher debt service payments than average prime loans.",
            "law_reference": "Fair Practice Guidelines"
        })

    # 2. Hidden APR Markups (difference between Effective APR and Stated Rate)
    stated_rate = metrics.get("interest_rate_annual", 0.0)
    markup = real_apr - stated_rate
    if markup > 3.0:
        alerts.append({
            "severity": "WARNING",
            "title": "Significant Hidden Cost Markup",
            "description": f"The real cost (Effective APR {real_apr:.2f}%) exceeds the stated rate ({stated_rate:.2f}%) by {markup:.2f}%.",
            "impact": "Indicates heavy upfront fee deductions, gst charges, or bundled insurance premiums that decrease your net cash in hand.",
            "law_reference": "Truth in Lending Act (TILA) / APR Disclosure Regulations"
        })

    # 3. Excessive Processing Fee
    # Check for processing_fee percentage
    processing_fee_charge = [c for c in charges if c["canonical_name"] == "processing_fee"]
    if processing_fee_charge:
        pf = processing_fee_charge[0]
        val = pf.get("value")
        # Try to parse numeric value
        pf_pct = 0.0
        if isinstance(val, (int, float)):
            pf_pct = float(val) if pf.get("unit") == "percent" else (float(val) / metrics.get("loan_amount", 1.0) * 100.0)
        else:
            # Try to clean/extract float
            import re
            match = re.search(r'-?\d+(?:\.\d+)?', str(val or ""))
            if match:
                try:
                    pf_pct = float(match.group(0))
                except ValueError:
                    pass
        
        if pf_pct > 3.0:
            alerts.append({
                "severity": "WARNING",
                "title": "Excessive Processing Fee",
                "description": f"The processing fee of {pf_pct:.1f}% exceeds standard retail loan benchmarks (normally capped below 2-3%).",
                "impact": f"Increases upfront costs by ₹{metrics.get('upfront_fees', 0.0):,.2f}, reducing your net payout.",
                "law_reference": "Fair Practices Code / Processing Fee Transparency Standards"
            })

    # 4. Foreclosure/Prepayment Charges Check
    foreclosure_charge = [c for c in charges if c["canonical_name"] == "foreclosure_charge"]
    prepayment_charge = [c for c in charges if c["canonical_name"] == "prepayment_charge"]
    
    if foreclosure_charge or prepayment_charge:
        desc_parts = []
        if foreclosure_charge:
            desc_parts.append(f"foreclosure penalty ({foreclosure_charge[0].get('value')})")
        if prepayment_charge:
            desc_parts.append(f"prepayment penalty ({prepayment_charge[0].get('value')})")
            
        alerts.append({
            "severity": "WARNING",
            "title": "Early Debt Payoff Penalties Active",
            "description": f"The loan contract penalizes you for trying to clear your debt early: {', '.join(desc_parts)}.",
            "impact": "Restricts your ability to prepay or switch to a lower interest lender. (Note: Many modern regulations, such as RBI for floating-rate personal loans, prohibit early closure fees).",
            "law_reference": "National Central Bank Fair Lending Codes / Consumer Prepayment Rights"
        })

    # 5. Over-the-Limit Default Penalty Caps
    late_fee_charge = [c for c in charges if c["canonical_name"] == "late_payment_fee"]
    bounce_charge = [c for c in charges if c["canonical_name"] == "bounce_charge"]
    
    excessive_penalty = False
    details = []
    
    if late_fee_charge:
        lf_val = late_fee_charge[0].get("value")
        if isinstance(lf_val, (int, float)) and lf_val > 500.0:
            excessive_penalty = True
            details.append(f"Late fee is ₹{lf_val:,.2f} (exceeds ₹500 standard)")
            
    if bounce_charge:
        bc_val = bounce_charge[0].get("value")
        if isinstance(bc_val, (int, float)) and bc_val > 500.0:
            excessive_penalty = True
            details.append(f"Bounce charge is ₹{bc_val:,.2f} (exceeds ₹500 standard)")

    if excessive_penalty:
        alerts.append({
            "severity": "WARNING",
            "title": "High Default/Penalty Fees Detected",
            "description": f"Penalties are set above recommended consumer thresholds: {', '.join(details)}.",
            "impact": "Defaulting or cheque bouncing will rapidly escalate your outstanding balance during cash-flow shortages.",
            "law_reference": "CFPB Late Fee Rules / National Banking Regulations on Penal Charges"
        })

    return alerts
