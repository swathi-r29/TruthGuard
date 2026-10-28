import re
import hashlib
from typing import Dict, Any, List
from modules.schemas import GraphState, PassageChunk
import modules.vector_store as vs

def _normalize_text_for_dedup(text: str) -> str:
    """Normalize text by stripping whitespace and punctuation for echo chamber defense."""
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text.lower())).strip()

def retriever_node(state: GraphState) -> Dict[str, Any]:
    """
    Retrieves candidate passages from ChromaDB based on the user question.
    """
    question = state.get("question", "")
    target_date = state.get("target_date")

    # Semantic search in ChromaDB
    passages = vs.vector_store.search_passages(query=question, n_results=20)

    # Initialize provenance details if empty
    provenance = state.get("provenance_details", {}) or {}
    provenance["retrieved_count"] = len(passages)

    return {
        "raw_passages": passages,
        "provenance_details": provenance
    }

def evidence_prep_node(state: GraphState) -> Dict[str, Any]:
    """
    Applies Evidence Preparation defenses:
    1. Echo Chamber Defense: Deduplicate identical chunks so repeated copies don't outvote a single amendment.
    2. Orphaned Exception Guard: Automatically append adjacent chunks so qualifying clauses are not cut off.
    3. Quarantine Filter: Quarantine chunks whose issuer authority is unverified (signature_verified == False or authority_level < 2).
    """
    raw_passages = state.get("raw_passages", [])
    target_date = state.get("target_date")
    provenance = dict(state.get("provenance_details", {}) or {})

    seen_hashes = set()
    deduped_passages: List[PassageChunk] = []
    echo_chamber_dropped = []

    # 1. Echo Chamber Defense
    for p in raw_passages:
        norm = _normalize_text_for_dedup(p.content)
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        if h in seen_hashes:
            echo_chamber_dropped.append({
                "chunk_id": p.chunk_id,
                "doc_id": p.doc_id,
                "title": p.metadata.title,
                "reason": "Duplicate content detected (Echo Chamber Defense)"
            })
            continue
        seen_hashes.add(h)
        deduped_passages.append(p)

    # 2. Orphaned Exception Guard
    # If chunk has an adjacent context with qualifying clauses ('except', 'unless', 'provided that', 'however'),
    # append surrounding context to ensure clauses are not severed.
    exception_indicators = ["except", "unless", "provided however", "provided that", "excluding", "not applicable to"]
    guarded_passages: List[PassageChunk] = []

    for p in deduped_passages:
        content = p.content
        if p.surrounding_context and p.surrounding_context != p.content:
            lower_ctx = p.surrounding_context.lower()
            if any(ind in lower_ctx for ind in exception_indicators):
                # Ensure the full qualifying sentence or context is included
                if not any(ind in content.lower() for ind in exception_indicators):
                    # Attach surrounding context to preserve exception
                    content = p.surrounding_context
        
        guarded_passages.append(
            PassageChunk(
                chunk_id=p.chunk_id,
                doc_id=p.doc_id,
                content=content,
                surrounding_context=p.surrounding_context,
                metadata=p.metadata
            )
        )

    # 3. Quarantine Filter
    quarantined = []
    filtered: List[PassageChunk] = []

    for p in guarded_passages:
        meta = p.metadata
        # Check if unverified or authority_level < 2
        if (not meta.signature_verified) or (meta.authority_level < 2):
            reason = []
            if not meta.signature_verified:
                reason.append("Unverified signature / spoof risk")
            if meta.authority_level < 2:
                reason.append(f"Insufficient authority level ({meta.authority_level} < 2)")
            
            quarantined.append({
                "chunk_id": p.chunk_id,
                "doc_id": p.doc_id,
                "title": meta.title,
                "issuer": meta.issuer,
                "authority_level": meta.authority_level,
                "signature_verified": meta.signature_verified,
                "reasons": reason,
                "snippet": p.content[:150]
            })
        else:
            filtered.append(p)

    provenance["echo_chamber_dropped"] = echo_chamber_dropped
    provenance["quarantined_chunks"] = quarantined
    provenance["active_evidence_count"] = len(filtered)

    return {
        "filtered_passages": filtered,
        "provenance_details": provenance
    }
