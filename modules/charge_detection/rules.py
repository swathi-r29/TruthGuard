import re

# Mapping of canonical keys to regular expression patterns for synonym matching
KEYWORDS_MAPPING = {
    "processing_fee": [
        r"processing\s+(?:fee|charge|cost)", 
        r"service\s+(?:fee|charge)", 
        r"admin(?:istrative)?\s+(?:fee|charge|cost)",
        r"upfront\s+(?:fee|charge)"
    ],
    "documentation_fee": [
        r"documentation\s+(?:fee|charge)", 
        r"stamp\s+duty", 
        r"agreement\s+(?:fee|charge)",
        r"legal\s+charges"
    ],
    "insurance": [
        r"insurance", 
        r"credit\s+shield", 
        r"protection\s+plan",
        r"group\s+insurance"
    ],
    "foreclosure_charge": [
        r"foreclosure\s+(?:charge|fee)", 
        r"early\s+(?:closure|termination|repayment|settlement)", 
        r"pre-closure\s+(?:charge|fee)",
        r"preclosure"
    ],
    "prepayment_charge": [
        r"prepayment\s+(?:charge|fee)", 
        r"part\s+prepayment\s+(?:charge|fee)"
    ],
    "late_payment_fee": [
        r"late\s+(?:payment|fee|charge)", 
        r"delay\s+(?:charge|penalty|fee)", 
        r"overdue\s+(?:charge|payment|fee)",
        r"delinquency\s+fee"
    ],
    "bounce_charge": [
        r"bounce\s+(?:charge|fee)", 
        r"returned\s+payment", 
        r"cheque\s+bounce", 
        r"ecs\s+bounce",
        r"dishonour\s+charge",
        r"\bbounce\b"
    ],
    "default_penalty": [
        r"default\s+(?:interest|penalty|charge)", 
        r"penal\s+interest",
        r"penalty\s+rate"
    ],
    "annual_fee": [
        r"annual\s+(?:fee|charge)", 
        r"maintenance\s+fee",
        r"yearly\s+fee"
    ],
    "renewal_fee": [
        r"renewal\s+(?:fee|charge)",
        r"extension\s+fee"
    ],
    "gst_tax_references": [
        r"gst", 
        r"service\s+tax", 
        r"applicable\s+taxes",
        r"value\s+added\s+tax",
        r"cgst",
        r"sgst",
        r"igst"
    ]
}

# Categories according to product principles
CLASSIFICATION_MAPPING = {
    # Base loan terms
    "loan_amount": "BASE_COST",
    "interest_rate": "BASE_COST",
    "interest_type": "BASE_COST",
    "tenure": "BASE_COST",
    "emi": "BASE_COST",
    "number_of_installments": "BASE_COST",
    
    # Additional upfront charges
    "processing_fee": "ADDITIONAL_COST",
    "processing_fee_percentage": "ADDITIONAL_COST",
    "documentation_fee": "ADDITIONAL_COST",
    
    # Taxes
    "gst_tax_references": "TAX",
    
    # Conditional costs
    "foreclosure_charge": "CONDITIONAL_COST",
    "prepayment_charge": "CONDITIONAL_COST",
    "lock_in_period": "CONDITIONAL_COST",
    "prepayment_conditions": "CONDITIONAL_COST",
    
    # Penalties
    "late_payment_fee": "PENALTY",
    "bounce_charge": "PENALTY",
    "default_penalty": "PENALTY",
    
    # Optional costs
    "insurance": "OPTIONAL_COST",
    
    # Recurring card fees
    "annual_fee": "ADDITIONAL_COST",
    "renewal_fee": "ADDITIONAL_COST"
}
