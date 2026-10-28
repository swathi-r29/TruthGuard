# TruthGuard: Adversarial Verification for Multi-Agent Document Q&A

**TruthGuard** is a multi-agent system designed to answer complex organizational questions over conflicting corporate documents (policies, amendments, circulars, handbooks, FAQs) **without silently blending conflicting data or hallucinating reconciliation**.

TruthGuard leverages **LangGraph** for multi-agent state graph orchestration, **ChromaDB** for local vector storage, and allows seamless switching between **Google Gemini Flash** (`ChatGoogleGenerativeAI`) and **Groq** (`ChatGroq`) via `.env`, with built-in deterministic verification fallbacks.

---

## 🛡️ Core Defensive Capabilities

1. **Echo Chamber Defense**: Deduplicates repeated chunks so duplicate copies of an older document do not outvote a single authoritative amendment.
2. **Orphaned Exception Guard**: Automatically stitches surrounding context to prevent critical qualifying clauses (e.g., *"except for contract staff"*, *"provided however"*) from being truncated.
3. **Quarantine Filter**: Automatically quarantines unverified or low-authority inputs (`signature_verified == False` or `authority_level < 2`) to protect against policy spoofing.
4. **Adversarial Critic Verifier**: Actively checks drafts for factual contradictions, staleness, ghost references (pointing to non-existent document IDs), and unsupported claims.
5. **Governing Resolution Engine**:
   - **Authority Precedence**: Higher authority level strictly overrides lower authority (Board = 3 > Department Head = 2 > Informal/FAQ = 1).
   - **Explicit Supersession**: Enforces designated replacement chains (`supersedes`).
   - **Temporal Order**: At equal authority, newer documents supersede older documents.
   - **Ghost Reference & Refusal to Guess**: Flags irreconcilable positions for human review instead of guessing.
   - **Time-Travel Querying**: Historical queries (e.g. `target_date="2023-06-01"`) snapshot policies valid at that exact historical moment.

---

## 🏗️ Multi-Agent Architecture

```
[ User Query / Historical Date ]
              │
              ▼
      ┌───────────────┐
      │ RetrieverNode │  <--- ChromaDB Vector Store (Chunks & Metadata)
      └───────┬───────┘
              │
              ▼
     ┌─────────────────┐
     │ EvidencePrepNode│  <--- Echo Chamber Defense + Orphaned Exception Guard + Quarantine Filter
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ SynthesizerNode │ <--- Drafts cited answer: [Doc: {title}, Ver: {v}, Date: {d}]
     └────────┬────────┘
              │
              ▼
       ┌──────────────┐
       │  CriticNode  │  <--- Adversarial Verification (Contradictions, Staleness, Hallucinations)
       └──────┬───────┘
              │
         [ Valid? ] ─── (No & Revisions < 2) ───> [ Increment Revision ] ──> SynthesizerNode
              │ (Yes or Revisions == 2)
              ▼
     ┌─────────────────┐
     │ ResolutionNode  │  <--- VERIFIED | CONFLICT_RESOLVED | FLAGGED_FOR_REVIEW
     └────────┬────────┘
              │
              ▼
            [ END ]
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```env
# LLM Provider: 'gemini' or 'groq'
LLM_PROVIDER=gemini

# Google Gemini Flash configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Groq configuration (Fast Llama-3 inference)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Backend Setup
Install Python dependencies:
```bash
pip install -r requirements.txt
```

Seed sample test corpus into ChromaDB:
```bash
python seed_samples.py
```

Run FastAPI Backend:
```bash
python app.py
```
*API runs at `http://localhost:8000` (docs available at `http://localhost:8000/docs`).*

### 4. Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs at `http://localhost:5173`.*

---

## 🧪 Automated Test Suite

Run the full automated test suite covering all specified adversarial scenarios:

```bash
pytest tests/test_truthguard.py -v
```

### Test Scenarios Covered:
1. `test_standard_conflict`: Policy 2022 (12 days) vs Board Amendment 2025 (15 days) -> Resolves to 15 days with governing precedence justification.
2. `test_newer_but_weaker`: 2024 Board Policy ($75) vs 2025 Slack FAQ ($100) -> Board Policy governs; weaker authority quarantined.
3. `test_ghost_reference`: Document claiming to supersede a non-existent document ID -> Abstains and flags as `FLAGGED_FOR_REVIEW`.
4. `test_unverified_spoof`: Unsigned file attempting to change policy -> Quarantined by Evidence Prep.
5. `test_time_travel`: Query specifying historical date (e.g. 2023) -> Returns 2022 policy value instead of 2025 value.

Also run document processor unit tests:
```bash
pytest tests/test_document_processor.py -v
```

---

## 📡 Backend API Endpoints

- `POST /api/upload`: Multipart file upload with authority metadata (`title`, `version`, `effective_date`, `issuer`, `authority_level`, `supersedes`, `signature_verified`).
- `POST /api/query`: Runs the full LangGraph pipeline given `{"query": str, "target_date": Optional[str]}`. Returns `status`, `final_answer`, `citations`, `critique`, `revision_count`, and `provenance_details`.
- `GET /api/documents`: Returns list of all ingested documents in the vector store with authority levels and versions.
- `DELETE /api/documents`: Clears the vector store.
- `POST /api/seed_samples`: One-click endpoint to seed sample test policies.
- `GET /api/health`: Health status and provider configuration.
