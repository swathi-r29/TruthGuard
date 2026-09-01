from typing import Dict, Any, List, Optional

def generate_markdown_report(
    metrics: Dict[str, Any],
    charges: List[Dict[str, Any]],
    transparency: Dict[str, Any],
    simulation: Optional[Dict[str, Any]] = None,
    recommendations: List[str] = []
) -> str:
    """
    Generates a structured educational report for download in markdown format.
    """
    currency = "₹"
    
    metrics = metrics or {}
    transparency = transparency or {}
    charges = charges or []
    
    p_val = metrics.get('loan_amount', 0.0) or 0.0
    r_val = metrics.get('interest_rate_annual', 0.0) or 0.0
    t_val = metrics.get('tenure_months', 0) or 0
    e_val = metrics.get('emi', 0.0) or 0.0
    u_val = metrics.get('upfront_fees', 0.0) or 0.0
    tx_val = metrics.get('taxes_on_fees', 0.0) or 0.0
    net_val = metrics.get('net_disbursed_amount', 0.0) or 0.0
    rep_val = metrics.get('total_scheduled_repayment', 0.0) or 0.0
    int_val = metrics.get('total_interest', 0.0) or 0.0
    cost_val = metrics.get('scheduled_total_cost', 0.0) or 0.0
    
    report = []
    report.append("# DEBT DETOX REPORT")
    report.append("### Know what your debt REALLY costs.")
    report.append("---")
    report.append("\n**IMPORTANT NOTICE**: This document is for educational purposes only. Debt Detox provides analysis based on the uploaded contract text and mathematical formulas. It should not be treated as professional financial or legal advice. Verify all terms directly with your lender.")
    report.append("\n## 1. Loan Overview & Calculations")
    
    # Financial Table
    report.append(f"| Metric | Value | Description |")
    report.append(f"| :--- | :--- | :--- |")
    report.append(f"| **Loan Amount (Principal)** | {currency}{p_val:,.2f} | The amount you borrowed |")
    report.append(f"| **Interest Rate** | {r_val}% | Annual interest rate |")
    report.append(f"| **Tenure** | {t_val} months | Total loan duration |")
    report.append(f"| **Monthly EMI** | {currency}{e_val:,.2f} | Scheduled monthly payment |")
    report.append(f"| **Upfront Fees** | {currency}{u_val:,.2f} | Fees deducted before payout |")
    report.append(f"| **Taxes on Fees** | {currency}{tx_val:,.2f} | GST/taxes on upfront fees |")
    report.append(f"| **Amount Actually Received** | **{currency}{net_val:,.2f}** | What you received after fees |")
    report.append(f"| **Total Scheduled Repayments** | {currency}{rep_val:,.2f} | Sum of all scheduled payments |")
    report.append(f"| **Total Interest Payable** | {currency}{int_val:,.2f} | Cost of credit |")
    report.append(f"| **Scheduled Total Cost** | **{currency}{cost_val:,.2f}** | Total interest + upfront costs |")
    
    # Transparency Score
    score_val = transparency.get('score', 0)
    tb = transparency.get("breakdown", {}) if isinstance(transparency.get("breakdown"), dict) else {}
    report.append(f"\n## 2. Debt Detox Transparency Score: {score_val}/100")
    report.append("A custom index assessing the consumer-friendliness of your loan terms:")
    report.append(f"- **Information Completeness**: {tb.get('information_completeness', 0)}/15")
    report.append(f"- **Prepayment Conditions**: {tb.get('prepayment_conditions', 0)}/15")
    report.append(f"- **Penalty Exposure**: {tb.get('penalty_exposure', 0)}/15")
    report.append(f"- **Fee Clarity**: {tb.get('fee_clarity', 0)}/20")
    report.append(f"- **Contract Complexity**: {tb.get('contract_complexity', 0)}/15")
    report.append(f"- **Additional Charges Score**: {tb.get('additional_charges', 0)}/20")
    
    # Charges Breakdown
    report.append("\n## 3. Detected Charges List")
    
    # Standardize output for charges
    report.append("| Charge Name | Rate/Value | Type | Description | Page |")
    report.append("| :--- | :--- | :--- | :--- | :--- |")
    
    for c in charges:
        val_str = "Mentioned"
        val = c.get("value")
        unit = c.get("unit")
        if val is not None:
            if unit == "percent":
                val_str = f"{val}%"
            elif isinstance(val, (int, float)):
                val_str = f"{currency}{val:,.2f}"
            else:
                val_str = str(val)
                
        classification = c.get("classification", "OTHER")
        evidence = c.get("evidence", "").replace("\n", " ").strip()
        page = c.get("page", 1)
        
        report.append(f"| {c['original_name']} | {val_str} | {classification} | {evidence[:60]}... | Page {page} |")
        
    # Recommendations
    if recommendations:
        report.append("\n## 4. Key Actions & Recommendations")
        for rec in recommendations:
            report.append(f"- {rec}")
            
    # Payoff Simulation
    if simulation and simulation.get("success"):
        report.append("\n## 5. Payoff Acceleration Simulation")
        report.append(f"- **Normal Payoff Timeline**: {simulation['normal_months']} months")
        report.append(f"- **Accelerated Payoff Timeline**: {simulation['accelerated_months']} months")
        report.append(f"- **Timeline Reduction**: **{simulation['months_saved']} months saved**")
        report.append(f"- **Total Interest Saved**: **{currency}{simulation['interest_saved']:,.2f}**")
        report.append(f"- **Accelerated Total Repayment**: {currency}{simulation['accelerated_total_repayment']:,.2f} (vs {currency}{simulation['normal_total_repayment']:,.2f} normal)")
        
    report.append("\n---")
    report.append("*Report generated by Debt Detox AI. Processed locally.*")
    
    return "\n".join(report)
