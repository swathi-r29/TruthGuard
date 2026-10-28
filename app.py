import os
import json
import logging
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from modules.schemas import (
    DocumentMetadata,
    QueryRequest,
    QueryResponse,
    GraphState
)
from modules.document_processor import process_document
from modules.vector_store import vector_store
from modules.graph import truthguard_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("truthguard.api")

app = FastAPI(
    title="TruthGuard: Adversarial Verification for Multi-Agent Document Q&A",
    description="Multi-agent orchestration preventing silent conflation of conflicting corporate documents.",
    version="2.0"
)

# Enable CORS for React frontend (Vite default port 5173 and others)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "TruthGuard",
        "version": "2.0",
        "status": "online",
        "provider": config.LLM_PROVIDER,
        "docs_count": len(vector_store.get_all_documents())
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "provider": config.LLM_PROVIDER,
        "gemini_configured": bool(config.GEMINI_API_KEY and "your_gemini" not in config.GEMINI_API_KEY),
        "groq_configured": bool(config.GROQ_API_KEY and "your_groq" not in config.GROQ_API_KEY),
        "total_documents": len(vector_store.get_all_documents())
    }

@app.get("/api/documents")
def list_documents():
    """
    Returns list of all ingested documents and their authority metadata.
    """
    docs = vector_store.get_all_documents()
    return {"documents": [d.model_dump() for d in docs]}

@app.delete("/api/documents")
def clear_documents():
    """
    Clears all documents from vector store.
    """
    vector_store.clear()
    return {"success": True, "message": "All documents cleared from TruthGuard vector store."}

@app.post("/api/seed_samples")
def seed_samples_endpoint():
    """
    Seeds the test corpus documents into the vector store.
    """
    from seed_samples import seed_sample_corpus
    seed_sample_corpus()
    return {"success": True, "total_documents": len(vector_store.get_all_documents())}

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    version: Optional[str] = Form("1.0"),
    effective_date: Optional[str] = Form("2024-01-01"),
    issuer: Optional[str] = Form("Executive Board"),
    authority_level: Optional[int] = Form(3),
    supersedes: Optional[str] = Form(""),
    signature_verified: Optional[bool] = Form(True)
):
    """
    Accepts files (PDF, TXT, MD), extracts metadata and text, and loads chunks into ChromaDB.
    """
    try:
        content = await file.read()
        filename = file.filename or "uploaded_document.txt"
        
        proc_result = process_document(content, filename)
        if not proc_result.get("success"):
            raise HTTPException(status_code=400, detail=proc_result.get("error", "Document processing failed"))

        full_text = proc_result.get("full_text", "")
        if not full_text.strip():
            raise HTTPException(status_code=400, detail="Extracted document text is empty.")

        # Parse supersedes if string
        supersedes_list = []
        if supersedes:
            supersedes_str = supersedes.strip()
            if supersedes_str.startswith("[") and supersedes_str.endswith("]"):
                try:
                    supersedes_list = json.loads(supersedes_str)
                except Exception:
                    supersedes_list = [s.strip() for s in supersedes_str.strip("[]").split(",") if s.strip()]
            else:
                supersedes_list = [s.strip() for s in supersedes_str.split(",") if s.strip()]

        derived_id = doc_id.strip() if doc_id and doc_id.strip() else os.path.splitext(filename)[0]
        derived_title = title.strip() if title and title.strip() else os.path.splitext(filename)[0]

        meta = DocumentMetadata(
            doc_id=derived_id,
            title=derived_title,
            version=version or "1.0",
            effective_date=effective_date or "2024-01-01",
            issuer=issuer or "Unknown",
            authority_level=int(authority_level if authority_level is not None else 1),
            supersedes=supersedes_list,
            signature_verified=bool(signature_verified)
        )

        chunk_count = vector_store.add_document(meta, full_text)

        return {
            "success": True,
            "doc_id": meta.doc_id,
            "title": meta.title,
            "version": meta.version,
            "authority_level": meta.authority_level,
            "effective_date": meta.effective_date,
            "chunks_created": chunk_count,
            "ocr_used": proc_result.get("ocr_used", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", response_model=QueryResponse)
def query_truthguard(request: QueryRequest):
    """
    Accepts query & target_date, runs the LangGraph state graph pipeline,
    and returns full state including status, final_answer, draft_critique_log, and provenance_details.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        initial_state: GraphState = {
            "question": request.query.strip(),
            "target_date": request.target_date.strip() if request.target_date else None,
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

        # Run multi-agent graph
        final_state = truthguard_graph.invoke(initial_state)

        critique_obj = final_state.get("critique")

        return QueryResponse(
            query=request.query,
            status=final_state.get("status", "VERIFIED"),
            final_answer=final_state.get("final_answer", ""),
            citations=final_state.get("citations", []),
            critique=critique_obj,
            revision_count=final_state.get("revision_count", 0),
            provenance_details=final_state.get("provenance_details", {}),
            draft_answer=final_state.get("draft_answer", "")
        )
    except Exception as e:
        logger.error(f"Query pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/api/corpus_health")
def scan_corpus_health():
    """
    Corpus Health Scanner: Proactively audits all ingested documents to find latent
    policy conflicts, ghost references, and staleness before any user asks a question.
    """
    from modules.agents.critic_node import _audit_passages_adversarially
    all_passages = vector_store.get_all_passages()
    all_docs = vector_store.get_all_documents()

    if not all_passages:
        return {
            "status": "HEALTHY",
            "health_score": 100,
            "total_documents": 0,
            "total_chunks": 0,
            "conflicts_count": 0,
            "staleness_count": 0,
            "ghost_references_count": 0,
            "contradictions": [],
            "staleness": [],
            "ghost_references": []
        }

    (has_contra, contra_details,
     has_stale, stale_details,
     has_ghost, ghost_details) = _audit_passages_adversarially(all_passages)

    # Clean deduplication: ensure each finding is reported exactly once
    unique_contra = list(dict.fromkeys(contra_details))
    unique_stale = list(dict.fromkeys(stale_details))
    unique_ghost = list(dict.fromkeys(ghost_details))

    total_issues = len(unique_contra) + len(unique_stale) + len(unique_ghost)
    # Calibrated health score: 100 base, deducted per distinct issue
    health_score = max(0, 100 - (total_issues * 15))

    status = "HEALTHY" if total_issues == 0 else "WARNING" if total_issues <= 2 else "ACTION_REQUIRED"

    return {
        "status": status,
        "health_score": health_score,
        "total_documents": len(all_docs),
        "total_chunks": len(all_passages),
        "conflicts_count": len(unique_contra),
        "staleness_count": len(unique_stale),
        "ghost_references_count": len(unique_ghost),
        "contradictions": unique_contra,
        "staleness": unique_stale,
        "ghost_references": unique_ghost
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
