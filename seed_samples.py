import sys
from pathlib import Path
from modules.schemas import DocumentMetadata
from modules.vector_store import vector_store

def seed_sample_corpus():
    print("Seeding TruthGuard sample documents into ChromaDB...")
    samples_dir = Path(__file__).resolve().parent / "sample_documents"
    
    docs_to_seed = [
        {
            "filename": "leave_policy_2022.md",
            "doc_id": "leave_policy_2022",
            "title": "Annual Leave Policy 2022",
            "version": "1.0",
            "effective_date": "2022-01-01",
            "issuer": "HR Department",
            "authority_level": 2,
            "supersedes": [],
            "signature_verified": True
        },
        {
            "filename": "leave_amendment_2025.md",
            "doc_id": "leave_amendment_2025",
            "title": "Board Resolution on Annual Leave 2025",
            "version": "2.0",
            "effective_date": "2025-01-15",
            "issuer": "Executive Board",
            "authority_level": 3,
            "supersedes": ["leave_policy_2022"],
            "signature_verified": True
        },
        {
            "filename": "travel_policy_2024.md",
            "doc_id": "travel_policy_2024",
            "title": "Corporate Travel & Expense Policy 2024",
            "version": "1.0",
            "effective_date": "2024-03-01",
            "issuer": "Executive Board",
            "authority_level": 3,
            "supersedes": [],
            "signature_verified": True
        },
        {
            "filename": "travel_slack_faq_2025.md",
            "doc_id": "travel_slack_faq_2025",
            "title": "Slack Internal Travel FAQ 2025",
            "version": "0.9",
            "effective_date": "2025-02-10",
            "issuer": "Peer Support Lead",
            "authority_level": 1,
            "supersedes": [],
            "signature_verified": True
        },
        {
            "filename": "ghost_amendment_2025.md",
            "doc_id": "ghost_amendment_2025",
            "title": "Remote Work Governance Circular",
            "version": "3.0",
            "effective_date": "2025-04-01",
            "issuer": "Regional Operations",
            "authority_level": 2,
            "supersedes": ["non_existent_policy_9999"],
            "signature_verified": True
        },
        {
            "filename": "unverified_spoof_policy.md",
            "doc_id": "unverified_spoof_policy",
            "title": "Anonymous Bonus Directives",
            "version": "9.9",
            "effective_date": "2025-05-01",
            "issuer": "Anonymous Actor",
            "authority_level": 1,
            "supersedes": [],
            "signature_verified": False
        }
    ]

    total_chunks = 0
    for item in docs_to_seed:
        file_path = samples_dir / item["filename"]
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            meta = DocumentMetadata(
                doc_id=item["doc_id"],
                title=item["title"],
                version=item["version"],
                effective_date=item["effective_date"],
                issuer=item["issuer"],
                authority_level=item["authority_level"],
                supersedes=item["supersedes"],
                signature_verified=item["signature_verified"]
            )
            chunks = vector_store.add_document(meta, text)
            total_chunks += chunks
            print(f"  [+] Ingested '{meta.title}' ({chunks} chunks, Auth: {meta.authority_level})")
        else:
            print(f"  [-] File not found: {file_path}")

    print(f"\nSeeding complete! {len(docs_to_seed)} documents, {total_chunks} total chunks in ChromaDB.")

if __name__ == "__main__":
    seed_sample_corpus()
