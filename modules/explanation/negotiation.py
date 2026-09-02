"""
Dispute & Negotiation Letter Generator for Debt Detox.
Generates formal, legally grounded fee waiver & renegotiation request letters
using extracted ACTIVE_LOAN data (zero hardcoded values).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

def generate_dispute_letter(
    active_loan: Dict[str, Any],
    selected_charges: Optional[List[str]] = None,
    borrower_name: str = "Borrower",
    custom_notes: str = ""
) -> str:
    """
    Generates a formal, professional dispute and fee waiver request letter
    based on extracted loan contract terms and compliance findings.
    """
    doc_name = active_loan.get("doc_name", "Loan Agreement")
    metrics = active_loan.get("metrics", {})
    charges = active_loan.get("charges", [])
    alerts = active_loan.get("compliance_alerts", [])
    extracted = active_loan.get("extracted", None)

    # Extract dynamic values
    principal = metrics.get("loan_amount", 0.0)
    stated_rate = metrics.get("interest_rate_annual", 0.0)
    real_apr = metrics.get("real_apr", 0.0)
    tenure = metrics.get("tenure_months", 0)
    upfront_fees = metrics.get("upfront_fees", 0.0)
    net_disbursed = metrics.get("net_disbursed_amount", 0.0)
    
    # Try to extract lender name or reference if available in schema
    lending_inst = "Lending Institution"
    doc_ref = doc_name
    if extracted:
        lending_inst = getattr(getattr(extracted, 'lending_institution', None), 'value', None) or "Lending Institution"
        doc_ref = getattr(getattr(extracted, 'document_reference', None), 'value', None) or doc_name

    date_str = datetime.now().strftime("%B %d, %Y")

    # Filter targeted charges
    target_charges = charges
    if selected_charges:
        target_charges = [c for c in charges if c.get("canonical_name") in selected_charges]

    # Build letter sections
    letter = f"""FORMAL REQUEST FOR FEE WAIVER & CONTRACT RE-EXAMINATION

Date: {date_str}
To: The Loan Operations & Grievance Redressal Officer
Lender: {lending_inst}
Re: Contract Audit & Dispute Notice — Reference: {doc_ref}
Borrower Name: {borrower_name}

--------------------------------------------------------------------------------

Dear Sir/Madam,

I am writing to formally request a review and re-examination of specific terms, fee structures, and disclosure conditions contained in my credit agreement ({doc_ref}). 

An independent financial audit of the contract terms reveals significant divergences between advertised loan costs and total effective debt obligations:

SUMMARY OF AUDIT FINDINGS:
--------------------------
1. Sanctioned Principal Amount: ₹{principal:,.2f}
2. Stated Annual Interest Rate: {stated_rate:.2f}% p.a.
3. Effective Annual Rate (Real APR): {real_apr:.2f}% p.a. (Hidden APR Markup: +{real_apr - stated_rate:.2f}%)
4. Upfront Deductions & Fees: ₹{upfront_fees:,.2f} (Net Disbursement: ₹{net_disbursed:,.2f})
5. Repayment Tenure: {tenure} Months

SPECIFIC CLAUSES UNDER DISPUTE / REQUEST FOR WAIVER:
---------------------------------------------------
"""

    if not target_charges:
        letter += "• Upfront Fee Structure: General request to review processing and administrative deductions.\n"
    else:
        for idx, charge in enumerate(target_charges, 1):
            name = charge.get("canonical_name", "fee").replace("_", " ").title()
            val = charge.get("value")
            unit = charge.get("unit", "")
            basis = charge.get("basis", "")
            evidence = charge.get("evidence", "No evidence quote.")
            page = charge.get("page", 1)

            val_str = f"₹{val:,.2f}" if isinstance(val, (int, float)) and unit != "percent" else f"{val}%"

            letter += f"{idx}. Clause / Charge: {name} ({val_str})\n"
            letter += f"   - Basis: {basis.replace('_', ' ').title()}\n"
            letter += f"   - Contract Evidence (Page {page}): \"{evidence}\"\n"

            # Add legal context based on charge type
            if "foreclosure" in name.lower() or "prepayment" in name.lower():
                letter += "   - Ground for Waiver: National central bank consumer guidelines prohibit foreclosure / early closure penalties on floating-rate individual retail credit lines.\n"
            elif "processing" in name.lower():
                letter += "   - Ground for Waiver: Upfront processing fee exceeds standard retail benchmarks and reduces net disbursement cash in hand.\n"
            elif "bounce" in name.lower() or "late" in name.lower():
                letter += "   - Ground for Waiver: Penal default charges must be reasonable and strictly cost-reflective rather than punitive.\n"
            letter += "\n"

    # Add compliance alerts if present
    if alerts:
        letter += "REGULATORY & FAIR PRACTICE CONCERNS:\n"
        letter += "------------------------------------\n"
        for alert in alerts:
            letter += f"• [{alert.get('severity', 'WARNING')}] {alert.get('title')}: {alert.get('description')}\n"
            letter += f"  Reference Standard: {alert.get('law_reference')}\n"
        letter += "\n"

    if custom_notes.strip():
        letter += f"ADDITIONAL BORROWER STATEMENT:\n------------------------------\n{custom_notes.strip()}\n\n"

    letter += f"""FORMAL RELIEF REQUESTED:
------------------------
In light of the above findings, I respectfully request that {lending_inst}:
1. Waive or reduce the disputed upfront and penalty fees listed above prior to final settlement.
2. Provide a clear, written APR disclosure breakdown confirming the net effective interest rate.
3. Confirm in writing that no un-disclosed post-disbursement fees will be levied.

I look forward to your prompt response and written confirmation within 7 working days.

Sincerely,

_______________________________
{borrower_name}
Contact Reference: {doc_ref}
Audit Verification Code: DEBT-DETOX-{hash(doc_name) & 0xFFFFFF:06X}
"""
    return letter
