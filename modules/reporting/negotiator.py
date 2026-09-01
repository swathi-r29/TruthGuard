from typing import Dict, List, Any
import datetime

def generate_negotiation_letter(
    metrics: Dict[str, Any],
    charges: List[Dict[str, Any]],
    doc_name: str,
    currency: str = "₹"
) -> str:
    """
    Generates a personalized, professional loan terms negotiation and waiver request letter.
    """
    stated_rate = metrics.get("interest_rate_annual", 0.0)
    real_apr = metrics.get("real_apr", 0.0)
    loan_amount = metrics.get("loan_amount", 0.0)
    net_disbursed = metrics.get("net_disbursed_amount", 0.0)
    upfront_fees = metrics.get("upfront_fees", 0.0)
    taxes = metrics.get("taxes_on_fees", 0.0)
    
    lender = "Lender Operations Department"
    borrower = "Jane Doe"
    
    # Try to find lender/borrower from charges/session state/extracted if possible
    # We can search through charges to see if we can find borrower/lender
    lender_charge = [c for c in charges if c["canonical_name"] == "lender_name"]
    if lender_charge and lender_charge[0].get("value"):
        lender = lender_charge[0]["value"]
        
    borrower_charge = [c for c in charges if c["canonical_name"] == "borrower_name"]
    if borrower_charge and borrower_charge[0].get("value"):
        borrower = borrower_charge[0]["value"]

    today = datetime.date.today().strftime("%B %d, %Y")
    
    letter_lines = []
    letter_lines.append(f"Date: {today}")
    letter_lines.append(f"To: Customer Relations & Grievance Department")
    letter_lines.append(f"Lender: {lender}")
    letter_lines.append("")
    letter_lines.append(f"Subject: Request for Waiver of Non-Disclosure Fees & Stated APR Review")
    letter_lines.append(f"Reference: Audit of Loan Agreement Document '{doc_name}'")
    letter_lines.append("")
    letter_lines.append(f"Dear Sir / Madam,")
    letter_lines.append("")
    letter_lines.append(f"I am writing in connection with the personal credit facility / loan agreement of principal amount {currency}{loan_amount:,.2f} associated with my account.")
    letter_lines.append("")
    letter_lines.append(f"Recently, I performed a detailed financial audit of the loan agreement using the Debt Detox Audit Engine. The audit reveals that the actual economic cost of this credit is significantly higher than the stated terms, resulting in an Effective APR of {real_apr:.2f}%, which is a markup of {(real_apr - stated_rate):.2f}% over the nominal rate of {stated_rate:.2f}%.")
    letter_lines.append("")
    letter_lines.append("I kindly request your department to review, clarify, and adjust the following cost elements in my contract:")
    letter_lines.append("")
    
    # List upfront fee deductions
    upfront_items = [c for c in charges if c["classification"] in ["ADDITIONAL_COST", "TAX", "OPTIONAL_COST"]]
    if upfront_items:
        letter_lines.append("1. HIGH UPFRONT DEDUCTIONS:")
        for c in upfront_items:
            name = c.get("original_name") or c.get("canonical_name").replace("_", " ").title()
            val = c.get("value")
            unit = c.get("unit")
            page = c.get("page", 1)
            
            val_str = f"{val}%" if unit == "percent" else f"{currency}{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            letter_lines.append(f"  - {name}: {val_str} (Page {page})")
        
        letter_lines.append(f"  * These upfront deductions reduce my net disbursed amount to {currency}{net_disbursed:,.2f} while I am forced to pay interest on the full {currency}{loan_amount:,.2f} principal. I request a partial waiver of these processing and administrative charges.")
        letter_lines.append("")

    # List foreclosure / prepayment penalty
    penalty_items = [c for c in charges if c["classification"] in ["CONDITIONAL_COST", "PENALTY"]]
    if penalty_items:
        letter_lines.append("2. PREDATORY CONDITIONAL FEES & EARLY CLOSURE PENALTIES:")
        for c in penalty_items:
            name = c.get("original_name") or c.get("canonical_name").replace("_", " ").title()
            val = c.get("value")
            unit = c.get("unit")
            page = c.get("page", 1)
            
            val_str = f"{val}%" if unit == "percent" else f"{currency}{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            letter_lines.append(f"  - {name}: {val_str} (Page {page})")
            
        letter_lines.append("  * Prepayment and foreclosure penalties are highly restrictive and deter consumers from clearing their liabilities. Under modern fair lending guidelines, early payment charges should be waived. I request that these penalties be removed from my active loan file.")
        letter_lines.append("")

    letter_lines.append("I request that your team provide:")
    letter_lines.append(f"  a) A written justification explaining why the calculated Effective APR ({real_apr:.2f}%) differs so significantly from the stated interest rate ({stated_rate:.2f}%).")
    letter_lines.append(f"  b) An adjusted repayment schedule reflecting waivers on processing fees or the deletion of the voluntary insurance premium (if optional).")
    letter_lines.append("")
    letter_lines.append("I value my relationship with your institution and hope we can resolve this mismatch transparently. I look forward to your response within 7 business days.")
    letter_lines.append("")
    letter_lines.append("Sincerely,")
    letter_lines.append(f"{borrower}")
    
    return "\n".join(letter_lines)
