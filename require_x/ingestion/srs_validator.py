"""
REQUIRE-X SRS Document Validator
Uses the configured LLM to judge whether an uploaded document is genuinely a
Software Requirement Specification (SRS), falling back to a deterministic
keyword/section heuristic (DocumentParser.assess_srs_likelihood) when the LLM
is unavailable (offline mode) or returns something unparseable.
"""

from typing import Dict, Any, Optional

from require_x.agents.llm_provider import LLMProvider
from require_x.ingestion.parser import DocumentParser


SRS_CLASSIFIER_SYSTEM_PROMPT = """You are a strict document classifier for REQUIRE-X, a Software \
Requirements Engineering analysis tool. Your ONLY job is to decide whether a given document is a \
genuine Software Requirement Specification (SRS) - i.e. a document that specifies functional and/or \
non-functional requirements for a software system, generally structured similarly to IEEE/ISO/IEC \
29148 (sections such as scope, overall description, functional requirements, non-functional \
requirements, interfaces, constraints, use cases, etc.), and/or containing many discrete "shall" / \
"should" style requirement statements.

Documents that are NOT an SRS include (but are not limited to): resumes/CVs, research papers, \
meeting notes, source code, README files, marketing content, invoices, general project reports, \
proposals without formal requirement statements, slide decks, or any unrelated text.

Respond with STRICT JSON ONLY. No markdown code fences, no commentary before or after. Exactly this shape:
{
  "is_srs": true or false,
  "confidence": <integer 0-100, how confident you are in this classification>,
  "document_type": "<your best guess at what this document actually is, e.g. 'resume', 'SRS', 'research paper'>",
  "reason": "<one concise sentence explaining the decision>"
}
"""


def _classify_with_llm(
    llm: LLMProvider,
    raw_text: str,
    filename: str,
    max_chars: int = 6000
) -> Optional[Dict[str, Any]]:
    """
    Asks the configured LLM to classify whether a document is a genuine SRS.
    Returns None (rather than raising) if the LLM is unavailable/offline or the
    response can't be parsed, so the caller can fall back to the heuristic check.
    """
    excerpt = (raw_text or "").strip()
    if not excerpt:
        return None

    if len(excerpt) > max_chars:
        # SRS signals (title, scope, requirement sections) tend to show up early,
        # but keep a tail slice too since some documents front-load boilerplate.
        head = excerpt[: int(max_chars * 0.7)]
        tail = excerpt[-int(max_chars * 0.3):]
        excerpt = f"{head}\n\n...[truncated]...\n\n{tail}"

    user_prompt = (
        f"Filename: {filename}\n\n"
        f"Document excerpt:\n\"\"\"\n{excerpt}\n\"\"\"\n\n"
        "Classify this document as instructed in the system prompt."
    )

    try:
        response_text = llm.generate(SRS_CLASSIFIER_SYSTEM_PROMPT, user_prompt, json_mode=True)
    except Exception:
        return None

    if not response_text:
        # Offline provider, disabled key, or a failed API call all surface as "".
        return None

    parsed = LLMProvider.extract_json_block(response_text)
    if not parsed or "is_srs" not in parsed:
        return None

    is_srs = bool(parsed.get("is_srs"))
    try:
        confidence_pct = max(0, min(100, int(parsed.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence_pct = 0

    return {
        "is_srs": is_srs,
        "confidence": round(confidence_pct / 100, 2),
        "document_type": str(parsed.get("document_type") or "unknown").strip(),
        "reason": str(parsed.get("reason") or "").strip() or "No reason provided by the classifier.",
        "source": "llm"
    }


def assess_document_is_srs(
    llm: LLMProvider,
    raw_text: str,
    sections: Dict[str, str],
    filename: str
) -> Dict[str, Any]:
    """
    Primary entry point for the pre-flight SRS check.

    Tries the LLM classifier first (semantic judgement — handles SRS-like documents
    with unconventional structure, and rejects things that merely contain a few
    matching keywords). Falls back to the deterministic keyword/section heuristic
    if the LLM is offline or its response can't be parsed, so the check never fails
    open silently.
    """
    llm_result = _classify_with_llm(llm, raw_text, filename)
    if llm_result is not None:
        return llm_result

    heuristic_result = dict(DocumentParser.assess_srs_likelihood(raw_text, sections))
    heuristic_result["source"] = "heuristic"
    heuristic_result.setdefault("document_type", "unknown")
    return heuristic_result
