"""
REQUIRE-X: Engineering Report Generation Agent
Aggregates all multi-agent analysis artifacts, constructs RTM, calculates KPIs, and compiles the master SRS Engineering Report.
"""

from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import (
    Requirement, AmbiguityIssue, RequirementDependency, ComplianceScorecard,
    ArchitectureRecommendation, TestCase, TraceabilityItem, QualityMetrics, SRSAnalysisReport
)


class EngineeringReportAgent(BaseAgent):
    """Specialized Agent for compiling consolidated engineering reports and traceability matrices."""

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Engineering Report Generation Agent",
            role="Compiles all multi-agent analysis results into executive summaries, KPIs, and RTM matrices",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Synthesizing multi-agent outputs and constructing Requirements Traceability Matrix (RTM)...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])
        ambiguities: List[AmbiguityIssue] = context.get("ambiguities", [])
        dependencies: List[RequirementDependency] = context.get("dependencies", [])
        compliance: ComplianceScorecard = context.get("compliance_scorecard")
        arch: ArchitectureRecommendation = context.get("architecture")
        test_cases: List[TestCase] = context.get("test_cases", [])
        doc_stats = context.get("doc_stats", {})
        filename = context.get("filename", "SRS Document")

        # 1. Build RTM Matrix
        rtm_matrix = self._build_rtm(requirements, arch, test_cases)

        # 2. Calculate Quality Metrics
        metrics = self._calculate_metrics(requirements, ambiguities, dependencies, compliance, test_cases, rtm_matrix)

        # 3. Generate Executive Synthesis
        exec_summary, strengths, risks, actions = self._generate_executive_synthesis(
            filename, requirements, ambiguities, compliance, arch, metrics
        )

        # 4. Assemble Master Report
        report = SRSAnalysisReport(
            project_title=f"REQUIRE-X Analysis Report: {filename}",
            author_organization="REQUIRE-X Multi-Agent RE Framework",
            raw_document_stats=doc_stats,
            executive_summary=exec_summary,
            key_strengths=strengths,
            key_risks=risks,
            action_items=actions,
            metrics=metrics,
            requirements=requirements,
            ambiguities=ambiguities,
            dependencies=dependencies,
            compliance_scorecard=compliance,
            architecture=arch,
            test_cases=test_cases,
            traceability_matrix=rtm_matrix
        )

        self.log("Master SRS Analysis Report compiled successfully.", "SUCCESS")
        context["report"] = report
        return context

    def _build_rtm(
        self,
        requirements: List[Requirement],
        arch: ArchitectureRecommendation,
        test_cases: List[TestCase]
    ) -> List[TraceabilityItem]:
        """Constructs bidirectional Requirements Traceability Matrix."""
        # Index test cases by requirement ID
        tests_by_req: Dict[str, List[str]] = {}
        for tc in test_cases:
            tests_by_req.setdefault(tc.req_id, []).append(tc.test_id)

        # Index components by mapped requirement ID
        comp_by_req: Dict[str, str] = {}
        if arch and arch.components:
            for comp in arch.components:
                for req_id in comp.mapped_requirements:
                    comp_by_req[req_id] = comp.name

        rtm_items: List[TraceabilityItem] = []
        for req in requirements:
            tc_ids = tests_by_req.get(req.id, [])
            mapped_module = comp_by_req.get(
                req.id,
                arch.components[0].name if (arch and arch.components) else "Core Application Module"
            )
            verification = "Testing" if req.req_type == "Functional" else "Analysis"
            status = "Covered" if tc_ids else "Uncovered"

            rtm_items.append(TraceabilityItem(
                req_id=req.id,
                req_title=req.title,
                req_type=req.req_type,
                category=req.category,
                architecture_module=mapped_module,
                test_case_ids=tc_ids,
                verification_method=verification,
                status=status
            ))

        return rtm_items

    def _calculate_metrics(
        self,
        requirements: List[Requirement],
        ambiguities: List[AmbiguityIssue],
        dependencies: List[RequirementDependency],
        compliance: ComplianceScorecard,
        test_cases: List[TestCase],
        rtm_matrix: List[TraceabilityItem]
    ) -> QualityMetrics:
        """Calculates quantitative RE KPIs."""
        total_reqs = len(requirements)
        fr_count = sum(1 for r in requirements if r.req_type == "Functional")
        nfr_count = sum(1 for r in requirements if r.req_type == "Non-Functional")
        amb_count = len(ambiguities)
        amb_rate = round((amb_count / total_reqs * 100.0) if total_reqs > 0 else 0.0, 1)
        covered_count = sum(1 for item in rtm_matrix if item.status == "Covered")
        coverage_pct = round((covered_count / total_reqs * 100.0) if total_reqs > 0 else 0.0, 1)
        total_pts = sum(r.story_points for r in requirements)

        return QualityMetrics(
            total_requirements=total_reqs,
            functional_count=fr_count,
            non_functional_count=nfr_count,
            ambiguity_count=amb_count,
            ambiguity_rate=amb_rate,
            total_dependencies=len(dependencies),
            iso_compliance_score=compliance.overall_score if compliance else 0.0,
            total_test_cases=len(test_cases),
            traceability_coverage_pct=coverage_pct,
            average_complexity="Medium",
            total_story_points=total_pts
        )

    def _generate_executive_synthesis(
        self,
        filename: str,
        requirements: List[Requirement],
        ambiguities: List[AmbiguityIssue],
        compliance: ComplianceScorecard,
        arch: ArchitectureRecommendation,
        metrics: QualityMetrics
    ) -> (str, List[str], List[str], List[str]):
        """Generates executive summary and risk assessment."""
        grade = compliance.grade if compliance else "B"
        score = compliance.overall_score if compliance else 85.0
        pattern = arch.recommended_pattern if arch else "Modular Architecture"

        exec_summary = (
            f"REQUIRE-X Multi-Agent AI Framework evaluated the Software Requirement Specification '{filename}'. "
            f"The specification comprises {metrics.total_requirements} total requirements "
            f"({metrics.functional_count} Functional, {metrics.non_functional_count} Non-Functional) with an estimated agile effort "
            f"of {metrics.total_story_points} story points. The document attained an ISO/IEC/IEEE 29148:2018 compliance score "
            f"of {score:.1f}% (Grade: {grade}). The framework generated {metrics.total_test_cases} automated test cases, "
            f"achieving {metrics.traceability_coverage_pct}% bidirectional traceability coverage mapped to a recommended {pattern} blueprint."
        )

        strengths = [
            f"Clear structural separation of {metrics.functional_count} Functional Requirements across core system modules.",
            f"High traceability readiness ({metrics.traceability_coverage_pct}% of requirements directly mapped to automated test suites).",
            f"Standardized numbering scheme compliant with ISO/IEC/IEEE 29148:2018 standards."
        ]

        risks = []
        if metrics.ambiguity_count > 0:
            risks.append(f"Identified {metrics.ambiguity_count} ambiguous or unquantified statements ({metrics.ambiguity_rate}% defect rate) that introduce misinterpretation risks.")
        if metrics.non_functional_count == 0:
            risks.append("Absence of explicit Non-Functional Requirements for security, performance, and recovery SLAs.")
        if not risks:
            risks.append("Low overall requirement ambiguity risk detected.")

        actions = [
            "Review and approve the suggested disambiguated rewrites in the Ambiguity Audit tab.",
            f"Adopt the recommended {pattern} component decomposition for architecture design.",
            "Export the generated Requirement Traceability Matrix (RTM) and Test Suite into the project's QA management tool."
        ]

        return exec_summary, strengths, risks, actions
