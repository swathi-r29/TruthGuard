import re
import logging
from typing import Dict, Any, List, Optional
from modules.schemas import GraphState, PassageChunk, DocumentMetadata, CritiqueResult

logger = logging.getLogger("truthguard.resolution")

def _clean_markdown_headings(text: str) -> str:
    """Strips leading markdown heading symbols (#, ##, ###) for clean presentation."""
    cleaned_lines = []
    for line in text.splitlines():
        cleaned_line = re.sub(r'^\s*#{1,6}\s*', '', line)
        if cleaned_line.strip():
            cleaned_lines.append(cleaned_line.strip())
    return " ".join(cleaned_lines)

class SelectionResult:
    def __init__(
        self,
        governing: Optional[DocumentMetadata],
        competitors: List[DocumentMetadata],
        reason: str,
        is_reconciled: bool
    ):
        self.governing = governing
        self.competitors = competitors
        self.reason = reason
        self.is_reconciled = is_reconciled

def _determine_governing_doc(passages: List[PassageChunk], target_date: Optional[str] = None) -> SelectionResult:
    # Deduplicate documents from passages
    docs: Dict[str, DocumentMetadata] = {}
    for p in passages:
        if p.doc_id not in docs:
            docs[p.doc_id] = p.metadata

    if not docs:
        return SelectionResult(None, [], "No documents found", False)

    # If target_date is supplied (time-travel query), filter documents
    candidates = list(docs.values())
    if target_date:
        valid_candidates = [d for d in candidates if d.effective_date <= target_date]
        if valid_candidates:
            candidates = valid_candidates
        else:
            return SelectionResult(
                None,
                candidates,
                f"No documents were effective on or prior to target date {target_date}.",
                False
            )

    if len(candidates) == 1:
        return SelectionResult(candidates[0], [], "Single governing document.", True)

    # Sort candidates by:
    # 1. Authority level (descending)
    # 2. Date (descending)
    candidates.sort(key=lambda d: (d.authority_level, d.effective_date), reverse=True)

    top_doc = candidates[0]
    second_doc = candidates[1]

    # Precedence Rule 1: Authority Level
    if top_doc.authority_level > second_doc.authority_level:
        reason = (
            f"'{top_doc.title}' (Authority Level {top_doc.authority_level}, Issuer: {top_doc.issuer}) "
            f"strictly supersedes '{second_doc.title}' (Authority Level {second_doc.authority_level}, Issuer: {second_doc.issuer}) "
            f"via superior institutional authority."
        )
        return SelectionResult(top_doc, candidates[1:], reason, True)

    # Precedence Rule 2: Explicit Supersession
    if second_doc.doc_id in (top_doc.supersedes or []):
        reason = (
            f"'{top_doc.title}' (v{top_doc.version}, Effective {top_doc.effective_date}) "
            f"explicitly supersedes '{second_doc.title}' (v{second_doc.version}) via designated document amendment."
        )
        return SelectionResult(top_doc, candidates[1:], reason, True)

    # Precedence Rule 3: Date Precedence when authority is equal
    if top_doc.effective_date > second_doc.effective_date:
        reason = (
            f"'{top_doc.title}' (v{top_doc.version}, Effective {top_doc.effective_date}) "
            f"replaces '{second_doc.title}' (v{second_doc.version}, Effective {second_doc.effective_date}) "
            f"via temporal precedence at equal authority level ({top_doc.authority_level})."
        )
        return SelectionResult(top_doc, candidates[1:], reason, True)

    # Equal authority and equal date with no supersession -> irreconcilable
    return SelectionResult(
        None,
        candidates,
        f"Equal competing authority ({top_doc.authority_level}) with no valid supersession link between '{top_doc.title}' and '{second_doc.title}'.",
        False
    )

def resolution_node(state: GraphState) -> Dict[str, Any]:
    """
    Finalizes the answer based on adversarial audit results:
    - If no contradiction: Output the verified draft (status: VERIFIED).
    - If contradiction exists and governing document is clear: Output governing policy,
      explain why it was chosen, show previous version for context, and list potential ripple effects (status: CONFLICT_RESOLVED).
    - If authority is equal, conflict cannot be reconciled, or Ghost Reference exists:
      Refuse to guess. Display both positions side by side with provenance and flag (status: FLAGGED_FOR_REVIEW).
    - If target_date is supplied by user (time-travel query): Evaluate validity at that date.
    """
    draft = state.get("draft_answer", "")
    passages = state.get("filtered_passages", [])
    critique = state.get("critique")
    target_date = state.get("target_date")
    provenance = dict(state.get("provenance_details", {}) or {})

    has_ghost = provenance.get("has_ghost_reference", False)
    has_contradiction = critique.has_contradiction if critique else False

    # Check time-travel context
    time_travel_note = ""
    if target_date:
        time_travel_note = f"\n> **Time-Travel Snapshot**: Evaluated strictly as of **{target_date}**. Later amendments are excluded from this ruling.\n\n"

    # 1. GHOST REFERENCE OR IRRECONCILABLE CONFLICT -> FLAGGED_FOR_REVIEW
    selection = _determine_governing_doc(passages, target_date)
    
    if has_ghost or (has_contradiction and not selection.is_reconciled):
        status = "FLAGGED_FOR_REVIEW"

        # Build side-by-side comparison
        side_by_side = []
        for p in passages:
            side_by_side.append({
                "doc_id": p.doc_id,
                "title": p.metadata.title,
                "version": p.metadata.version,
                "effective_date": p.metadata.effective_date,
                "issuer": p.metadata.issuer,
                "authority_level": p.metadata.authority_level,
                "supersedes": p.metadata.supersedes,
                "excerpt": _clean_markdown_headings(p.content)
            })

        conflict_reasons = []
        if has_ghost:
            conflict_reasons.append("Unverified Ghost Reference: Document references a non-existent document ID in supersedes.")
        if critique and critique.contradiction_details:
            conflict_reasons.extend(critique.contradiction_details)
        if not selection.is_reconciled:
            conflict_reasons.append(selection.reason)

        final_answer = (
            f"### ⚠️ FLAGGED FOR HUMAN REVIEW: IRRECONCILABLE DOCUMENT CONFLICT\n\n"
            f"{time_travel_note}"
            f"TruthGuard refuses to guess or silently blend mutually conflicting documents.\n\n"
            f"#### Conflict Reasons:\n"
            + "\n".join(f"- {r}" for r in conflict_reasons)
            + "\n\n#### Competing Positions Side-by-Side:\n"
        )

        for s in side_by_side:
            final_answer += (
                f"\n--- \n"
                f"**Document**: {s['title']} (Ver {s['version']})\n"
                f"- **Issuer**: {s['issuer']} (Authority Level: {s['authority_level']})\n"
                f"- **Effective Date**: {s['effective_date']}\n"
                f"- **Claims**: \"{s['excerpt']}\"\n"
            )

        provenance["side_by_side"] = side_by_side
        provenance["status"] = status
        provenance["verdict_reason"] = "Contradiction cannot be reconciled automatically."

        return {
            "status": status,
            "final_answer": final_answer,
            "provenance_details": provenance
        }

    # 2. CONTRADICTION RESOLVED WITH GOVERNING DOCUMENT
    if has_contradiction and selection.is_reconciled and selection.governing:
        status = "CONFLICT_RESOLVED"
        gov = selection.governing

        # Extract operative governing content
        gov_chunks = [p.content for p in passages if p.doc_id == gov.doc_id]
        operative_chunks = [c for c in gov_chunks if not c.startswith("# ")]
        raw_gov = " ".join(operative_chunks) if operative_chunks else (" ".join(gov_chunks) if gov_chunks else draft)
        gov_content = _clean_markdown_headings(raw_gov)

        # Extract previous/superseded content for context
        previous_sections = []
        for other in selection.competitors:
            other_chunks = [p.content for p in passages if p.doc_id == other.doc_id]
            operative_other = [c for c in other_chunks if not c.startswith("# ")]
            raw_other = " ".join(operative_other) if operative_other else (" ".join(other_chunks) if other_chunks else "")
            clean_prior = _clean_markdown_headings(raw_other)[:250]
            previous_sections.append(
                f"- **Previous / Subordinate Policy**: *{other.title}* (v{other.version}, Date: {other.effective_date}, Issuer: {other.issuer})\n"
                f"  - Prior Clause: \"{clean_prior}...\""
            )

        ripple_effects = [
            "Update all downstream departmental guidelines and employee handbook portals.",
            "Verify automated payroll/HRMS calculation rules match the governing policy.",
            "Issue an executive memorandum clarifying the supersession to all department managers."
        ]

        final_answer = (
            f"### ✅ Governing Policy Verdict: [Doc: {gov.title}, Ver: {gov.version}, Date: {gov.effective_date}]\n\n"
            f"{time_travel_note}"
            f"**Resolution**: Based on adversarial precedence verification, **{gov.title}** governs this requirement.\n\n"
            f"**Governing Clause**: {gov_content}\n\n"
            f"#### Precedence Justification\n"
            f"{selection.reason}\n\n"
            f"#### Previous Version Context\n"
            + ("\n".join(previous_sections) if previous_sections else "None") + "\n\n"
            f"#### Potential Ripple Effects\n"
            + "\n".join(f"- {eff}" for eff in ripple_effects)
        )

        provenance["governing_doc"] = gov.model_dump()
        provenance["status"] = status
        provenance["verdict_reason"] = selection.reason

        return {
            "status": status,
            "final_answer": final_answer,
            "provenance_details": provenance
        }

    # 3. NO CONTRADICTION -> VERIFIED
    status = "VERIFIED"
    final_answer = draft
    if time_travel_note:
        final_answer = time_travel_note + final_answer

    provenance["status"] = status
    provenance["verdict_reason"] = "All source documents verified without contradictions."

    return {
        "status": status,
        "final_answer": final_answer,
        "provenance_details": provenance
    }
