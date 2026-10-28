import re
import json
import logging
from typing import Dict, Any, List, Tuple
from modules.schemas import GraphState, PassageChunk, CritiqueResult
from modules.llm import get_llm
import modules.vector_store as vs

logger = logging.getLogger("truthguard.critic")

CRITIC_SYSTEM_PROMPT = """You are TruthGuard Adversarial Verifier.
Your job is to rigorously audit the synthesized answer against the source document passages.
Check for:
1. Contradictions between sources (e.g. differing numbers, dates, rules).
2. Staleness & Precedence (Higher authority overrides lower authority; explicit 'supersedes' overrides older docs; newer dates override older dates only when authority is equal).
3. Ghost References (documents claiming to supersede IDs that do not exist).
4. Hallucinations / Unsupported claims (any claim in draft not backed by evidence).

Return your response strictly as a JSON object matching this schema:
{
  "has_contradiction": bool,
  "contradiction_details": ["string"],
  "has_staleness": bool,
  "staleness_details": ["string"],
  "has_unsupported_claims": bool,
  "unsupported_claims": ["string"],
  "is_valid": bool
}"""

NON_UNITS = {
    "per", "the", "a", "an", "and", "of", "to", "in", "for", "by", "on", "at", "with",
    "from", "as", "is", "was", "are", "or", "clause", "section", "document", "id",
    "ver", "version", "date", "level", "regular", "calendar", "all", "full", "time"
}

def _canonicalize_unit(u: str) -> str:
    u = u.lower().rstrip("s")
    if u in ["dollar", "$", "usd"]:
        return "dollar"
    if u in ["percent", "%"]:
        return "percent"
    if u in ["day"]:
        return "day"
    if u in ["month"]:
        return "month"
    if u in ["year"]:
        return "year"
    return u

def _extract_numbers_and_units(text: str) -> List[Tuple[str, str]]:
    """Extract patterns like '12 days', '15 days', '10%', '$500'."""
    pattern = r'(\$?\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?'
    raw = re.findall(pattern, text)
    results = []
    for num, unit in raw:
        if num.startswith("$"):
            results.append((num.lstrip("$"), "dollar"))
        elif unit:
            u_clean = unit.lower()
            if u_clean not in NON_UNITS and len(u_clean) > 1:
                results.append((num, _canonicalize_unit(u_clean)))
    return results

def _audit_passages_adversarially(passages: List[PassageChunk], target_date: str = None) -> Tuple[bool, List[str], bool, List[str], bool, List[str]]:
    """
    Algorithmic adversarial verifier that guarantees rigorous checks on:
    - Factual contradictions across different documents
    - Authority hierarchy & precedence
    - Supersedes links & Ghost reference detection
    - Temporal validity / Time-travel
    """
    has_contradiction = False
    contradiction_details = []
    has_staleness = False
    staleness_details = []
    has_ghost = False
    ghost_details = []

    # Group passages by doc_id
    docs_by_id = {}
    for p in passages:
        if p.doc_id not in docs_by_id:
            docs_by_id[p.doc_id] = p.metadata

    # Check for Ghost References:
    all_registered_docs = {d.doc_id for d in vs.vector_store.get_all_documents()}
    all_known_ids = set(docs_by_id.keys()).union(all_registered_docs)

    for doc_id, meta in docs_by_id.items():
        if meta.supersedes:
            for sup_target in meta.supersedes:
                if sup_target and sup_target not in all_known_ids:
                    has_ghost = True
                    detail = (
                        f"Ghost Reference detected in '{meta.title}' (ID: {doc_id}): "
                        f"claims to supersede non-existent document ID '{sup_target}'."
                    )
                    ghost_details.append(detail)
                    contradiction_details.append(detail)

    # Check for Contradictions across documents
    doc_ids = list(docs_by_id.keys())
    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            id1, id2 = doc_ids[i], doc_ids[j]
            meta1, meta2 = docs_by_id[id1], docs_by_id[id2]

            chunks1 = [p.content for p in passages if p.doc_id == id1]
            chunks2 = [p.content for p in passages if p.doc_id == id2]
            text1 = " ".join(chunks1)
            text2 = " ".join(chunks2)

            # Check if text1 and text2 discuss the same subject or have an explicit supersession link
            stop_topics = {"what", "is", "the", "in", "on", "at", "for", "a", "an", "and", "or", "of", "to", "how", "many", "was", "are", "be", "per", "by", "as", "all", "it", "this", "that", "with", "from"}
            topics1 = {w.lower().rstrip("s.,;:!?") for w in text1.split() if w.lower().rstrip("s.,;:!?") not in stop_topics and len(w) > 2}
            topics2 = {w.lower().rstrip("s.,;:!?") for w in text2.split() if w.lower().rstrip("s.,;:!?") not in stop_topics and len(w) > 2}
            is_same_topic = bool(topics1.intersection(topics2)) or (id1 in (meta2.supersedes or [])) or (id2 in (meta1.supersedes or []))

            if not is_same_topic:
                continue

            nums1 = _extract_numbers_and_units(text1)
            nums2 = _extract_numbers_and_units(text2)

            for val1, unit1 in nums1:
                for val2, unit2 in nums2:
                    if unit1.lower() == unit2.lower() and val1 != val2:
                        has_contradiction = True
                        c_msg = (
                            f"Factual conflict on '{unit1}': '{meta1.title}' (Ver {meta1.version}, Date {meta1.effective_date}) "
                            f"states {val1} {unit1}, whereas '{meta2.title}' (Ver {meta2.version}, Date {meta2.effective_date}) "
                            f"states {val2} {unit2}."
                        )
                        contradiction_details.append(c_msg)

                        # Check staleness and precedence
                        # 1. Authority precedence
                        if meta1.authority_level > meta2.authority_level:
                            staleness_details.append(
                                f"'{meta2.title}' (Authority {meta2.authority_level}) is overridden by higher authority '{meta1.title}' (Authority {meta1.authority_level})."
                            )
                            has_staleness = True
                        elif meta2.authority_level > meta1.authority_level:
                            staleness_details.append(
                                f"'{meta1.title}' (Authority {meta1.authority_level}) is overridden by higher authority '{meta2.title}' (Authority {meta2.authority_level})."
                            )
                            has_staleness = True
                        else:
                            # 2. Equal authority: check supersedes or date
                            if meta2.doc_id in (meta1.supersedes or []):
                                staleness_details.append(
                                    f"'{meta1.title}' explicitly supersedes '{meta2.title}'."
                                )
                                has_staleness = True
                            elif meta1.doc_id in (meta2.supersedes or []):
                                staleness_details.append(
                                    f"'{meta2.title}' explicitly supersedes '{meta1.title}'."
                                )
                                has_staleness = True
                            elif meta1.effective_date > meta2.effective_date:
                                staleness_details.append(
                                    f"'{meta2.title}' ({meta2.effective_date}) is older than '{meta1.title}' ({meta1.effective_date}) at equal authority."
                                )
                                has_staleness = True
                            elif meta2.effective_date > meta1.effective_date:
                                staleness_details.append(
                                    f"'{meta1.title}' ({meta1.effective_date}) is older than '{meta2.title}' ({meta2.effective_date}) at equal authority."
                                )
                                has_staleness = True

    # Check time-travel query validity
    if target_date:
        for p in passages:
            if p.metadata.effective_date > target_date:
                has_staleness = True
                staleness_details.append(
                    f"Document '{p.metadata.title}' became effective on {p.metadata.effective_date}, "
                    f"which is after requested target date {target_date}."
                )

    return (
        has_contradiction,
        contradiction_details,
        has_staleness,
        staleness_details,
        has_ghost,
        ghost_details
    )

def critic_node(state: GraphState) -> Dict[str, Any]:
    """
    Adversarially evaluates the draft answer against raw/filtered passages.
    Produces CritiqueResult.
    """
    draft = state.get("draft_answer", "")
    passages = state.get("filtered_passages", [])
    raw_passages = state.get("raw_passages", [])
    target_date = state.get("target_date")
    revision_count = state.get("revision_count", 0)

    # Perform algorithmic verification
    (has_contra, contra_details,
     has_stale, stale_details,
     has_ghost, ghost_details) = _audit_passages_adversarially(passages, target_date)

    # Hallucination check: ensure key claims in draft are supported by passages
    has_unsupported = False
    unsupported_claims = []

    combined_evidence = " ".join([p.content.lower() for p in passages])
    draft_nums = _extract_numbers_and_units(draft)
    for val, unit in draft_nums:
        # Check if this exact number/unit exists in evidence
        if f"{val} {unit}".lower() not in combined_evidence and f"{val}{unit}".lower() not in combined_evidence:
            has_unsupported = True
            unsupported_claims.append(f"Claimed metric '{val} {unit}' is not found in verified evidence.")

    # Check for Ghost Reference
    if has_ghost:
        has_contra = True
        contra_details.extend(ghost_details)

    # Determine validity
    # If there are unsupported claims or if this is the first draft with unaddressed contradictions/staleness
    is_valid = True
    if has_unsupported:
        is_valid = False
    elif (has_contra or has_stale) and revision_count == 0:
        # Require one revision cycle so synthesizer addresses the conflict explicitly
        is_valid = False

    critique = CritiqueResult(
        has_contradiction=has_contra,
        contradiction_details=list(set(contra_details)),
        has_staleness=has_stale,
        staleness_details=list(set(stale_details)),
        has_unsupported_claims=has_unsupported,
        unsupported_claims=unsupported_claims,
        is_valid=is_valid
    )

    provenance = dict(state.get("provenance_details", {}) or {})
    provenance["critique"] = critique.model_dump()
    provenance["has_ghost_reference"] = has_ghost

    return {
        "critique": critique,
        "provenance_details": provenance
    }
