# Debt Detox — AI That Reveals What Your Loan Is Really Costing You

Debt Detox is a financial literacy and analysis application built for borrowers. It analyzes loan agreements, credit card statements, and Buy Now Pay Later (BNPL) contracts to reveal upfront, recurring, and conditional costs that might otherwise go unnoticed.

The project processes documents locally using **PyMuPDF**, performs OCR on scanned materials via **Tesseract**, extracts terms using **Ollama** (local LLM), and performs precise, deterministic financial calculations in **Python** (preventing LLM math errors).

---

## Key Features

1. **Deterministic Calculations**: Python computes EMI, interest, taxes, and net disbursements. No reliance on LLM arithmetic.
2. **Traceable Findings**: Every extracted term includes its exact page number and supporting text snippet as evidence.
3. **Transparency Score**: A metric (0-100) scoring a contract's consumer-friendliness based on fee count, prepayment clauses, and penalty rates.
4. **Interactive Payoff Simulator**: Models the financial impact of extra monthly or one-time principal prepayments.
5. **Multi-Debt Strategy Tool**: Ranks debts by priority using Avalanche (highest interest first) or Snowball (smallest balance first).

---

## Installation & Setup

### 1. Prerequisites (Windows)

* **Python 3.11+**
* **Tesseract OCR**:
  * Download the installer from: [UB Mannheim Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  * Run the installer.
  * *Option A*: Add the Tesseract directory (e.g. `C:\Program Files\Tesseract-OCR`) to your system environment variables `PATH`.
  * *Option B*: Configure it in `.env`:
    ```env
    TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
    ```
* **Ollama (for Local LLM)**:
  * Download and install from [Ollama.com](https://ollama.com).
  * Launch Ollama.
  * Pull a model for extraction (we recommend `gemma2:2b` or `llama3` for standard setups):
    ```cmd
    ollama pull gemma2:2b
    ```

### 2. Project Installation

1. Clone or copy the codebase to a directory (e.g., `d:\DEBT DETOX`).
2. Create a virtual environment and activate it:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

### 3. Local Environment

Copy `.env.example` to `.env` and verify the settings:
```cmd
copy .env.example .env
```
Ensure your `OLLAMA_MODEL` in `.env` matches the model you pulled in Ollama (e.g., `gemma2:2b`).

---

## Running the Application

Activate your virtual environment and launch Streamlit:
```cmd
streamlit run app.py
```

---

## Running Tests

Verify the calculations and schemas:
```cmd
python -m unittest discover tests
```
