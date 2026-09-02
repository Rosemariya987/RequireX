"""
REQUIRE-X: Ambiguity Detection Agent
Detects vague, ambiguous, inconsistent, untestable, or incomplete requirement statements and suggests ISO-compliant rewrites.
"""

import re
from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement, AmbiguityIssue


class AmbiguityDetectionAgent(BaseAgent):
    """Specialized Agent for detecting ambiguities, subjective terminology, and requirement defects."""

    VAGUE_TERMS = {
        "fast": ("Unquantified Metric", "The term 'fast' is subjective and untestable without defined latency/response time thresholds (e.g., '< 200ms at 95th percentile')."),
        "user-friendly": ("Subjective Language", "'User-friendly' cannot be objectively verified. Define specific usability criteria, such as task completion rate > 90% or SUS score > 80."),
        "easy to use": ("Subjective Language", "'Easy to use' lacks measurable criteria. Replace with maximum click depth or user training time bounds."),
        "robust": ("Vagueness / Weak Words", "'Robust' is non-verifiable. Specify precise fault tolerance, error handling, or recovery MTTR bounds."),
        "efficient": ("Vagueness / Weak Words", "'Efficient' lacks quantitative boundaries. Specify CPU/memory consumption limits or throughput targets."),
        "seamless": ("Subjective Language", "'Seamless' is a marketing buzzword. Detail exact API integration protocols and error mitigation."),
        "as appropriate": ("Incomplete Specification", "'As appropriate' introduces implementation ambiguity. Specify exact operational conditions."),
        "as needed": ("Incomplete Specification", "'As needed' leaves execution trigger undefined. Specify explicit trigger events."),
        "etc": ("Incomplete Specification", "Use of 'etc.' leaves requirement open-ended and incomplete. List all explicit options."),
        "and so on": ("Incomplete Specification", "Open-ended statement prevents complete test coverage. Enumerate all allowed inputs/states."),
        "high performance": ("Unquantified Metric", "Specify quantitative throughput (transactions/second) or concurrent connection targets."),
        "minimal delay": ("Unquantified Metric", "Quantify allowable latency bounds in milliseconds."),
        "sufficient": ("Vagueness / Weak Words", "Specify explicit capacity limits (e.g., storage in GB or records count)."),
        "tbd": ("Incomplete Specification", "Marked as To-Be-Determined (TBD), leaving requirement unfinished and unbuildable."),
        "flexible": ("Subjective Language", "'Flexible' cannot be verified by a QA test engineer. Define configuration parameters or plugin interfaces.")
    }

    PASSIVE_VOICE_PATTERN = re.compile(
        r"\b(?:is|are|was|were|be|been|being)\s+([a-z]+ed|[a-z]+en)\b", re.IGNORECASE
    )

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Ambiguity Detection Agent",
            role="Detects vague, ambiguous, incomplete, and non-verifiable requirement phrasings and proposes rewrites",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting ambiguity and defect inspection on extracted requirements...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])

        ambiguities: List[AmbiguityIssue] = []

        # Try LLM-based analysis if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for deep semantic ambiguity analysis...", "INFO")
            ambiguities = self._detect_with_llm(requirements)

        # Fallback to rule-based analysis
        if not ambiguities:
            self.log("Executing deterministic NLP heuristic ambiguity auditing...", "INFO")
            ambiguities = self._detect_with_rules(requirements)

        self.log(
            f"Detected {len(ambiguities)} potential ambiguities and quality issues across {len(requirements)} requirements.",
            "WARNING" if ambiguities else "SUCCESS"
        )
        context["ambiguities"] = ambiguities
        return context

    def _detect_with_llm(self, requirements: List[Requirement]) -> List[AmbiguityIssue]:
        """Detects ambiguities using LLM."""
        req_summaries = [
            f"[{r.id}] ({r.req_type} - {r.category}): {r.statement}"
            for r in requirements[:20]
        ]
        user_prompt = "Analyze these requirements for ambiguities, vague words, missing actors, untestable statements, and inconsistencies:\n\n" + "\n".join(req_summaries)

        system_prompt = (
            "You are an expert Requirements Quality Auditor specializing in ISO/IEC/IEEE 29148:2018. "
            "Identify all ambiguous, vague, untestable, or incomplete requirement phrasings. "
            "Return a strictly valid JSON object with the key 'ambiguities', containing an array of objects. "
            "Each object must have:\n"
            "- req_id: string (matching the requirement ID)\n"
            "- ambiguous_text: string (the problematic phrase)\n"
            "- flaw_category: one of ['Vagueness / Weak Words', 'Subjective Language', 'Unquantified Metric', 'Passive Voice / Missing Actor', 'Incomplete Specification', 'Untestable / Non-verifiable', 'Contradiction / Inconsistency']\n"
            "- severity: 'Critical', 'Warning', or 'Minor'\n"
            "- explanation: string (why it is problematic)\n"
            "- suggested_rewrite: string (clear, measurable, ISO-compliant rewrite)"
        )

        response_text = self.llm.generate(system_prompt, user_prompt, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "ambiguities" in data:
            issues = []
            for item in data["ambiguities"]:
                try:
                    issues.append(AmbiguityIssue(**item))
                except Exception as e:
                    self.log(f"Skipping malformed ambiguity item: {e}", "WARNING")
            return issues
        return []

    def _detect_with_rules(self, requirements: List[Requirement]) -> List[AmbiguityIssue]:
        """Deterministic NLP rule-based ambiguity detection."""
        ambiguities: List[AmbiguityIssue] = []

        for req in requirements:
            stmt = req.statement
            stmt_lower = stmt.lower()

            # 1. Check for known vague / subjective keywords
            for term, (cat, expl) in self.VAGUE_TERMS.items():
                pattern = r"\b" + re.escape(term) + r"\b"
                match = re.search(pattern, stmt_lower)
                if match:
                    # Formulate rewrite
                    rewrite = self._generate_rule_rewrite(req, term, cat)
                    severity = "Critical" if cat in ["Incomplete Specification", "Untestable / Non-verifiable"] else "Warning"

                    ambiguities.append(AmbiguityIssue(
                        req_id=req.id,
                        ambiguous_text=term,
                        flaw_category=cat,
                        severity=severity,
                        explanation=expl,
                        suggested_rewrite=rewrite
                    ))

            # 2. Check for passive voice without clear actor
            passive_match = self.PASSIVE_VOICE_PATTERN.search(stmt)
            if passive_match and not any(a.req_id == req.id for a in ambiguities):
                snippet = passive_match.group(0)
                ambiguities.append(AmbiguityIssue(
                    req_id=req.id,
                    ambiguous_text=snippet,
                    flaw_category="Passive Voice / Missing Actor",
                    severity="Minor",
                    explanation=f"Passive construct '{snippet}' obscures the system actor responsible for the action.",
                    suggested_rewrite=f"The System shall explicitly execute the action rather than stating '{snippet}'."
                ))

            # 3. Check for overly short or generic requirements
            if len(stmt.split()) < 6 and not any(a.req_id == req.id for a in ambiguities):
                ambiguities.append(AmbiguityIssue(
                    req_id=req.id,
                    ambiguous_text=stmt,
                    flaw_category="Incomplete Specification",
                    severity="Warning",
                    explanation="Statement is excessively brief and lacks input preconditions or expected measurable output state.",
                    suggested_rewrite=f"{stmt.rstrip('.')} with specific input validation parameters and return status codes."
                ))

        return ambiguities

    def _generate_rule_rewrite(self, req: Requirement, term: str, category: str) -> str:
        """Generates a concrete, quantifiable rewrite based on detected flaw."""
        stmt = req.statement
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)

        if term == "fast":
            return pattern.sub("within 250 milliseconds under peak concurrent load of 1,000 requests/sec", stmt)
        elif term in ["user-friendly", "easy to use"]:
            return pattern.sub("conformant with WCAG 2.1 AA guidelines and enabling task completion in <= 3 user clicks", stmt)
        elif term == "robust":
            return pattern.sub("fault-tolerant with automated retry logic and 99.95% error-free transaction processing", stmt)
        elif term == "efficient":
            return pattern.sub("consuming no more than 512MB RAM and 20% CPU utilization during normal operation", stmt)
        elif term == "seamless":
            return pattern.sub("using authenticated RESTful JSON APIs with automatic token refresh", stmt)
        elif term in ["as appropriate", "as needed"]:
            return pattern.sub("upon detecting a validated user trigger event", stmt)
        elif term in ["etc", "and so on"]:
            return pattern.sub("including all documented supported file types (.pdf, .docx, .txt)", stmt)
        elif term == "high performance":
            return pattern.sub("supporting at least 500 concurrent transactions per second with < 500ms latency", stmt)
        elif term == "minimal delay":
            return pattern.sub("within a maximum threshold of 100 milliseconds", stmt)
        elif term == "sufficient":
            return pattern.sub("a minimum capacity of 100 GB of dedicated NVMe storage", stmt)
        elif term == "flexible":
            return pattern.sub("configurable via an externalized JSON/YAML settings file without system recompilation", stmt)
        else:
            return f"{stmt} [Quantified: specified with measurable tolerance bounds and ISO 29148 compliance]."
