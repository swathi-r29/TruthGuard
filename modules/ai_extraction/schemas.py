from typing import Optional, List, Union
from pydantic import BaseModel, Field

# Explicit Term Extraction Status Constants
STATUS_VERIFIED = "VERIFIED"
STATUS_MENTIONED_UNSPECIFIED = "MENTIONED-BUT-NOT-SPECIFIED"
STATUS_NOT_FOUND = "NOT FOUND"
STATUS_NOT_APPLICABLE = "NOT APPLICABLE"

class ExtractedField(BaseModel):
    value: Optional[Union[float, str]] = Field(
        default=None, 
        description="The extracted value, numeric if applicable, or string. Must be null if not found."
    )
    unit: Optional[str] = Field(
        default=None, 
        description="The unit of the value, e.g., 'percent', 'INR', 'months', 'days', or null if not applicable."
    )
    basis: Optional[str] = Field(
        default=None, 
        description="The calculation basis, e.g., 'principal', 'outstanding_principal', 'flat', 'monthly', 'annual', or null if not applicable."
    )
    page: Optional[int] = Field(
        default=None, 
        description="The 1-based page number where this information is found in the document."
    )
    evidence: Optional[str] = Field(
        default=None, 
        description="The exact textual snippet/sentence from the document that supports this extraction."
    )
    confidence: Optional[str] = Field(
        default=None, 
        description="The confidence score of this extraction: 'high', 'medium', or 'low'."
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Additional surrounding context or verbatim terms if different from evidence."
    )
    original_term: Optional[str] = Field(
        default=None,
        description="The exact phrase/label as written in the original document."
    )
    normalized_category: Optional[str] = Field(
        default=None,
        description="The standardized category key (e.g. loan_amount, processing_fee)."
    )
    condition: Optional[str] = Field(
        default=None,
        description="Any specific condition or rule associated with this term."
    )
    frequency: Optional[str] = Field(
        default=None,
        description="Charge or payment frequency (e.g. one_time, monthly, annual)."
    )
    status: str = Field(
        default=STATUS_NOT_FOUND,
        description="Extraction status: VERIFIED, MENTIONED-BUT-NOT-SPECIFIED, NOT FOUND, NOT APPLICABLE."
    )

class OtherChargeField(BaseModel):
    name: str = Field(description="The name of the charge as written in the document.")
    value: Optional[Union[float, str]] = Field(default=None, description="The charge value.")
    unit: Optional[str] = Field(default=None, description="The unit of the charge (e.g. percent, INR).")
    basis: Optional[str] = Field(default=None, description="The calculation basis.")
    page: Optional[int] = Field(default=None, description="The page number.")
    evidence: Optional[str] = Field(default=None, description="Verbatim clause.")
    confidence: Optional[str] = Field(default=None, description="Confidence rating.")
    original_term: Optional[str] = Field(default=None, description="Original phrasing.")
    status: str = Field(default=STATUS_VERIFIED, description="Status.")

class LoanExtractionResult(BaseModel):
    document_type: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Type of debt agreement, e.g., 'personal_loan', 'bnpl', 'credit_card_agreement', 'unknown'."
    )
    lender_name: ExtractedField = Field(default_factory=ExtractedField, description="Name of the lending institution/entity.")
    borrower_name: ExtractedField = Field(default_factory=ExtractedField, description="Name of the borrower.")
    loan_amount: ExtractedField = Field(default_factory=ExtractedField, description="The principal loan amount borrowed.")
    outstanding_principal: ExtractedField = Field(default_factory=ExtractedField, description="The current outstanding loan balance/principal if specified in the document.")
    disbursed_amount: ExtractedField = Field(default_factory=ExtractedField, description="The net amount received/disbursed to borrower's account.")
    interest_rate: ExtractedField = Field(default_factory=ExtractedField, description="The nominal interest rate.")
    interest_type: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Type of interest calculation, e.g., 'reducing_balance', 'flat_rate', 'zero_interest'."
    )
    rate_basis: ExtractedField = Field(
        default_factory=ExtractedField, 
        description="Whether interest rate is annual or monthly: 'annual', 'monthly'."
    )
    tenure: ExtractedField = Field(default_factory=ExtractedField, description="The duration of the loan (e.g., 24 months, 3 years).")
    emi: ExtractedField = Field(default_factory=ExtractedField, description="Equated Monthly Installment amount.")
    number_of_installments: ExtractedField = Field(default_factory=ExtractedField, description="The total number of schedule payments.")
    processing_fee: ExtractedField = Field(default_factory=ExtractedField, description="Processing or administrative fee (absolute value if known).")
    processing_fee_percentage: ExtractedField = Field(default_factory=ExtractedField, description="Processing fee expressed as a percentage of principal.")
    insurance: ExtractedField = Field(default_factory=ExtractedField, description="Mandatory or optional credit shield insurance fee.")
    documentation_fee: ExtractedField = Field(default_factory=ExtractedField, description="Charges for documentation or stamp duty.")
    gst_tax_references: ExtractedField = Field(default_factory=ExtractedField, description="Clauses mentioning tax or GST applicable on fees.")
    foreclosure_charge: ExtractedField = Field(default_factory=ExtractedField, description="Charges/fees for early repayment or foreclosure of the entire loan.")
    prepayment_charge: ExtractedField = Field(default_factory=ExtractedField, description="Charges/fees for part-prepayment.")
    late_payment_fee: ExtractedField = Field(default_factory=ExtractedField, description="Late payment charge or delay penalty.")
    bounce_charge: ExtractedField = Field(default_factory=ExtractedField, description="Charges for check/payment bounce or ECS bounce.")
    default_penalty: ExtractedField = Field(default_factory=ExtractedField, description="Extra penalty interest rate or default interest terms.")
    annual_fee: ExtractedField = Field(default_factory=ExtractedField, description="Annual maintenance or card renewal fee.")
    renewal_fee: ExtractedField = Field(default_factory=ExtractedField, description="Renewal or extension fee.")
    lock_in_period: ExtractedField = Field(default_factory=ExtractedField, description="The period during which the loan cannot be prepaid.")
    prepayment_conditions: ExtractedField = Field(default_factory=ExtractedField, description="Any other rules or requirements for prepayment.")
    other_charges: List[OtherChargeField] = Field(default_factory=list, description="Any other additional fees/charges listed in the agreement.")
