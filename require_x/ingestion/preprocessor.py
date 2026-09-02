"""
REQUIRE-X Ingestion Preprocessor
Cleans and segments raw document text into candidate requirement statements.
"""

import re
from typing import List, Dict, Any, Tuple


class TextPreprocessor:
    """Preprocesses raw SRS text into structured candidate requirement chunks."""

    MODAL_VERBS_PATTERN = re.compile(
        r"\b(?:shall|must|should|will|is required to|needs to)\b", re.IGNORECASE
    )

    REQ_ID_PATTERN = re.compile(
        r"(?:(?:REQ|FR|NFR|BR|SR|SYS|USE|UC)[\-_]?\d+(?:\.\d+)*)", re.IGNORECASE
    )

    NON_REQ_SECTIONS = [
        "table of contents", "contents", "list of figures", "list of tables", "list of abbreviations",
        "abstract", "introduction", "literature review", "environmental study", "system configuration",
        "hardware requirements", "software requirements for development", "feasibility study",
        "system design", "system implementation", "results and discussion", "conclusion",
        "future enhancement", "bibliography", "references", "appendices"
    ]

    @classmethod
    def preprocess_text(cls, raw_text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Preprocesses text and extracts candidate requirement statements.
        Handles both bulleted/explicitly tagged requirements and structured numbered SRS sections.
        """
        # First clean out running footers and page numbering noise
        cleaned_text = cls._clean_document_noise(raw_text)

        # 1. Attempt structured numbered extraction (e.g., 4.6.1 User Interface ... The framework shall ...)
        structured_candidates = cls._extract_structured_numbered_requirements(cleaned_text)
        if len(structured_candidates) >= 4:
            return structured_candidates

        # 2. Section-based candidate extraction
        candidates: List[Dict[str, Any]] = []
        for section_name, section_content in sections.items():
            sec_lower = section_name.lower()
            if any(non_sec in sec_lower for non_sec in cls.NON_REQ_SECTIONS):
                continue

            lines = section_content.splitlines()
            buffer = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if buffer:
                        stmt = " ".join(buffer)
                        cls._process_candidate_statement(stmt, section_name, candidates)
                        buffer = []
                    continue

                is_new_item = bool(
                    re.match(r"^[\*\-\•\–\—\d+\.]\s+", stripped)
                    or cls.REQ_ID_PATTERN.match(stripped)
                )

                if is_new_item and buffer:
                    stmt = " ".join(buffer)
                    cls._process_candidate_statement(stmt, section_name, candidates)
                    buffer = [stripped]
                else:
                    buffer.append(stripped)

            if buffer:
                stmt = " ".join(buffer)
                cls._process_candidate_statement(stmt, section_name, candidates)

        # 3. Fallback: scan for any explicit requirement IDs in the text
        if not candidates:
            candidates = cls._extract_explicit_id_statements(cleaned_text)

        return candidates

    @classmethod
    def _clean_document_noise(cls, text: str) -> str:
        """Removes running headers, footers, page numbers, and dots."""
        lines = text.splitlines()
        clean_lines = []
        for line in lines:
            l = line.strip()
            if not l:
                continue
            if re.search(r"department of computer applications|gec thrissur|^\d+$|^a multi-agent ai framework", l, re.I):
                continue
            if re.search(r"\.\s*\.\s*\.\s*\.|\.{3,}\s*\d+", l):
                continue
            clean_lines.append(l)
        return "\n".join(clean_lines)

    @classmethod
    def _extract_structured_numbered_requirements(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extracts numbered SRS requirements like:
        4.6.1 User Interface
        The framework shall provide a simple user interface...
        """
        pattern = re.compile(
            r"(\b4\.[67]\.\d+|\b\d+\.\d+\.\d+)\s*\n\s*([A-Za-z\s\-_/]+?)\s*\n\s*(The\s+[\s\S]*?)(?=(?:\n\s*(?:4\.[67]|\d+\.\d+)\.\d+|\n\s*4\.8|\n\s*\d+\s+SYSTEM|\Z))",
            re.IGNORECASE
        )

        matches = pattern.findall(text)
        candidates = []
        for num, title, body in matches:
            clean_body = " ".join(body.split())
            clean_title = title.strip().replace("\n", " ")
            if not cls.MODAL_VERBS_PATTERN.search(clean_body):
                continue
            
            # Check if non-functional or functional based on section number (4.7) or title
            is_nfr = "4.7" in num or any(k in clean_title.lower() for k in ["scalability", "usability", "reliability", "maintainability", "security", "performance"])
            
            candidates.append({
                "raw_statement": f"{clean_title}: {clean_body}",
                "section": "Non-Functional Requirements" if is_nfr else "Functional Requirements",
                "detected_id": None,
                "contains_modal": True,
                "is_req_section": True
            })

        return candidates

    @classmethod
    def _extract_explicit_id_statements(cls, text: str) -> List[Dict[str, Any]]:
        """Extracts statements starting with FR-001, NFR-001, etc."""
        candidates = []
        pattern = re.compile(r"((?:FR|NFR|REQ|BR|SR)[\-_]?\d+[\:\-\.\s]+[\s\S]*?)(?=(?:FR|NFR|REQ|BR|SR)[\-_]?\d+|\Z)", re.I)
        matches = pattern.findall(text)
        for m in matches:
            clean = " ".join(m.split())
            if len(clean) > 15:
                id_match = cls.REQ_ID_PATTERN.search(clean)
                detected_id = id_match.group(0).upper() if id_match else None
                candidates.append({
                    "raw_statement": clean,
                    "section": "Functional Requirements" if (detected_id and "FR" in detected_id) else "Non-Functional Requirements",
                    "detected_id": detected_id,
                    "contains_modal": bool(cls.MODAL_VERBS_PATTERN.search(clean)),
                    "is_req_section": True
                })
        return candidates

    @classmethod
    def _process_candidate_statement(
        cls, statement: str, section: str, output_list: List[Dict[str, Any]]
    ):
        """Filters and refines a single candidate statement."""
        clean_stmt = re.sub(r"^[\*\-\•\–\—\d+\.\:\)\s]+", "", statement).strip()
        if len(clean_stmt) < 15:
            return

        id_match = cls.REQ_ID_PATTERN.search(statement)
        detected_id = id_match.group(0).upper() if id_match else None
        contains_modal = bool(cls.MODAL_VERBS_PATTERN.search(clean_stmt))

        # Only accept if it contains a modal verb or explicit ID
        if not contains_modal and not detected_id:
            return

        output_list.append({
            "raw_statement": clean_stmt,
            "section": section,
            "detected_id": detected_id,
            "contains_modal": contains_modal,
            "is_req_section": True
        })
