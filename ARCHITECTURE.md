# TruthGuard: Architecture & Multi-Agent Verification

## 1. Overview
TruthGuard is an enterprise document question-answering architecture that eliminates the "silent blending" hazard in retrieval-augmented generation. When enterprise handbooks, policies, and board resolutions contradict each other, naive RAG blends chunks together and generates a misleading hybrid answer. 

TruthGuard treats document synthesis as an adversarial courtroom:
- **Retriever & Evidence Prep**: Ingests, filters, and quarantines questionable evidence before it can pollute generation.
- **Synthesizer**: Synthesizes a rigorously cited draft answer requiring strict citation tags.
- **Critic (Adversarial Verifier)**: Audits the evidence for factual contradictions, staleness, ghost references, and unsupported claims.
- **Resolution**: Enforces hierarchical institutional precedence, explicit supersession chains, and temporal ordering—or refuses to guess if the conflict is irreconcilable.

---

## 2. Core Data Models (`modules/schemas.py`)

### `DocumentMetadata`
```python
class DocumentMetadata(BaseModel):
    doc_id: str
    title: str
    version: str = "1.0"
    effective_date: str = "2024-01-01"  # ISO YYYY-MM-DD
    issuer: str = "Unknown"
    authority_level: int = 1  # 3: Board/Executive, 2: Dept Head, 1: Informal
    supersedes: Optional[List[str]] = Field(default_factory=list)
    signature_verified: bool = True
```

### `PassageChunk`
```python
class PassageChunk(BaseModel):
    chunk_id: str
    doc_id: str
    content: str
    surrounding_context: Optional[str] = None
    metadata: DocumentMetadata
```

### `CritiqueResult`
```python
class CritiqueResult(BaseModel):
    has_contradiction: bool = False
    contradiction_details: List[str] = Field(default_factory=list)
    has_staleness: bool = False
    staleness_details: List[str] = Field(default_factory=list)
    has_unsupported_claims: bool = False
    unsupported_claims: List[str] = Field(default_factory=list)
    is_valid: bool = True
```

### `GraphState`
```python
class GraphState(TypedDict):
    question: str
    target_date: Optional[str]
    raw_passages: List[PassageChunk]
    filtered_passages: List[PassageChunk]
    draft_answer: str
    citations: List[Dict[str, Any]]
    critique: Optional[CritiqueResult]
    revision_count: int
    status: str  # "VERIFIED" | "CONFLICT_RESOLVED" | "FLAGGED_FOR_REVIEW"
    final_answer: str
    provenance_details: Dict[str, Any]
```

---

## 3. Defense Mechanisms

### 3.1 Echo Chamber Defense
When an organization retains multiple redundant drafts, copies, or backups of an old policy, naive vector search can retrieve multiple copies of the old clause, causing LLMs to favor it due to repetition. TruthGuard computes normalized content hashes and deduplicates identical text chunks prior to synthesis.

### 3.2 Orphaned Exception Guard
Chunking often severs trailing exception clauses (*"except for probationary staff"*, *"provided that..."*). When chunks are split, TruthGuard's vector store preserves surrounding context windows. The Evidence Prep node detects orphaned qualifier indicators and reattaches adjacent context before passing chunks to the synthesizer.

### 3.3 Quarantine Filter
Unsigned or low-authority documents (`signature_verified == False` or `authority_level < 2`) are separated into a quarantine partition. Their contents are barred from answering questions as valid evidence, but are exposed in the audit trail for investigation.

### 3.4 Precedence Hierarchy Engine
When sources disagree:
1. **Institutional Authority**: Level 3 (Board / C-Suite) strictly overrides Level 2 (Dept Head) and Level 1 (Peer / Slack).
2. **Explicit Supersession**: If Document A designates Document B in `supersedes`, Document A governs.
3. **Ghost Reference Defense**: If Document A claims to supersede a non-existent document ID, the system abstains and flags for review.
4. **Temporal Precedence**: At equal authority, newer `effective_date` overrides older.
5. **Time-Travel Querying**: If a user supplies `target_date`, all documents enacted after that date are omitted from the historical ruling.
