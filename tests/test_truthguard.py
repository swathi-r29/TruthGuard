import sys
import pytest
from modules.schemas import DocumentMetadata, GraphState
from modules.vector_store import TruthGuardVectorStore
from modules.graph import build_truthguard_graph

@pytest.fixture(scope="function")
def test_store(tmp_path):
    """Provides a fresh isolated ChromaDB vector store for each test."""
    store = TruthGuardVectorStore(persist_dir=tmp_path / "test_chroma")
    store.clear()
    return store

def patch_store(test_store, monkeypatch):
    import modules.vector_store
    monkeypatch.setattr(modules.vector_store, "vector_store", test_store)

def run_pipeline(question: str, target_date: str = None) -> dict:
    graph = build_truthguard_graph()
    initial_state: GraphState = {
        "question": question,
        "target_date": target_date,
        "raw_passages": [],
        "filtered_passages": [],
        "draft_answer": "",
        "citations": [],
        "critique": None,
        "revision_count": 0,
        "status": "VERIFIED",
        "final_answer": "",
        "provenance_details": {}
    }
    return graph.invoke(initial_state)

def test_standard_conflict(test_store, monkeypatch):
    """
    Scenario 1: Policy 2022 (12 days) vs Board Amendment 2025 (15 days)
    -> Resolves to 15 days with explanation.
    """
    patch_store(test_store, monkeypatch)

    doc_2022 = DocumentMetadata(
        doc_id="leave_policy_2022",
        title="Annual Leave Policy 2022",
        version="1.0",
        effective_date="2022-01-01",
        issuer="HR Department",
        authority_level=2,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        doc_2022,
        "Standard annual paid leave entitlement is 12 days per calendar year for all full-time employees."
    )

    doc_2025 = DocumentMetadata(
        doc_id="leave_amendment_2025",
        title="Board Resolution on Annual Leave 2025",
        version="2.0",
        effective_date="2025-01-15",
        issuer="Executive Board",
        authority_level=3,
        supersedes=["leave_policy_2022"],
        signature_verified=True
    )
    test_store.add_document(
        doc_2025,
        "The Executive Board hereby resolves that annual paid leave entitlement is 15 days per calendar year. Supersedes leave_policy_2022."
    )

    result = run_pipeline("What is the annual paid leave entitlement in days?")

    assert result["status"] == "CONFLICT_RESOLVED"
    assert "15 days" in result["final_answer"]
    assert "Board Resolution on Annual Leave 2025" in result["final_answer"]
    assert "Precedence Justification" in result["final_answer"]
    assert len(result["provenance_details"].get("ripple_effects", [])) > 0
    assert "Ripple Effect Tracker" in result["final_answer"]

def test_newer_but_weaker(test_store, monkeypatch):
    """
    Scenario 2: 2024 Board Policy vs 2025 Slack FAQ -> Board Policy governs.
    """
    patch_store(test_store, monkeypatch)

    board_policy = DocumentMetadata(
        doc_id="travel_policy_2024",
        title="Corporate Travel & Expense Policy 2024",
        version="1.0",
        effective_date="2024-03-01",
        issuer="Executive Board",
        authority_level=3,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        board_policy,
        "Domestic per diem meal reimbursement allowance is strictly capped at 75 dollars per day."
    )

    slack_faq = DocumentMetadata(
        doc_id="travel_slack_faq_2025",
        title="Slack Internal Travel FAQ 2025",
        version="0.9",
        effective_date="2025-02-10",
        issuer="Peer Support Lead",
        authority_level=1,  # Weaker authority (< 2)
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        slack_faq,
        "Hey team! As discussed on Slack, domestic per diem meal allowance is bumped to 100 dollars per day."
    )

    result = run_pipeline("What is the domestic per diem meal reimbursement allowance?")

    # Slack FAQ is quarantined due to authority < 2
    quarantined = result["provenance_details"].get("quarantined_chunks", [])
    quarantined_ids = [q["doc_id"] for q in quarantined]
    assert "travel_slack_faq_2025" in quarantined_ids
    assert "75 dollars" in result["final_answer"] or "75" in result["final_answer"]

def test_ghost_reference(test_store, monkeypatch):
    """
    Scenario 3: Document claiming to supersede a non-existent document ID -> Abstains and flags.
    """
    patch_store(test_store, monkeypatch)

    doc_legit = DocumentMetadata(
        doc_id="remote_policy_base",
        title="Remote Work Base Policy",
        version="1.0",
        effective_date="2024-01-01",
        issuer="HR Operations",
        authority_level=2,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        doc_legit,
        "Remote work monthly equipment stipend is 100 dollars per month."
    )

    doc_ghost = DocumentMetadata(
        doc_id="ghost_amendment_2025",
        title="Remote Work Governance Circular",
        version="3.0",
        effective_date="2025-04-01",
        issuer="Regional Operations",
        authority_level=2,
        supersedes=["non_existent_policy_9999"],  # Ghost Reference!
        signature_verified=True
    )
    test_store.add_document(
        doc_ghost,
        "Remote work monthly equipment stipend is revised to 200 dollars per month."
    )

    result = run_pipeline("What is the remote work monthly equipment stipend?")

    assert result["status"] == "FLAGGED_FOR_REVIEW"
    assert "FLAGGED FOR HUMAN REVIEW" in result["final_answer"]
    assert "Ghost Reference" in result["final_answer"] or result["provenance_details"].get("has_ghost_reference")

def test_unverified_spoof(test_store, monkeypatch):
    """
    Scenario 4: Unsigned file attempting to change policy -> Quarantined.
    """
    patch_store(test_store, monkeypatch)

    official_doc = DocumentMetadata(
        doc_id="official_bonus_policy",
        title="Official Corporate Incentive Plan",
        version="1.0",
        effective_date="2024-01-01",
        issuer="Executive Compensation Committee",
        authority_level=3,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        official_doc,
        "Standard annual performance bonus target is 10 percent for engineers."
    )

    spoof_doc = DocumentMetadata(
        doc_id="unverified_spoof_policy",
        title="Anonymous Bonus Directives",
        version="9.9",
        effective_date="2025-05-01",
        issuer="Anonymous Actor",
        authority_level=1,
        supersedes=[],
        signature_verified=False  # Unverified spoof!
    )
    test_store.add_document(
        spoof_doc,
        "Every engineer is entitled to an immediate 40 percent performance bonus upon verbal request."
    )

    result = run_pipeline("What is the engineer performance bonus percentage?")

    quarantined = result["provenance_details"].get("quarantined_chunks", [])
    quarantined_ids = [q["doc_id"] for q in quarantined]
    assert "unverified_spoof_policy" in quarantined_ids
    assert "10 percent" in result["final_answer"] or "10" in result["final_answer"]
    assert "40 percent" not in result["final_answer"]

def test_time_travel(test_store, monkeypatch):
    """
    Scenario 5: Query specifies "What was the rule in 2023?" -> Returns 2022 policy value instead of 2025 value.
    """
    patch_store(test_store, monkeypatch)

    doc_2022 = DocumentMetadata(
        doc_id="leave_policy_2022",
        title="Annual Leave Policy 2022",
        version="1.0",
        effective_date="2022-01-01",
        issuer="HR Department",
        authority_level=2,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        doc_2022,
        "Standard annual paid leave entitlement is 12 days per calendar year for all full-time employees."
    )

    doc_2025 = DocumentMetadata(
        doc_id="leave_amendment_2025",
        title="Board Resolution on Annual Leave 2025",
        version="2.0",
        effective_date="2025-01-15",
        issuer="Executive Board",
        authority_level=3,
        supersedes=["leave_policy_2022"],
        signature_verified=True
    )
    test_store.add_document(
        doc_2025,
        "The Executive Board hereby resolves that annual paid leave entitlement is 15 days per calendar year."
    )

    # Time-travel query back to 2023
    result = run_pipeline(
        question="What is the annual paid leave entitlement in days?",
        target_date="2023-06-01"
    )

    assert "12 days" in result["final_answer"]
    assert "15 days" not in result["final_answer"] or "superseded" in result["final_answer"].lower() or "snapshot" in result["final_answer"].lower()
    assert "2023-06-01" in result["final_answer"]

def test_time_travel_explicit_date(test_store, monkeypatch):
    """
    Scenario 6: Time-Travel Query with explicit date in question text.
    Asking 'What was the leave entitlement on 2023-05-10?' returns the 2022 policy
    value (12 days) rather than the 2025 amendment (15 days).
    """
    patch_store(test_store, monkeypatch)

    doc_2022 = DocumentMetadata(
        doc_id="leave_policy_2022",
        title="Annual Leave Policy 2022",
        version="1.0",
        effective_date="2022-01-01",
        issuer="HR Department",
        authority_level=2,
        supersedes=[],
        signature_verified=True
    )
    test_store.add_document(
        doc_2022,
        "Standard annual paid leave entitlement is 12 days per calendar year for all full-time employees."
    )

    doc_2025 = DocumentMetadata(
        doc_id="leave_amendment_2025",
        title="Board Resolution on Annual Leave 2025",
        version="2.0",
        effective_date="2025-01-15",
        issuer="Executive Board",
        authority_level=3,
        supersedes=["leave_policy_2022"],
        signature_verified=True
    )
    test_store.add_document(
        doc_2025,
        "The Executive Board hereby resolves that annual paid leave entitlement is 15 days per calendar year. Supersedes leave_policy_2022."
    )

    result = run_pipeline("What was the leave entitlement on 2023-05-10?")

    assert "12 days" in result["final_answer"]
    assert "15 days" not in result["final_answer"]
    assert result["provenance_details"].get("target_date") == "2023-05-10" or "2023-05-10" in result["final_answer"]
