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

## 👥 Project Team

- **Dharshini K** (2312012)
- **Dhivya Varshini D** (2312013)
- **Gnana Jeyanthi M** (2312016)
- **Swathi R** (2312041)
- **Anitha M** (2312066)

---

## 🧪 Automated Test Suite & Benchmark Evaluation

### 1. Quantitative Benchmark Script
Run the standalone PoC evaluation benchmark to verify all stated accuracy and safety thresholds:
```bash
python evaluate_metrics.py
```
Output:
```text
+-----------------------+----------+---------+
| Metric                | Target   | Actual  |
+-----------------------+----------+---------+
| Conflict Recall       | >= 90%   | 100%    |
| Stale Answer Rate     | < 5%     | 0%      |
| Unsupported Claims    | < 5%     | 0%      |
| Silent Blends         | 0        | 0       |
+-----------------------+----------+---------+
```

### 2. Full Pytest Suite
Run the full test suite covering all 8 specified hidden test cases:
```bash
pytest tests -v
```

### 8 Hidden Test Cases Implemented:
1. **Time-travel query**: Asked about a past date? Answers from version valid then, not newest (`tests/test_truthguard.py::test_time_travel_explicit_date`).
2. **Newer but weaker**: Recent FAQ never overrides older board-approved policy. Authority beats recency (`test_newer_but_weaker`).
3. **Partial supersession**: An amendment modifying one clause leaves the rest of the document intact.
4. **Echo chamber**: Duplicate copies of older policies do not outvote an amendment. Deduplicated by Evidence Prep.
5. **Ghost reference**: References non-existent document ID in supersedes? Flagged for review; system refuses to guess (`test_ghost_reference`).
6. **Spoofed amendment**: Unsigned file with unverified issuer quarantined (`test_unverified_spoof`).
7. **Orphaned exception**: Adjacent qualification clauses (*"except contract staff"*) automatically retrieved.
8. **Ripple effect**: Scans and surfaces all downstream policies and systems (Payroll, HRMS, Handbooks) requiring updates.

---

## 📡 Backend API Endpoints

- `POST /api/upload`: Multipart file upload with authority metadata.
- `POST /api/query`: Runs the full LangGraph pipeline.
- `GET /api/corpus_health`: Proactive corpus health scanner detecting latent conflicts across all registered policies before users query.
- `GET /api/documents`: Returns list of all ingested documents in the vector store.
- `DELETE /api/documents`: Clears the vector store.
- `POST /api/seed_samples`: One-click endpoint to seed sample test policies.
- `GET /api/health`: Health status and provider configuration.
