# ARCHITECTURE — Debt Detox

Debt Detox is a financial education tool designed to help consumers understand the real costs of their debt (loans, credit cards, BNPL) by combining AI-driven clause understanding with deterministic Python calculations.

## 1. Modular Structure

The application is structured into the following modules to ensure separation of concerns:

```
DebtDetox/
│
├── app.py                     # Main Streamlit application
├── config.py                  # Environment and application configuration
├── requirements.txt           # Python package dependencies
├── .env.example               # Example environment variables template
├── README.md                  # Project overview and run instructions
├── ARCHITECTURE.md            # System architecture and data flow
├── PROGRESS.md                # Project development progress tracker
├── .gitignore                 # Files to exclude from version control
│
├── modules/
│   ├── document_processor/    # Module 1: Document Processing (PDF/Image text extraction)
│   │   ├── __init__.py
│   │   ├── pdf_processor.py   # Extracts text from standard PDFs using PyMuPDF
│   │   ├── ocr_processor.py   # Runs OCR on images/scanned PDFs using pytesseract
│   │   └── text_cleaner.py    # Sanitizes and formats extracted text
│   │
│   ├── ai_extraction/         # Module 2: AI Financial Extraction (LLM processing)
│   │   ├── __init__.py
│   │   ├── client.py          # Unified client abstraction for LLM provider (Ollama)
│   │   ├── extractor.py       # Orchestrates chunking, prompt execution, and validation
│   │   ├── schemas.py         # Pydantic schemas for structured extraction
│   │   └── prompts.py         # System and user prompts for extraction
│   │
│   ├── charge_detection/      # Module 3: Charge Detection and Classification
│   │   ├── __init__.py
│   │   ├── detector.py        # Combines AI extraction and regex keyword matching
│   │   ├── classifier.py      # Classifies charges (BASE_COST, PENALTY, etc.)
│   │   └── rules.py           # Keyword patterns, synonyms, and classification rules
│   │
│   ├── financial_engine/      # Module 4: Financial Calculation Engine (Deterministic)
│   │   ├── __init__.py
│   │   ├── emi.py             # Reducing-balance EMI math (handles zero-interest)
│   │   ├── interest.py        # Total interest calculations
│   │   ├── fees.py            # Fixed and percentage-based fee calculators
│   │   ├── taxes.py           # Tax/GST calculations based on rates/basis
│   │   └── real_cost.py       # Calculates net disbursement and total cost of debt
│   │
│   ├── analyzer/              # Module 5 & 6: Real Cost & Transparency Score
│   │   ├── __init__.py
│   │   ├── cost_analyzer.py   # Compiles effective cost metrics and breaks down costs
│   │   └── transparency_score.py # Calculates the Debt Detox Transparency Score (0-100)
│   │
│   ├── explanation/           # Module 7: Plain Language Explanation
│   │   ├── __init__.py
│   │   └── explainer.py       # Rewrites complex clauses and generates concrete math examples
│   │
│   ├── debt_strategy/         # Module 8 & 9: Strategic Comparison & Payoff Simulator
│   │   ├── __init__.py
│   │   ├── comparison.py      # Standardizes metrics across different debt types
│   │   ├── ranking.py         # Debt prioritization engine (Snowball vs. Avalanche)
│   │   └── payoff_simulator.py# Simulates extra monthly or one-time payments and computes savings
│   │
│   └── reporting/             # Module 10: Report Generation
│       ├── __init__.py
│       └── report_generator.py# Generates text/markdown export reports (safe format)
│
├── ui/                        # Streamlit Pages & Layouts
│   ├── dashboard.py           # Dashboard / Loan Truth view
│   ├── upload.py              # File uploader and processing status
│   ├── charges.py             # Charges categorization and visualization page
│   ├── evidence.py            # Evidence trace and verification page
│   ├── comparison.py          # Multi-debt comparison and strategy page
│   ├── simulator.py           # Interactive payoff simulator page
│   └── report.py              # Downloadable summary page
│
├── tests/                     # Test Suites (Unit & Integration)
│   ├── test_document_processor.py
│   ├── test_extraction.py
│   ├── test_charges.py
│   ├── test_financial_engine.py
│   ├── test_strategy.py
│   └── test_end_to_end.py
│
└── sample_documents/          # Fictional synthetic documents for testing/demo
```

---

## 2. Core Data Flow

Below is the end-to-end data flow showing how an uploaded document transitions from raw text into structured findings, calculations, and recommendations:

```
[Document Upload (PDF/Image)]
       │
       ▼
[document_processor] (PyMuPDF / OCR) ──► Raw Pages (page_number, text)
       │
       ▼
[ai_extraction] (Ollama / LLM Abstraction) ──► Structured Entities JSON (Schema Validated)
       │
       ▼
[charge_detection] (Rules + Synonyms) ──► Standardized & Classified Charges
       │
       ▼
[financial_engine] (Deterministic Python) ──► EMI, Net Received, Total Cost, Effective Cost
       │
       ▼
[analyzer & explanation] ──► Transparency Score, Plain English Explanations & Examples
       │
       ▼
[UI / Strategy / Reporting] ──► Visual Dashboard, Strategy Recommendation, Interactive Simulator, Downloadable Report
```

---

## 3. Module Interfaces

### Document Processor
```python
def process_document(file_path_or_bytes: bytes, file_name: str) -> list[dict]:
    # Returns list of dicts: [{"page_number": int, "text": str}]
```

### AI Extraction
```python
def extract_terms(pages: list[dict]) -> dict:
    # Sends pages to LLM in chunks if necessary.
    # Returns verified JSON according to extraction schema.
```

### Charge Detection
```python
def detect_charges(extracted_terms: dict, pages: list[dict]) -> list[dict]:
    # Runs rules/keywords against text and standardizes LLM findings.
    # Returns list of standardized charges with classification category.
```

### Financial Engine
```python
def calculate_loan_metrics(principal: float, rate_annual: float, tenure_months: int, charges: list[dict]) -> dict:
    # Returns: emi, total_repayment, total_interest, net_disbursement, total_scheduled_cost, etc.
```

---

## 4. Key Dependencies
* **Streamlit**: Web dashboard UI framework.
* **PyMuPDF (fitz)**: Rapid PDF page loading and text extraction.
* **pytesseract & Pillow**: OCR engine for image and scanned PDF support. (Requires local installation of Tesseract OCR on Windows).
* **Pydantic**: JSON structure validation for LLM responses.
* **Pandas & Plotly**: Dynamic graphing and comparison matrices.
* **python-dotenv**: Environment file configurations.

---

## 5. Key Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **LLM Hallucinations** | Strict instruction to return `null` if not found. Validation schema verifies types. Every value must include its supporting textual snippet and page number. |
| **Scanned/Ocr Text Quality** | Clean text using normalized spacing. Ensure Tesseract defaults to robust configuration. Warn user if OCR confidence is low. |
| **Ollama Connectivity / Performance** | Configuration parameters for URL/model. Timeout handling. Beautiful custom UI error screen with step-by-step connection guide if Ollama is offline. |
| **Large Documents** | Page-by-page processing and chunk consolidation rather than passing large text arrays into single LLM prompts. |

---

## 6. Testing Strategy
* **Unit Tests**: Test core components under `tests/` using `unittest` or `pytest`. Test financial calculations with precise asserts (interest, EMI, net disbursement). Test keyword-matching logic.
* **Integration Tests**: Mock the LLM client or run against a real local Ollama instance to test end-to-end extraction and validation flow.
* **Manual Verification**: Run Streamlit and navigate the pages using sample documents. Verify dynamic updates in payoff simulator and ranking displays.
