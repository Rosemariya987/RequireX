"""
Tests for REQUIRE-X Multi-Agent Pipeline & End-to-End Orchestrator
"""
import io
import os
import unittest
from require_x.agents.llm_provider import LLMProvider
from require_x.agents.orchestrator import MultiAgentOrchestrator
from require_x.reporting.pdf_exporter import PDFReportGenerator
from require_x.reporting.json_exporter import JSONReportExporter, MarkdownReportExporter


class TestPipeline(unittest.TestCase):
    def test_full_offline_pipeline(self):
        sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "healthcare_srs.txt")
        with open(sample_path, "r", encoding="utf-8") as f:
            text = f.read()

        llm = LLMProvider(provider="offline")
        orchestrator = MultiAgentOrchestrator(llm_provider=llm)

        buffer = io.StringIO(text)
        report = orchestrator.analyze_document(buffer, "healthcare_srs.txt")

        self.assertIsNotNone(report)
        self.assertGreater(len(report.requirements), 0)
        self.assertGreater(report.metrics.functional_count, 0)
        self.assertGreater(report.metrics.iso_compliance_score, 0)
        self.assertIn(report.compliance_scorecard.grade, ["A+", "A", "B+", "B", "C", "D", "F"])
        self.assertGreater(len(report.test_cases), 0)
        self.assertGreater(len(report.traceability_matrix), 0)
        self.assertNotEqual(report.architecture.recommended_pattern, "")

        # Test PDF Generation
        pdf_bytes = PDFReportGenerator.generate_pdf_bytes(report)
        self.assertGreater(len(pdf_bytes), 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Test JSON and Markdown Exporters
        json_out = JSONReportExporter.to_json_str(report)
        self.assertIn("requirements", json_out)

        md_out = MarkdownReportExporter.to_markdown(report)
        self.assertIn("# REQUIRE-X", md_out)


if __name__ == "__main__":
    unittest.main()
