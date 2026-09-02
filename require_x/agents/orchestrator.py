"""
REQUIRE-X: Coordinator & Multi-Agent Orchestrator
Orchestrates the collaborative multi-agent execution workflow for end-to-end Requirements Engineering analysis.
"""

from typing import Dict, Any, List, Optional, Callable
from require_x.ingestion.parser import DocumentParser
from require_x.ingestion.preprocessor import TextPreprocessor
from require_x.agents.llm_provider import LLMProvider
from require_x.agents.extraction_agent import RequirementExtractionAgent
from require_x.agents.ambiguity_agent import AmbiguityDetectionAgent
from require_x.agents.dependency_agent import DependencyAnalysisAgent
from require_x.agents.compliance_agent import StandardsComplianceAgent
from require_x.agents.architecture_agent import ArchitectureRecommendationAgent
from require_x.agents.test_generation_agent import TestCaseGenerationAgent
from require_x.agents.report_agent import EngineeringReportAgent
from require_x.models.schema import SRSAnalysisReport


class MultiAgentOrchestrator:
    """Coordinator Agent that orchestrates specialized AI agents in the REQUIRE-X pipeline."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        on_step_progress: Optional[Callable[[str, int, int, str], None]] = None,
        on_agent_log: Optional[Callable[[str, str, str], None]] = None
    ):
        self.llm = llm_provider or LLMProvider(provider="auto")
        self.on_step_progress = on_step_progress
        self.on_agent_log = on_agent_log

        # Initialize specialized agents
        self.extraction_agent = RequirementExtractionAgent(self.llm, self.on_agent_log)
        self.ambiguity_agent = AmbiguityDetectionAgent(self.llm, self.on_agent_log)
        self.dependency_agent = DependencyAnalysisAgent(self.llm, self.on_agent_log)
        self.compliance_agent = StandardsComplianceAgent(self.llm, self.on_agent_log)
        self.architecture_agent = ArchitectureRecommendationAgent(self.llm, self.on_agent_log)
        self.test_agent = TestCaseGenerationAgent(self.llm, self.on_agent_log)
        self.report_agent = EngineeringReportAgent(self.llm, self.on_agent_log)

    def analyze_document(self, file_path_or_buffer, filename: str) -> SRSAnalysisReport:
        """Runs the complete end-to-end Multi-Agent analysis on an uploaded SRS document."""
        total_steps = 7

        # Step 0: Ingestion & Parsing
        self._notify_progress("Ingesting and parsing SRS document...", 0, total_steps, "INGESTION")
        parsed = DocumentParser.parse_file(file_path_or_buffer, filename)
        raw_text = parsed["raw_text"]
        sections = parsed["sections"]
        stats = parsed["stats"]

        candidates = TextPreprocessor.preprocess_text(raw_text, sections)

        context: Dict[str, Any] = {
            "filename": filename,
            "raw_text": raw_text,
            "sections": sections,
            "doc_stats": stats,
            "candidates": candidates
        }

        # Step 1: Requirement Extraction & Classification
        self._notify_progress("Agent 1: Extracting and Classifying Requirements...", 1, total_steps, "EXTRACTION")
        context = self.extraction_agent.run(context)

        # Step 2: Ambiguity Detection
        self._notify_progress("Agent 2: Auditing Phrasings for Ambiguities & Defect Severity...", 2, total_steps, "AMBIGUITY")
        context = self.ambiguity_agent.run(context)

        # Step 3: Dependency Analysis
        self._notify_progress("Agent 3: Mapping Inter-Requirement Dependencies & Constraints...", 3, total_steps, "DEPENDENCY")
        context = self.dependency_agent.run(context)

        # Step 4: ISO/IEC/IEEE 29148:2018 Standards Compliance Validation
        self._notify_progress("Agent 4: Validating against ISO/IEC/IEEE 29148:2018 Standard...", 4, total_steps, "COMPLIANCE")
        context = self.compliance_agent.run(context)

        # Step 5: Traceability & Architecture Recommendation
        self._notify_progress("Agent 5: Synthesizing Software Architecture Blueprint & Patterns...", 5, total_steps, "ARCHITECTURE")
        context = self.architecture_agent.run(context)

        # Step 6: Test Case Generation
        self._notify_progress("Agent 6: Generating Functional & Non-Functional Test Suites...", 6, total_steps, "TEST_GEN")
        context = self.test_agent.run(context)

        # Step 7: Engineering Report Generation
        self._notify_progress("Agent 7: Compiling Master SRS Engineering Report & RTM Matrix...", 7, total_steps, "REPORT")
        context = self.report_agent.run(context)

        self._notify_progress("Multi-Agent Analysis Pipeline Completed Successfully!", 7, total_steps, "COMPLETE")
        return context["report"]

    def _notify_progress(self, message: str, current_step: int, total_steps: int, stage_code: str):
        if self.on_step_progress:
            self.on_step_progress(message, current_step, total_steps, stage_code)
