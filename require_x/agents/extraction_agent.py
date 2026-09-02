"""
REQUIRE-X: Requirement Extraction & Classification Agent
Extracts atomic requirements, assigns standard IDs, classifies FR vs NFR, and estimates complexity.
"""

import re
from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement


class RequirementExtractionAgent(BaseAgent):
    """Specialized Agent for extracting, classifying, and sizing Software Requirements."""

    NFR_KEYWORDS = {
        "Security": ["security", "authenticate", "authorization", "encrypt", "jwt", "tls", "oauth", "permission", "rbac", "password", "gdpr", "vulnerability"],
        "Performance": ["response time", "latency", "throughput", "concurrency", "second", "millisecond", "tps", "load", "bandwidth", "speed", "fast", "scale"],
        "Reliability": ["uptime", "availability", "99.9", "fault", "disaster recovery", "backup", "failover", "mtbf", "mttr", "redundancy"],
        "Usability": ["user interface", "ux", "accessibility", "wcag", "intuitive", "navigation", "screen", "mobile friendly", "responsive", "theme"],
        "Maintainability": ["modular", "clean code", "docker", "documentation", "logging", "telemetry", "test coverage", "ci/cd", "upgrade", "api versioning"],
        "Scalability": ["scale", "concurrent users", "horizontal", "elastic", "distributed", "cluster", "peak load", "partitioning"],
        "Compliance": ["iso", "ieee", "hipaa", "pci-dss", "audit", "regulatory", "standard", "legal"]
    }

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Requirement Extraction & Classification Agent",
            role="Extracts atomic requirements from SRS, classifies FR vs NFR, and estimates complexity",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting requirement extraction and classification...", "INFO")
        candidates = context.get("candidates", [])
        raw_text = context.get("raw_text", "")
        sections = context.get("sections", {})

        requirements: List[Requirement] = []

        # Attempt LLM-based extraction first if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for structured semantic extraction and classification...", "INFO")
            requirements = self._extract_with_llm(raw_text, sections)

        # If LLM returned empty or offline mode
        if not requirements:
            self.log("Executing deterministic NLP & Rule-Based extraction pipeline...", "INFO")
            requirements = self._extract_with_rules(candidates, sections, raw_text)

        self.log(
            f"Successfully extracted {len(requirements)} requirements "
            f"({sum(1 for r in requirements if r.req_type == 'Functional')} Functional, "
            f"{sum(1 for r in requirements if r.req_type == 'Non-Functional')} Non-Functional).",
            "SUCCESS"
        )
        context["requirements"] = requirements
        return context

    def _extract_with_llm(self, raw_text: str, sections: Dict[str, str]) -> List[Requirement]:
        """Extracts and classifies requirements using LLM."""
        system_prompt = (
            "You are a Senior Requirement Engineer and ISO/IEC/IEEE 29148:2018 expert. "
            "Analyze the provided SRS document and extract all atomic functional and non-functional requirements. "
            "Return a strictly valid JSON object with the key 'requirements', containing an array of requirement objects. "
            "Each object must have:\n"
            "- id: string (e.g. 'FR-001', 'FR-002', 'NFR-001')\n"
            "- title: string (concise title)\n"
            "- statement: string (complete requirement text starting with 'The system shall...')\n"
            "- req_type: 'Functional' or 'Non-Functional'\n"
            "- category: string ('Security', 'Performance', 'Usability', 'Reliability', 'Maintainability', 'Scalability', 'Data Management', 'Business Logic', or 'Compliance')\n"
            "- complexity: 'Low', 'Medium', or 'High'\n"
            "- story_points: integer (1, 2, 3, 5, 8, or 13)\n"
            "- complexity_rationale: string (technical justification)\n"
            "- acceptance_criteria: array of strings\n"
            "- priority: 'Must Have', 'Should Have', 'Could Have', or 'Won\'t Have'\n"
            "- source_section: string"
        )
        
        # Take up to 12,000 characters to fit standard context
        prompt_text = raw_text[:12000]
        user_prompt = f"Extract all atomic requirements from this SRS text:\n\n{prompt_text}"

        response_text = self.llm.generate(system_prompt, user_prompt, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "requirements" in data:
            req_list = []
            for item in data["requirements"]:
                try:
                    req_list.append(Requirement(**item))
                except Exception as e:
                    self.log(f"Skipping malformed requirement item: {e}", "WARNING")
            return req_list
        return []

    def _extract_with_rules(
        self, candidates: List[Dict[str, Any]], sections: Dict[str, str], raw_text: str
    ) -> List[Requirement]:
        """Deterministic rule-based extraction fallback."""
        requirements: List[Requirement] = []
        fr_counter = 1
        nfr_counter = 1

        seen_statements = set()

        for cand in candidates:
            stmt = cand["raw_statement"].strip()
            if not stmt or stmt in seen_statements:
                continue
            seen_statements.add(stmt)

            section = cand["section"]
            sec_lower = section.lower()
            stmt_lower = stmt.lower()

            # Determine FR vs NFR strictly based on section and context
            is_nfr = False
            detected_category = "Business Logic"

            if "non-functional" in sec_lower or "nfr" in sec_lower:
                is_nfr = True
                detected_category = "General Quality Attribute"
                for cat, keywords in self.NFR_KEYWORDS.items():
                    if any(kw in stmt_lower or kw in sec_lower for kw in keywords):
                        detected_category = cat
                        break
            elif "functional" in sec_lower or "fr" in sec_lower:
                is_nfr = False
                detected_category = self._classify_functional_category(stmt)
            else:
                # If section is generic, check keywords
                for cat, keywords in self.NFR_KEYWORDS.items():
                    if any(kw in stmt_lower for kw in keywords):
                        is_nfr = True
                        detected_category = cat
                        break
                if not is_nfr:
                    detected_category = self._classify_functional_category(stmt)

            # Assign ID
            if is_nfr:
                req_id = cand.get("detected_id") or f"NFR-{nfr_counter:03d}"
                nfr_counter += 1
                req_type = "Non-Functional"
            else:
                req_id = cand.get("detected_id") or f"FR-{fr_counter:03d}"
                fr_counter += 1
                req_type = "Functional"

            # Clean and normalize statement phrasing to IEEE 29148 standard ("The system shall...")
            normalized_stmt = self._normalize_statement(stmt)
            title = self._generate_title(clean_stmt=stmt, category=detected_category, req_id=req_id)
            complexity, story_points, rationale = self._estimate_complexity(stmt, detected_category, is_nfr)
            acceptance = self._generate_acceptance_criteria(normalized_stmt, detected_category)
            priority = self._assign_priority(stmt, detected_category)

            req = Requirement(
                id=req_id,
                title=title,
                statement=normalized_stmt,
                req_type=req_type,
                category=detected_category,
                complexity=complexity,
                story_points=story_points,
                complexity_rationale=rationale,
                acceptance_criteria=acceptance,
                priority=priority,
                source_section=section
            )
            requirements.append(req)

        # If no candidates parsed, fallback to splitting raw text by line
        if not requirements:
            requirements = self._fallback_raw_split(raw_text)

        return requirements

    def _classify_functional_category(self, stmt: str) -> str:
        s = stmt.lower()
        if any(k in s for k in ["auth", "login", "signup", "role", "user", "profile"]):
            return "User Management & Auth"
        if any(k in s for k in ["payment", "checkout", "billing", "invoice", "price"]):
            return "Payment & Billing"
        if any(k in s for k in ["report", "analytics", "dashboard", "metric", "chart"]):
            return "Reporting & Analytics"
        if any(k in s for k in ["notify", "alert", "email", "sms", "push"]):
            return "Notifications"
        if any(k in s for k in ["database", "store", "persist", "archive", "export", "import"]):
            return "Data Management"
        if any(k in s for k in ["api", "integration", "webhook", "sync", "service"]):
            return "System Integration"
        return "Core Business Logic"

    def _normalize_statement(self, stmt: str) -> str:
        s = stmt.strip()
        # Remove any leading ID prefix like "FR-001:" or "NFR-002: Security -"
        s = re.sub(r"^(?:(?:REQ|FR|NFR|BR|SR|SYS|USE|UC)[\-_]?\d+(?:\.\d+)*\s*[\:\-\.]\s*(?:[A-Za-z\s]+[\-\:])?\s*)", "", s, flags=re.IGNORECASE).strip()
        if not re.search(r"\b(?:shall|must|should)\b", s, re.IGNORECASE):
            s = f"The system shall {s[0].lower() + s[1:] if len(s) > 1 else s}"
        return s

    def _generate_title(self, clean_stmt: str, category: str, req_id: str) -> str:
        # Strip ID prefix and category label if present
        clean = re.sub(r"^(?:(?:REQ|FR|NFR|BR|SR|SYS|USE|UC)[\-_]?\d+(?:\.\d+)*\s*[\:\-\.]\s*(?:[A-Za-z\s]+[\-\:])?\s*)", "", clean_stmt, flags=re.IGNORECASE).strip()
        # Remove "The system shall" / "The application should" prefix
        shortened = re.sub(r"^(?:the system shall|the system must|the application should|the system should|system shall)\s+", "", clean, flags=re.IGNORECASE).strip()
        words = shortened.split()
        if len(words) <= 6:
            return shortened.capitalize().rstrip(".:;")
        title_words = words[:6]
        return " ".join(title_words).capitalize().rstrip(".:;")

    def _estimate_complexity(self, stmt: str, category: str, is_nfr: bool) -> (str, int, str):
        stmt_lower = stmt.lower()
        word_count = len(stmt.split())

        high_indicators = ["real-time", "distributed", "ai", "machine learning", "failover", "multi-region", "biometric", "blockchain", "encryption at rest and transit", "streaming"]
        low_indicators = ["display", "view", "show", "label", "button", "static", "help text", "read-only"]

        if any(k in stmt_lower for k in high_indicators) or word_count > 35:
            return "High", 8, "Involves advanced architectural synchronization, external integrations, or high concurrency constraints."
        elif any(k in stmt_lower for k in low_indicators) and word_count < 15:
            return "Low", 2, "Standard UI presentation or basic CRUD operation with minimal business logic."
        else:
            return "Medium", 3, "Standard business domain logic requiring database interaction, validation, and unit test coverage."

    def _generate_acceptance_criteria(self, stmt: str, category: str) -> List[str]:
        return [
            f"Verify that system successfully executes: '{stmt[:60]}...'",
            f"Verify error handling and validation for invalid inputs or failure states.",
            f"Verify compliance with {category} operational specifications and telemetry logging."
        ]

    def _assign_priority(self, stmt: str, category: str) -> str:
        s = stmt.lower()
        if "must" in s or "shall" in s or category in ["Security", "Reliability"]:
            return "Must Have"
        if "should" in s or category in ["Performance", "Scalability"]:
            return "Should Have"
        if "could" in s or "optional" in s:
            return "Could Have"
        return "Must Have"

    def _fallback_raw_split(self, raw_text: str) -> List[Requirement]:
        """Simple line-by-line fallback if document had unconventional formatting."""
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 20]
        reqs = []
        for i, line in enumerate(lines[:15], 1):
            reqs.append(Requirement(
                id=f"FR-{i:03d}",
                title=f"Requirement {i}",
                statement=f"The system shall {line}",
                req_type="Functional",
                category="Core Business Logic",
                complexity="Medium",
                story_points=3,
                complexity_rationale="Derived from basic document parsing.",
                acceptance_criteria=[f"System passes validation for Requirement {i}"],
                priority="Must Have",
                source_section="General"
            ))
        return reqs
