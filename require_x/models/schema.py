"""
REQUIRE-X: Data Models and Pydantic Schemas
Defines core data structures for requirements, agent outputs, compliance metrics, and reports.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import datetime


class Requirement(BaseModel):
    """Represents an atomic Software Requirement."""
    id: str = Field(..., description="Unique identifier (e.g. FR-001, NFR-002)")
    title: str = Field(..., description="Short descriptive title of the requirement")
    statement: str = Field(..., description="The full requirement statement text")
    req_type: Literal["Functional", "Non-Functional"] = Field(
        ..., description="Classification as Functional (FR) or Non-Functional (NFR)"
    )
    category: str = Field(
        "General",
        description="Subcategory (e.g., Security, Performance, Usability, Reliability, Data Management, Business Logic)"
    )
    complexity: Literal["Low", "Medium", "High"] = Field(
        "Medium", description="Estimated implementation complexity"
    )
    story_points: int = Field(3, description="Estimated agile story points (1, 2, 3, 5, 8, 13)")
    complexity_rationale: str = Field("", description="Justification for the complexity rating")
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="Measurable acceptance criteria / test conditions"
    )
    priority: Literal["Must Have", "Should Have", "Could Have", "Won't Have"] = Field(
        "Must Have", description="MoSCoW priority"
    )
    source_section: Optional[str] = Field(None, description="Original document section where requirement was found")


class AmbiguityIssue(BaseModel):
    """Represents an identified ambiguity, inconsistency, or quality defect in a requirement."""
    req_id: str = Field(..., description="Associated Requirement ID")
    ambiguous_text: str = Field(..., description="Specific ambiguous word, phrase, or sentence fragment")
    flaw_category: Literal[
        "Vagueness / Weak Words",
        "Subjective Language",
        "Unquantified Metric",
        "Passive Voice / Missing Actor",
        "Incomplete Specification",
        "Untestable / Non-verifiable",
        "Contradiction / Inconsistency"
    ] = Field(..., description="Type of requirement defect")
    severity: Literal["Critical", "Warning", "Minor"] = Field(
        "Warning", description="Defect severity impact"
    )
    explanation: str = Field(..., description="Why this phrasing causes ambiguity or misinterpretation")
    suggested_rewrite: str = Field(..., description="Disambiguated, testable ISO-compliant rewrite")


class RequirementDependency(BaseModel):
    """Represents a relationship or dependency between two requirements."""
    source_id: str = Field(..., description="Source Requirement ID")
    target_id: str = Field(..., description="Target Requirement ID")
    dependency_type: Literal[
        "depends_on",
        "conflicts_with",
        "extends",
        "triggers",
        "constrains"
    ] = Field(..., description="Type of relationship")
    description: str = Field(..., description="Explanation of why this dependency exists")


class ComplianceCriterion(BaseModel):
    """Evaluation against a specific ISO/IEC/IEEE 29148:2018 quality characteristic."""
    criterion_name: str = Field(
        ...,
        description="ISO 29148 criterion (Completeness, Consistency, Correctness, Unambiguity, Verifiability, Modifiability, Traceability, Feasibility, Necessity)"
    )
    score: float = Field(..., ge=0.0, le=100.0, description="Compliance score percentage (0 - 100)")
    status: Literal["Pass", "Warning", "Fail"] = Field(..., description="Status check")
    strengths: List[str] = Field(default_factory=list, description="Identified strong points")
    defects_found: List[str] = Field(default_factory=list, description="Specific non-compliance findings")
    remediation: str = Field(..., description="Actionable recommendation to achieve 100% compliance")


class ComplianceScorecard(BaseModel):
    """Overall ISO/IEC/IEEE 29148:2018 Standards Compliance Scorecard."""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted average compliance index")
    grade: str = Field("B+", description="Standard letter grade (A+, A, B, C, D, F)")
    criteria: List[ComplianceCriterion] = Field(default_factory=list, description="Detailed 9-criteria assessment")
    summary: str = Field(..., description="Executive compliance summary")


class ArchitecturalComponent(BaseModel):
    """Represents a recommended architectural component or service."""
    name: str = Field(..., description="Component or service name")
    component_type: str = Field(..., description="e.g., API Gateway, Service, Database, Event Bus, UI Layer")
    responsibility: str = Field(..., description="Core responsibility of this module")
    mapped_requirements: List[str] = Field(default_factory=list, description="Requirement IDs handled by this component")


class ArchitectureRecommendation(BaseModel):
    """Recommended software architecture pattern and implementation blueprint."""
    recommended_pattern: str = Field(
        ...,
        description="Primary architecture pattern (e.g. Microservices, Clean / Hexagonal Architecture, Event-Driven, Layered MVC)"
    )
    secondary_pattern: Optional[str] = Field(
        None, description="Complementary pattern (e.g. CQRS, Modular Monolith, BFF)"
    )
    rationale: str = Field(..., description="Detailed technical justification based on FRs and NFRs")
    tradeoffs_pros: List[str] = Field(default_factory=list, description="Key benefits")
    tradeoffs_cons: List[str] = Field(default_factory=list, description="Potential challenges & mitigation")
    components: List[ArchitecturalComponent] = Field(default_factory=list, description="Component decomposition")
    tech_stack_recommendation: Dict[str, str] = Field(
        default_factory=dict, description="Recommended technology stack (Backend, Frontend, DB, Message Queue, Security)"
    )
    mermaid_diagram: str = Field(..., description="Mermaid.js diagram representing architecture topology")


class TestCase(BaseModel):
    """Generated test case mapped to software requirements."""
    test_id: str = Field(..., description="Unique Test ID (e.g., TC-001)")
    req_id: str = Field(..., description="Mapped Requirement ID")
    title: str = Field(..., description="Test scenario title")
    test_type: Literal[
        "Functional", "Integration", "Security", "Performance", "Boundary / Edge Case", "Usability"
    ] = Field("Functional", description="Test classification")
    preconditions: str = Field(..., description="Preconditions required before execution")
    steps: List[str] = Field(default_factory=list, description="Step-by-step test instructions")
    test_data: str = Field("", description="Input test data")
    expected_result: str = Field(..., description="Expected system behavior / pass criterion")


class TraceabilityItem(BaseModel):
    """Traceability matrix link between requirement, architecture component, and test cases."""
    req_id: str = Field(..., description="Requirement ID")
    req_title: str = Field(..., description="Requirement Title")
    req_type: str = Field(..., description="FR or NFR")
    category: str = Field(..., description="Category")
    architecture_module: str = Field(..., description="Mapped Architectural Module")
    test_case_ids: List[str] = Field(default_factory=list, description="Associated Test Case IDs")
    verification_method: Literal["Testing", "Demonstration", "Inspection", "Analysis"] = Field(
        "Testing", description="ISO 29148 verification method"
    )
    status: Literal["Covered", "Partially Covered", "Uncovered"] = Field(
        "Covered", description="Traceability coverage status"
    )


class QualityMetrics(BaseModel):
    """Quantitative Software Requirement Engineering metrics."""
    total_requirements: int = 0
    functional_count: int = 0
    non_functional_count: int = 0
    ambiguity_count: int = 0
    ambiguity_rate: float = 0.0
    total_dependencies: int = 0
    iso_compliance_score: float = 0.0
    total_test_cases: int = 0
    traceability_coverage_pct: float = 0.0
    average_complexity: str = "Medium"
    total_story_points: int = 0


class SRSAnalysisReport(BaseModel):
    """Consolidated master analysis report produced by the Multi-Agent Framework."""
    project_title: str = Field("REQUIRE-X SRS Analysis", description="Extracted or designated project title")
    author_organization: Optional[str] = Field(None, description="Author or Organization name")
    analysis_timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    raw_document_stats: Dict[str, Any] = Field(default_factory=dict, description="Stats on pages, characters, paragraphs")
    executive_summary: str = Field(..., description="High-level executive summary of the SRS review")
    key_strengths: List[str] = Field(default_factory=list, description="Top positive findings in the SRS")
    key_risks: List[str] = Field(default_factory=list, description="Critical risks and shortcomings identified")
    action_items: List[str] = Field(default_factory=list, description="Recommended immediate next steps")
    metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    requirements: List[Requirement] = Field(default_factory=list)
    ambiguities: List[AmbiguityIssue] = Field(default_factory=list)
    dependencies: List[RequirementDependency] = Field(default_factory=list)
    compliance_scorecard: ComplianceScorecard = Field(
        default_factory=lambda: ComplianceScorecard(
            overall_score=0.0, grade="N/A", summary="Not evaluated", criteria=[]
        )
    )
    architecture: ArchitectureRecommendation = Field(
        default_factory=lambda: ArchitectureRecommendation(
            recommended_pattern="Modular Monolith",
            rationale="Default initial baseline",
            mermaid_diagram="graph TD\n  Client --> App"
        )
    )
    test_cases: List[TestCase] = Field(default_factory=list)
    traceability_matrix: List[TraceabilityItem] = Field(default_factory=list)
