import os
from pathlib import Path
import fitz  # PyMuPDF

def generate_personal_loan(output_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    
    text = """
APEX LENDING SERVICES - PERSONAL LOAN CONTRACT
==============================================

Lending Institution: Apex Lending Services Ltd.
Borrower: John Doe
Document Reference: AL-98492019-PD

LOAN SPECIFICATIONS:
-------------------
1. Loan Principal Amount: INR 3,00,000 (Rupees Three Lakhs Only)
2. Nominal Interest Rate: 14.5% per annum
3. Interest Calculation: Reducing Balance Method
4. Loan Tenure: 36 Months
5. Equated Monthly Installment (EMI): INR 10,327.50
6. Number of Scheduled Installments: 36 Months

UPFRONT CHARGES & FEES:
----------------------
- Processing Fee: 2.5% of the principal loan amount (plus applicable taxes), deducted from disbursement.
- Documentation & Stamp Duty: Fixed charge of INR 1,500, deducted upfront.
- Insurance Protection Plan: Optional credit guard shield insurance premium of INR 6,000. (The borrower has opted for this protection).
- Taxes on Charges: GST of 18% is applicable on all processing and documentation fees.

CONDITIONAL FEES & CHARGES:
--------------------------
- Foreclosure/Prepayment Charge: In case of early closure of the loan before the scheduled maturity, a prepayment charge of 4% of the outstanding principal balance shall be payable.
- Lock-in Period: No foreclosure is permitted within the first 6 months from the date of disbursement.
- Late Payment Penalty: If any installment is delayed past the due date, a late fee of INR 500 per month plus overdue interest of 2% per month on the overdue EMI amount will be levied.
- Repayment Bounce Charge: In the event of NACH/ECS auto-debit bounce or check return due to insufficient balance, a bounce charge of INR 450 per instance will be charged to the borrower's account.

This agreement constitutes a binding contract between Apex Lending Services and the borrower.
"""
    # Insert text into page
    page.insert_text((54, 54), text, fontsize=10)
    doc.save(output_dir / "apex_personal_loan_agreement.pdf")
    doc.close()
    print("Generated personal loan agreement.")

def generate_bnpl_agreement(output_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    
    text = """
SPLITPAY LATER - CONSUMER CREDIT AGREEMENT
==========================================

Provider: SplitPay Finance Inc.
Merchant Partner: ElectroWorld Store
Borrower: Alice Smith

TRANSACTION DETAILS:
--------------------
- Purchased Item: Smart TV
- Purchase Price: INR 45,000
- Initial Down Payment: INR 15,000
- Funded Loan Amount: INR 30,000
- Interest Rate: 0% Interest (Zero-Interest Promo Loan)
- Total Repayment Term: 3 Months
- Monthly installment amount: INR 10,000
- Number of installments: 3 installments

APPLICABLE CHARGES:
-------------------
- Processing & Platform Fee: A flat upfront charge of INR 499 is payable at the time of order confirmation.
- Monthly Account Fee: INR 99 charged on the active payment card on the 1st of each month during the tenure.
- Convenience Fee: INR 50 per installment for credit card autopayments (waived for UPI auto-debits).

PENALTIES & CONSTRAINTS:
------------------------
- Late Payment Fee: A penalty of INR 250 is charged automatically if the payment is delayed by more than 3 days from the due date.
- Repayment Bounce Fee: If a direct-debit attempt fails, a flat dishonour fee of INR 350 is charged.
- Prepayment: No early closure charges apply. Borrower can pay early without penalty.

No insurance products are bundled with this BNPL agreement. All details are final.
"""
    page.insert_text((54, 54), text, fontsize=10)
    doc.save(output_dir / "splitpay_bnpl_contract.pdf")
    doc.close()
    print("Generated BNPL agreement.")

def generate_credit_card_details(output_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    
    text = """
NOVA TRUST BANK - TITANIUM REWARDS CREDIT CARD TERMS
=====================================================

Issuer: Nova Trust Bank Ltd.
Card Class: Titanium Rewards Card

CREDIT LIMIT & RATES:
--------------------
1. Approved Credit Limit: INR 1,500,000
2. Cash Advance Limit: INR 300,000
3. Retail Purchase Interest Rate: 3.5% per month (42% per annum)
4. Cash Advance Interest Rate: 3.9% per month (46.8% per annum)
5. Interest-Free Grace Period: Up to 50 days (applicable on retail purchases only if the previous statement balance is fully paid).

ANNUAL & TRANSACTION FEES:
---------------------------
- Joining / Annual Fee: INR 2,999 (Charged on the first statement. Waived if annual spend exceeds INR 3,00,000).
- Cash Advance Transaction Fee: 2.5% of the transaction amount or INR 500, whichever is higher.
- Overlimit Charge: 2.5% of the overlimit amount subject to a minimum of INR 600 per occurrence.
- GST: 18% GST applies to all fees, interest rates, and retail charges listed.

DELINQUENCY & PENALTIES:
------------------------
- Minimum Amount Due (MAD): 5% of the total outstanding statement balance or INR 200, whichever is higher.
- Late Payment Fee (based on statement balance):
  * Balance up to INR 1,000: INR 100
  * Balance INR 1,001 to 10,000: INR 500
  * Balance INR 10,001 to 50,000: INR 750
  * Balance above INR 50,000: INR 1,000
- Payment Dishonour Charge (Bounce fee): 2% of the payment amount, minimum INR 450.
"""
    page.insert_text((54, 54), text, fontsize=10)
    doc.save(output_dir / "nova_credit_card_terms.pdf")
    doc.close()
    print("Generated Credit Card agreement.")

def generate_scanned_pdf(output_dir: Path):
    # 1. Create a PDF page with text
    temp_doc = fitz.open()
    page = temp_doc.new_page()
    text = """
SCANNED AGREEMENT EXCERPT: MICRO LENDING
----------------------------------------
Lender: QuickMicro Finance Ltd.
Loan Product: Micro Biz Loan
Amount: INR 50,000
Interest Rate: 18.0% per annum
Tenure: 12 months
EMI: INR 4,584.00

Additional upfront cost details:
- Processing fee is 2% (INR 1,000)
- Documentation fee is INR 500
- Late payment charge is INR 250 flat per month.
- Foreclosure fee is 3% of balance.
"""
    page.insert_text((54, 54), text, fontsize=11)
    
    # 2. Render to PNG bytes
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    width = page.rect.width
    height = page.rect.height
    temp_doc.close()
    
    # 3. Create a new PDF, and embed the PNG as a image to make it look scanned
    scanned_doc = fitz.open()
    scanned_page = scanned_doc.new_page(width=width, height=height)
    
    # Insert image stream
    rect = scanned_page.rect
    scanned_page.insert_image(rect, stream=png_bytes)
    
    scanned_doc.save(output_dir / "scanned_micro_loan_agreement.pdf")
    scanned_doc.close()
    print("Generated scanned micro loan agreement PDF.")

def generate_debt_detox_sample(output_dir: Path):
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    text1 = """DEBT DETOX SAMPLE BANK
======================
PERSONAL LOAN AGREEMENT

This Agreement is made on this 17th day of August, 2026.

LENDER: Debt Detox Bank Ltd.
BORROWER: Jane Doe

SECTION 1: KEY LOAN TERMS
- Loan Amount: Rs. 2,00,000 (Rupees Two Lakhs Only)
- Interest Rate: 18% per annum
- Tenure: 24 months
- Equated Monthly Installment (EMI): Rs. 10,024.00

Please refer to Page 2 of this agreement for detailed clauses regarding processing fees, foreclosure charges, insurance, and other penalty fees.
"""
    page1.insert_text((54, 54), text1, fontsize=10)
    
    # Page 2
    page2 = doc.new_page()
    text2 = """DEBT DETOX SAMPLE BANK - SECTION 2: CHARGES AND PENALTIES
=========================================================

The following charges, fees, and penalties are applicable under this loan agreement:

1. UPFRONT CHARGES:
   - Processing Fee: 2% of sanctioned amount
   - Insurance Premium: Rs. 3,500
   - GST: Applicable on eligible charges at 18%

2. CONTINGENT CHARGES & PENALTIES:
   - Foreclosure Charge: 4% of outstanding principal
   - Late Payment Fee: Rs. 500 per occurrence
   - Check Bounce Fee: Rs. 450 per instance

Both parties have read and agree to all clauses outlined in page 1 and page 2.
"""
    page2.insert_text((54, 54), text2, fontsize=10)
    
    doc.save(output_dir / "debt_detox_sample_loan.pdf")
    doc.close()
    print("Generated Debt Detox sample loan PDF.")

if __name__ == "__main__":
    out_path = Path("d:/DEBT DETOX/sample_documents")
    out_path.mkdir(exist_ok=True)
    generate_personal_loan(out_path)
    generate_bnpl_agreement(out_path)
    generate_credit_card_details(out_path)
    generate_scanned_pdf(out_path)
    generate_debt_detox_sample(out_path)

