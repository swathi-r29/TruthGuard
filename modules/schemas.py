from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    doc_id: str
    title: str
    version: str = "1.0"
    effective_date: str = "2024-01-01"  # ISO YYYY-MM-DD
    issuer: str = "Unknown"
    authority_level: int = 1  # 3 = Board/Executive, 2 = Department Head, 1 = Informal/Unverified
    supersedes: Optional[List[str]] = Field(default_factory=list)
    signature_verified: bool = True

class PassageChunk(BaseModel):
    chunk_id: str
    doc_id: str
    content: str
    surrounding_context: Optional[str] = None
    metadata: DocumentMetadata

class CritiqueResult(BaseModel):
    has_contradiction: bool = False
    contradiction_details: List[str] = Field(default_factory=list)
    has_staleness: bool = False
    staleness_details: List[str] = Field(default_factory=list)
    has_unsupported_claims: bool = False
    unsupported_claims: List[str] = Field(default_factory=list)
    is_valid: bool = True

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

# API Schemas
class QueryRequest(BaseModel):
    query: str
    target_date: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    status: str
    final_answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    critique: Optional[CritiqueResult] = None
    revision_count: int = 0
    provenance_details: Dict[str, Any] = Field(default_factory=dict)
    draft_answer: Optional[str] = None

