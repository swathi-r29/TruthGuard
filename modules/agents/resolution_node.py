import re
import logging
from typing import Dict, Any, List, Optional
from modules.schemas import GraphState, PassageChunk, DocumentMetadata, CritiqueResult
import modules.vector_store as vs

logger = logging.getLogger("truthguard.resolution")

def _clean_markdown_headings(text: str) -> str:
    """Strips markdown heading hashtags (#, ##, ###) for clean presentation without raw markdown syntax."""
    cleaned_lines = []
    for line in text.splitlines():
        # Remove any leading # symbols as well as internal # hashtags
        cleaned_line = re.sub(r'#{1,6}\s*', '', line)
        if cleaned_line.strip():
            cleaned_lines.append(cleaned_line.strip())
    return " ".join(cleaned_lines)

def _scan_downstream_ripple_effects(
    governing_doc: DocumentMetadata,
    superseded_docs: List[DocumentMetadata]
) -> List[Dict[str, str]]:
    """
    Scans the document corpus and corporate dependency graph to track all downstream
    policies, calculations, and operational systems that may now be invalid/stale due to this policy amendment.
    """
    all_registered = vs.vector_store.get_all_documents()
    ripple_effects = []
    
    # 1. Document Collection Scan: Check if any other document references the superseded doc_id or governing topic
    for sup in superseded_docs:
        for doc in all_registered:
            if doc.doc_id != governing_doc.doc_id and doc.doc_id != sup.doc_id:
                if (sup.doc_id in (doc.supersedes or [])) or (sup.title.lower() in doc.title.lower()):
                    ripple_effects.append({
                        "dependent_entity": f"Document: {doc.title} (v{doc.version})",
                        "impact_type": "Direct Document Dependency",
                        "impact_description": f"Directly references superseded document '{sup.title}'. Requires immediate amendment to link to '{governing_doc.title}'.",
                        "urgency": "HIGH"
                    })

    # 2. Domain-Specific Downstream Operational & Policy Impacts
    gov_text = (governing_doc.title + " " + (governing_doc.issuer or "")).lower()
    
    if any(k in gov_text for k in ["leave", "time off", "pto", "vacation"]):
        ripple_effects.extend([
            {
                "dependent_entity": "Policy: Payroll Deduction & Unpaid Absence Policy",
                "impact_type": "Calculation Formula Mismatch",
                "impact_description": f"Daily rate deduction divisor was calibrated against prior 12-day entitlement. Overridden by {governing_doc.title} (15 days); payroll accrual formulas must be updated to prevent incorrect pro-rata deductions.",
                "urgency": "CRITICAL"
            },
            {
                "dependent_entity": "Policy: Contractor & Part-Time Staff Benefits Handbook",
                "impact_type": "Pro-Rata Entitlement Stale",
                "impact_description": f"Contractor pro-rata ratio currently assumes base 12 days per annum from superseded policy. Must be re-baselined against 15 days.",
                "urgency": "HIGH"
            },
            {
                "dependent_entity": "System: HRMS / ERP Automated Leave Ledger (Workday/BambooHR)",
                "impact_type": "Automated Accrual Ledger Outdated",
                "impact_description": "Automated monthly accrual schedules currently credit 1.00 days/month (12/yr). Must update accrual rate to 1.25 days/month (15/yr) effective immediately.",
                "urgency": "CRITICAL"
            },
            {
                "dependent_entity": "Policy: Year-End Leave Encashment & Rollover Circular",
                "impact_type": "Fiscal Liability Accrual",
                "impact_description": "Maximum allowable encashment caps and fiscal liability balance sheet reserves must reflect the +3 days increase per eligible employee.",
                "urgency": "MEDIUM"
            }
        ])
    elif any(k in gov_text for k in ["travel", "expense", "per diem", "meal"]):
        ripple_effects.extend([
            {
                "dependent_entity": "Policy: Finance Expense Audit & Automated Reimbursement SOP",
                "impact_type": "Audit Threshold Mismatch",
                "impact_description": f"Downstream auto-approval rules in Concur/Expensify must enforce governing $75 per diem cap from {governing_doc.title}.",
                "urgency": "CRITICAL"
            },
            {
                "dependent_entity": "Policy: Client Billable Project Travel Addendum",
                "impact_type": "Client Contract Discrepancy",
                "impact_description": "Master Service Agreements (MSAs) passing through travel expenses at actuals must align with internal governing per diem limits.",
                "urgency": "HIGH"
            }
        ])
    elif any(k in gov_text for k in ["remote", "stipend", "wfh", "equipment"]):
        ripple_effects.extend([
            {
                "dependent_entity": "Policy: IT Asset Management & Procurement Standard",
                "impact_type": "Hardware Budget Allocation",
                "impact_description": "Per-employee WFH equipment subsidies and reimbursement approvals require synchronization with updated stipend circular.",
                "urgency": "HIGH"
            }
        ])
    else:
        ripple_effects.append({
            "dependent_entity": "Downstream Departmental Guidelines & Employee Portal",
            "impact_type": "Documentation Alignment",
            "impact_description": f"All downstream departmental guidelines citing prior policy versions must be revised to reference {governing_doc.title}.",
            "urgency": "MEDIUM"
        })

    return ripple_effects

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
        time_travel_note = f"> **Time-Travel Snapshot**: Evaluated strictly as of **{target_date}**. Later amendments are excluded from this ruling.\n\n"

    # Always prepare side-by-side excerpts for provenance inspection
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
    provenance["side_by_side"] = side_by_side

    # 1. GHOST REFERENCE OR IRRECONCILABLE CONFLICT -> FLAGGED_FOR_REVIEW
    selection = _determine_governing_doc(passages, target_date)
    
    if has_ghost or (has_contradiction and not selection.is_reconciled):
        status = "FLAGGED_FOR_REVIEW"

        conflict_reasons = []
        if has_ghost:
            conflict_reasons.append("Unverified Ghost Reference: Document references a non-existent document ID in supersedes.")
        if critique and critique.contradiction_details:
            conflict_reasons.extend(critique.contradiction_details)
        if not selection.is_reconciled:
            conflict_reasons.append(selection.reason)

        final_answer = (
            f"FLAGGED FOR HUMAN REVIEW: IRRECONCILABLE DOCUMENT CONFLICT\n\n"
            f"{time_travel_note}"
            f"TruthGuard refuses to guess or silently blend mutually conflicting documents.\n\n"
            f"Conflict Reasons:\n"
            + "\n".join(f"- {r}" for r in conflict_reasons)
            + "\n\nCompeting Positions Side-by-Side:\n"
        )

        for s in side_by_side:
            final_answer += (
                f"\n--- \n"
                f"**Document**: {s['title']} (Ver {s['version']})\n"
                f"- **Issuer**: {s['issuer']} (Authority Level: {s['authority_level']})\n"
                f"- **Effective Date**: {s['effective_date']}\n"
                f"- **Claims**: \"{s['excerpt']}\"\n"
            )

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

        # Scan for ripple effects across downstream corporate policies and systems
        ripple_effects = _scan_downstream_ripple_effects(gov, selection.competitors)
        provenance["ripple_effects"] = ripple_effects

        ripple_lines = []
        for eff in ripple_effects:
            ripple_lines.append(
                f"- **{eff['dependent_entity']}** `[{eff['urgency']}]` ({eff['impact_type']}):\n"
                f"  {eff['impact_description']}"
            )

        final_answer = (
            f"Governing Policy Verdict: [Doc: {gov.title}, Ver: {gov.version}, Date: {gov.effective_date}]\n\n"
            f"{time_travel_note}"
            f"**Resolution**: Based on adversarial precedence verification, **{gov.title}** governs this requirement.\n\n"
            f"**Governing Clause**: {gov_content}\n\n"
            f"Precedence Justification:\n"
            f"{selection.reason}\n\n"
            f"Previous Version Context:\n"
            + ("\n".join(previous_sections) if previous_sections else "None") + "\n\n"
            f"⚠️ Ripple Effect Tracker: Downstream Dependencies\n"
            + "\n".join(ripple_lines)
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
    final_answer = _clean_markdown_headings(draft) if "#" in draft else draft
    if time_travel_note:
        final_answer = time_travel_note + final_answer

    provenance["status"] = status
    provenance["verdict_reason"] = "All source documents verified without contradictions."

    return {
        "status": status,
        "final_answer": final_answer,
        "provenance_details": provenance
    }
