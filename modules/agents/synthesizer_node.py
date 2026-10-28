import re
import logging
from typing import Dict, Any, List
from modules.schemas import GraphState, PassageChunk
from modules.llm import get_llm

logger = logging.getLogger("truthguard.synthesizer")

SYNTHESIZER_PROMPT_TEMPLATE = """You are TruthGuard Synthesizer, an AI agent specialized in high-integrity document synthesis.
Your mission is to draft an accurate, fact-based answer to the user's question using ONLY the provided verified document passages.

STRICT INSTRUCTIONS:
1. Every factual statement or claim MUST include a citation in the exact format:
   [Doc: {{title}}, Ver: {{version}}, Date: {{effective_date}}]
2. Do NOT invent, assume, or extrapolate any facts outside the provided passages.
3. If passages disagree or state different numbers/rules, mention what each document specifies with its citation.
{revision_instructions}

User Question: {question}
Target Date: {target_date}

Verified Passages:
{passages_text}

Draft your concise, rigorously cited answer below:"""

def _format_passages_for_prompt(passages: List[PassageChunk]) -> str:
    parts = []
    for i, p in enumerate(passages, 1):
        m = p.metadata
        parts.append(
            f"Passage [{i}]:\n"
            f"Document Title: {m.title}\n"
            f"Version: {m.version}\n"
            f"Effective Date: {m.effective_date}\n"
            f"Issuer: {m.issuer} (Authority: {m.authority_level})\n"
            f"Content: {p.content}\n"
        )
    return "\n".join(parts)

def _extract_citations(text: str) -> List[Dict[str, str]]:
    """Extracts [Doc: ..., Ver: ..., Date: ...] tags from generated answer."""
    pattern = r'\[Doc:\s*([^,]+?),\s*Ver:\s*([^,]+?),\s*Date:\s*([^\]]+?)\]'
    matches = re.findall(pattern, text)
    citations = []
    seen = set()
    for title, ver, date in matches:
        key = (title.strip(), ver.strip(), date.strip())
        if key not in seen:
            seen.add(key)
            citations.append({
                "title": title.strip(),
                "version": ver.strip(),
                "effective_date": date.strip(),
                "tag": f"[Doc: {title.strip()}, Ver: {ver.strip()}, Date: {date.strip()}]"
            })
    return citations

def _deterministic_synthesis(passages: List[PassageChunk], question: str, target_date: str = None, critique=None) -> str:
    """
    Deterministic synthesis engine used when LLM is unavailable or for testing.
    Constructs statements mapped directly to evidence chunks with citations.
    """
    if not passages:
        return "No authorized document passages were found to answer the query."

    # If target_date is given, sort/filter passages by effective date
    valid_passages = passages
    if target_date:
        valid_passages = [p for p in passages if p.metadata.effective_date <= target_date]
        if not valid_passages:
            valid_passages = passages

    statements = []
    for p in valid_passages:
        meta = p.metadata
        # Pick the most relevant sentences from the chunk
        lines = [line.strip() for line in p.content.split("\n") if line.strip()]
        snippet = " ".join(lines[:3]) if lines else p.content.strip()
        citation = f"[Doc: {meta.title}, Ver: {meta.version}, Date: {meta.effective_date}]"
        statements.append(f"{snippet} {citation}")

    return "\n\n".join(statements)

def synthesizer_node(state: GraphState) -> Dict[str, Any]:
    """
    Synthesizes a draft answer with strict citation tags from filtered passages.
    """
    question = state.get("question", "")
    target_date = state.get("target_date")
    passages = state.get("filtered_passages", [])
    critique = state.get("critique")
    revision_count = state.get("revision_count", 0)

    if not passages:
        return {
            "draft_answer": "No verified document evidence found.",
            "citations": []
        }

    revision_instructions = ""
    if critique and not critique.is_valid:
        feedback_lines = []
        if critique.has_contradiction:
            feedback_lines.append(f"- Contradictions identified: {'; '.join(critique.contradiction_details)}")
        if critique.has_staleness:
            feedback_lines.append(f"- Outdated/stale evidence: {'; '.join(critique.staleness_details)}")
        if critique.has_unsupported_claims:
            feedback_lines.append(f"- Unsupported claims to remove: {'; '.join(critique.unsupported_claims)}")
        revision_instructions = (
            "CRITIQUE REVISION DIRECTIVE:\n"
            "Your previous draft had the following defects. You MUST correct them:\n"
            + "\n".join(feedback_lines) + "\n"
        )

    llm = get_llm()
    draft = ""
    if llm:
        try:
            prompt = SYNTHESIZER_PROMPT_TEMPLATE.format(
                question=question,
                target_date=target_date or "Current/Latest",
                passages_text=_format_passages_for_prompt(passages),
                revision_instructions=revision_instructions
            )
            response = llm.invoke(prompt)
            draft = response.content.strip()
        except Exception as e:
            logger.error(f"Synthesizer LLM invocation error: {e}. Falling back to deterministic synthesizer.")
            draft = _deterministic_synthesis(passages, question, target_date, critique)
    else:
        draft = _deterministic_synthesis(passages, question, target_date, critique)

    citations = _extract_citations(draft)

    # Ensure every passage referenced in deterministic mode has citation
    if not citations and passages:
        for p in passages:
            meta = p.metadata
            citations.append({
                "title": meta.title,
                "version": meta.version,
                "effective_date": meta.effective_date,
                "tag": f"[Doc: {meta.title}, Ver: {meta.version}, Date: {meta.effective_date}]"
            })

    return {
        "draft_answer": draft,
        "citations": citations
    }

