import json
import math
import hashlib
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

import config
from modules.schemas import DocumentMetadata, PassageChunk

logger = logging.getLogger("truthguard.vector_store")

class FastHashEmbedding(EmbeddingFunction):
    """
    Deterministic sub-millisecond embedding function based on normalized token hashing.
    Requires no remote downloads or heavy model checkpoints.
    """
    def __init__(self, dim: int = 256):
        self.dim = dim

    @staticmethod
    def name() -> str:
        return "fast_hash_embedding"

    def get_config(self) -> Dict[str, Any]:
        return {"dim": self.dim}

    @classmethod
    def build_from_config(cls, config: Dict[str, Any]):
        return cls(dim=config.get("dim", 256))

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for doc in input:
            vec = [0.0] * self.dim
            words = doc.lower().replace("\n", " ").split()
            if not words:
                embeddings.append(vec)
                continue
            for w in words:
                h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16) % self.dim
                vec[h] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings

class TruthGuardVectorStore:
    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or config.CHROMA_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_fn = FastHashEmbedding()
        self.collection = self.client.get_or_create_collection(
            name="truthguard_documents",
            embedding_function=self.embedding_fn
        )
        self._doc_registry_path = self.persist_dir / "documents_registry.json"
        self._documents: Dict[str, DocumentMetadata] = self._load_registry()

    def _load_registry(self) -> Dict[str, DocumentMetadata]:
        if self._doc_registry_path.exists():
            try:
                with open(self._doc_registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {k: DocumentMetadata(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading document registry: {e}")
        return {}

    def _save_registry(self):
        try:
            with open(self._doc_registry_path, "w", encoding="utf-8") as f:
                data = {k: v.model_dump() for k, v in self._documents.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving document registry: {e}")

    def chunk_text(self, text: str, chunk_size: int = 300, overlap: int = 60) -> List[str]:
        """
        Splits text into chunks preserving sentence/line flow.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) <= chunk_size:
                current = (current + "\n\n" + p).strip()
            else:
                if current:
                    chunks.append(current)
                # If paragraph itself is very long, split by sentences or chunks
                if len(p) > chunk_size:
                    for i in range(0, len(p), chunk_size - overlap):
                        part = p[i:i + chunk_size].strip()
                        if part:
                            chunks.append(part)
                    current = ""
                else:
                    current = p
        if current:
            chunks.append(current)
        return chunks if chunks else [text.strip()]

    def add_document(self, metadata: DocumentMetadata, text: str) -> int:
        """
        Chunks text, stores surrounding context for orphaned exception guard,
        and adds to vector DB.
        """
        raw_chunks = self.chunk_text(text)
        if not raw_chunks:
            return 0

        # Build surrounding context (previous + current + next)
        ids = []
        documents = []
        metadatas = []

        supersedes_json = json.dumps(metadata.supersedes or [])

        for i, chunk in enumerate(raw_chunks):
            chunk_id = f"{metadata.doc_id}_chunk_{i}"
            prev_chunk = raw_chunks[i - 1] if i > 0 else ""
            next_chunk = raw_chunks[i + 1] if i < len(raw_chunks) - 1 else ""
            surrounding = f"{prev_chunk}\n---\n{chunk}\n---\n{next_chunk}".strip()

            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "chunk_id": chunk_id,
                "doc_id": metadata.doc_id,
                "title": metadata.title,
                "version": metadata.version,
                "effective_date": metadata.effective_date,
                "issuer": metadata.issuer,
                "authority_level": int(metadata.authority_level),
                "supersedes": supersedes_json,
                "signature_verified": bool(metadata.signature_verified),
                "chunk_index": i,
                "surrounding_context": surrounding
            })

        # Remove existing chunks for this doc_id if updating
        try:
            existing = self.collection.get(where={"doc_id": metadata.doc_id})
            if existing and existing.get("ids"):
                self.collection.delete(ids=existing["ids"])
        except Exception:
            pass

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        self._documents[metadata.doc_id] = metadata
        self._save_registry()
        return len(ids)

    def search_passages(self, query: str, n_results: int = 15) -> List[PassageChunk]:
        """
        Retrieves top passages using vector similarity and relevance filtering.
        """
        total_docs = self.collection.count()
        if total_docs == 0:
            return []

        limit = min(n_results, total_docs)
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )

        passages: List[PassageChunk] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return passages

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        ids = results["ids"][0]
        dists = results.get("distances", [[0.0] * len(docs)])[0]

        # Calculate query keywords for hybrid relevance check
        stopwords = {"what", "is", "the", "in", "on", "at", "for", "a", "an", "and", "or", "of", "to", "how", "many", "was", "are", "be", "per", "by", "as", "all", "it"}
        q_tokens = {w.lower() for w in query.replace("?", " ").replace("!", " ").split() if w.lower() not in stopwords}
        d_min = dists[0] if dists else 0.0

        for idx, doc_text in enumerate(docs):
            meta_dict = metas[idx]
            chunk_id = ids[idx]
            d = dists[idx]

            # Keyword overlap with chunk content and document title
            text_tokens = set(doc_text.lower().split() + meta_dict.get("title", "").lower().split())
            overlap = len(q_tokens.intersection(text_tokens))

            # Exclude chunks that are vastly farther than best match or have weak relevance
            if len(docs) > 2 and ((d > (d_min + 0.30) and overlap < 2) or (overlap == 0 and d > d_min + 0.15)):
                continue

            supersedes_list = []
            try:
                supersedes_list = json.loads(meta_dict.get("supersedes", "[]"))
            except Exception:
                pass

            doc_meta = DocumentMetadata(
                doc_id=meta_dict.get("doc_id", "unknown"),
                title=meta_dict.get("title", "Untitled"),
                version=meta_dict.get("version", "1.0"),
                effective_date=meta_dict.get("effective_date", "2024-01-01"),
                issuer=meta_dict.get("issuer", "Unknown"),
                authority_level=int(meta_dict.get("authority_level", 1)),
                supersedes=supersedes_list,
                signature_verified=bool(meta_dict.get("signature_verified", True))
            )

            passage = PassageChunk(
                chunk_id=chunk_id,
                doc_id=doc_meta.doc_id,
                content=doc_text,
                surrounding_context=meta_dict.get("surrounding_context"),
                metadata=doc_meta
            )
            passages.append(passage)

        return passages

    def get_all_documents(self) -> List[DocumentMetadata]:
        return list(self._documents.values())

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self._documents.get(doc_id)

    def clear(self):
        try:
            self.client.delete_collection(name="truthguard_documents")
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name="truthguard_documents",
            embedding_function=self.embedding_fn
        )
        self._documents = {}
        self._save_registry()

# Global vector store singleton
vector_store = TruthGuardVectorStore()
