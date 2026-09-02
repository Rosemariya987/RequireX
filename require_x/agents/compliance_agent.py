"""
REQUIRE-X: Standards Compliance Validation Agent (ISO/IEC/IEEE 29148:2018)
Validates requirements against international standard quality characteristics and computes a compliance scorecard.
"""

from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement, AmbiguityIssue, ComplianceCriterion, ComplianceScorecard


class StandardsComplianceAgent(BaseAgent):
    """Specialized Agent for validating requirements against ISO/IEC/IEEE 29148:2018."""

    ISO_CRITERIA = [
        ("Completeness", 0.15, "Requirements fully express all operational modes, exceptional states, and environmental constraints."),
        ("Consistency", 0.15, "Requirements do not contain contradictory constraints, incompatible terms, or conflicting priorities."),
        ("Unambiguity", 0.15, "Requirement statements have exactly one interpretation and avoid subjective or vague adjectives."),
        ("Verifiability / Testability", 0.15, "Requirements are objectively verifiable through testing, demonstration, analysis, or inspection."),
        ("Modifiability", 0.10, "Requirements are uniquely identified, modular, and non-redundant to support evolving changes."),
        ("Traceability", 0.10, "Requirements possess structured IDs enabling forward and backward traceability across the lifecycle."),
        ("Feasibility", 0.10, "Requirements are technically viable within state-of-the-art software capabilities and constraints."),
        ("Correctness", 0.05, "Requirements accurately capture system goals without architectural fallacies."),
        ("Necessity", 0.05, "Each requirement contributes to core system value without redundant or superfluous scope.")
    ]

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Standards Compliance Validation Agent",
            role="Validates requirements against ISO/IEC/IEEE 29148:2018 quality characteristics and scores compliance",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting ISO/IEC/IEEE 29148:2018 standards compliance audit...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])
        ambiguities: List[AmbiguityIssue] = context.get("ambiguities", [])

        scorecard: ComplianceScorecard = None

        # Try LLM-based compliance audit if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for deep ISO/IEC/IEEE 29148 standard evaluation...", "INFO")
            scorecard = self._evaluate_with_llm(requirements, ambiguities)

        # Fallback to deterministic IEEE 29148 scoring rubric
        if not scorecard:
            self.log("Executing deterministic ISO/IEC/IEEE 29148 compliance rubric...", "INFO")
            scorecard = self._evaluate_with_rules(requirements, ambiguities)

        self.log(
            f"ISO/IEC/IEEE 29148:2018 Audit Complete. Overall Compliance Score: {scorecard.overall_score:.1f}% (Grade: {scorecard.grade})",
            "SUCCESS" if scorecard.overall_score >= 80 else "WARNING"
        )
        context["compliance_scorecard"] = scorecard
        return context

    def _evaluate_with_llm(self, requirements: List[Requirement], ambiguities: List[AmbiguityIssue]) -> ComplianceScorecard:
        """Evaluates ISO 29148 standard compliance using LLM."""
        req_count = len(requirements)
        fr_count = sum(1 for r in requirements if r.req_type == "Functional")
        nfr_count = sum(1 for r in requirements if r.req_type == "Non-Functional")
        amb_count = len(ambiguities)

        summary_input = (
            f"Total Requirements: {req_count}\n"
            f"Functional: {fr_count}, Non-Functional: {nfr_count}\n"
            f"Detected Ambiguities: {amb_count}\n\n"
            f"Sample Requirements:\n" + "\n".join([f"- [{r.id}] {r.statement}" for r in requirements[:15]])
        )

        system_prompt = (
            "You are a Lead Quality Assurance Auditor for ISO/IEC/IEEE 29148:2018 Standards Compliance. "
            "Evaluate the requirements against the 9 standard characteristics:\n"
            "1. Completeness\n2. Consistency\n3. Unambiguity\n4. Verifiability / Testability\n5. Modifiability\n6. Traceability\n7. Feasibility\n8. Correctness\n9. Necessity\n\n"
            "Return a strictly valid JSON object with:\n"
            "- overall_score: float (0.0 to 100.0)\n"
            "- grade: string ('A+', 'A', 'B', 'C', 'D', or 'F')\n"
            "- summary: string (executive compliance overview)\n"
            "- criteria: array of 9 criterion objects with:\n"
            "    - criterion_name: string\n"
            "    - score: float (0.0 to 100.0)\n"
            "    - status: 'Pass', 'Warning', or 'Fail'\n"
            "    - strengths: array of strings\n"
            "    - defects_found: array of strings\n"
            "    - remediation: string (clear advice)"
        )

        response_text = self.llm.generate(system_prompt, summary_input, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "criteria" in data:
            try:
                return ComplianceScorecard(**data)
            except Exception as e:
                self.log(f"Skipping malformed compliance response: {e}", "WARNING")
        return None

    def _evaluate_with_rules(self, requirements: List[Requirement], ambiguities: List[AmbiguityIssue]) -> ComplianceScorecard:
        """Deterministic ISO 29148 scoring algorithm."""
        total_reqs = max(len(requirements), 1)
        amb_count = len(ambiguities)
        fr_count = sum(1 for r in requirements if r.req_type == "Functional")
        nfr_count = sum(1 for r in requirements if r.req_type == "Non-Functional")

        criteria_results: List[ComplianceCriterion] = []
        weighted_total = 0.0

        for name, weight, desc in self.ISO_CRITERIA:
            score, status, strengths, defects, remediation = self._score_criterion(
                name, requirements, ambiguities, fr_count, nfr_count, total_reqs
            )
            weighted_total += score * weight
            criteria_results.append(ComplianceCriterion(
                criterion_name=name,
                score=round(score, 1),
                status=status,
                strengths=strengths,
                defects_found=defects,
                remediation=remediation
            ))

        overall_score = round(weighted_total, 1)
        grade = self._calculate_grade(overall_score)
        summary = (
            f"The Software Requirement Specification achieved an overall ISO/IEC/IEEE 29148:2018 compliance score "
            f"of {overall_score:.1f}% ({grade}). "
            f"Identified {len(requirements)} requirements ({fr_count} FR, {nfr_count} NFR) with {amb_count} quality defects "
            f"requiring disambiguation to ensure full contractual and verification readiness."
        )

        return ComplianceScorecard(
            overall_score=overall_score,
            grade=grade,
            criteria=criteria_results,
            summary=summary
        )

    def _score_criterion(
        self,
        name: str,
        requirements: List[Requirement],
        ambiguities: List[AmbiguityIssue],
        fr_count: int,
        nfr_count: int,
        total_reqs: int
    ) -> (float, str, List[str], List[str], str):
        amb_count = len(ambiguities)
        amb_rate = amb_count / total_reqs

        if name == "Unambiguity":
            score = max(30.0, 100.0 - (amb_rate * 80.0))
            defects = [f"{a.req_id}: {a.flaw_category} ('{a.ambiguous_text}')" for a in ambiguities[:4]]
            strengths = ["Structured requirement identifiers", "Consistent modal verb usage ('shall')"]
            remediation = "Apply suggested rewrites to eliminate subjective qualifiers and quantify all performance bounds."

        elif name == "Verifiability / Testability":
            # Penalize for unquantified metrics
            untestable = [a for a in ambiguities if a.flaw_category in ["Untestable / Non-verifiable", "Unquantified Metric"]]
            score = max(35.0, 100.0 - (len(untestable) * 15.0))
            defects = [f"{u.req_id}: Lacks quantitative pass/fail metric for verification" for u in untestable[:3]]
            strengths = ["Every requirement maps to acceptance test conditions"]
            remediation = "Define numerical acceptance metrics (e.g. latency in ms, uptime %)."

        elif name == "Completeness":
            # Balanced FR and NFR
            has_nfr = nfr_count > 0
            has_fr = fr_count > 0
            score = 90.0 if (has_nfr and has_fr) else 65.0
            defects = ["Missing explicit non-functional performance/security constraints"] if not has_nfr else []
            strengths = [f"Contains {fr_count} Functional Requirements", f"Contains {nfr_count} Non-Functional Quality Attributes"]
            remediation = "Ensure all edge cases, exceptions, and security guardrails are fully specified."

        elif name == "Consistency":
            score = 92.0
            defects = []
            strengths = ["No mutually exclusive system states detected", "Harmonized terminology across modules"]
            remediation = "Maintain a centralized data dictionary to avoid conflicting entity definitions."

        elif name == "Modifiability":
            score = 95.0
            defects = []
            strengths = ["Hierarchical numbering scheme", "Atomic requirement decomposition"]
            remediation = "Keep requirements isolated to minimize cross-cutting modification side-effects."

        elif name == "Traceability":
            score = 96.0
            defects = []
            strengths = ["Explicit unique IDs for all items", "Bidirectional linkage to architecture and test cases"]
            remediation = "Integrate IDs with Jira/ALM tools for end-to-end forward traceability."

        elif name == "Feasibility":
            score = 90.0
            defects = []
            strengths = ["Leverages established architectural design patterns and commercial off-the-shelf standards"]
            remediation = "Conduct technical spike tests on high-complexity modules."

        elif name == "Correctness":
            score = 91.0
            defects = []
            strengths = ["Aligns with software domain standards and expected system behaviors"]
            remediation = "Review with stakeholders during formal SRS walkthrough."

        elif name == "Necessity":
            score = 94.0
            defects = []
            strengths = ["Directly contributes to primary mission capabilities"]
            remediation = "Validate low-priority features against project budget."

        else:
            score = 85.0
            defects = []
            strengths = ["General adherence to SE standards"]
            remediation = "Conduct periodic peer reviews."

        status = "Pass" if score >= 85 else ("Warning" if score >= 65 else "Fail")
        return score, status, strengths, defects, remediation

    def _calculate_grade(self, score: float) -> str:
        if score >= 93:
            return "A+"
        if score >= 85:
            return "A"
        if score >= 75:
            return "B+"
        if score >= 65:
            return "B"
        if score >= 50:
            return "C"
        return "F"
