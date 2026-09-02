"""
REQUIRE-X: Verification & Demo Execution Script
Runs the complete multi-agent pipeline on benchmark SRS documents and generates sample PDF/JSON/Markdown outputs.
"""

import os
from require_x.agents.llm_provider import LLMProvider
from require_x.agents.orchestrator import MultiAgentOrchestrator
from require_x.reporting.pdf_exporter import PDFReportGenerator
from require_x.reporting.json_exporter import JSONReportExporter, MarkdownReportExporter


def run_demo():
    print("=" * 70)
    print("REQUIRE-X: Multi-Agent AI Framework for Requirement Engineering")
    print("=" * 70)

    sample_dir = os.path.join(os.path.dirname(__file__), "samples")
    files = ["healthcare_srs.txt", "ecommerce_srs.txt"]

    os.makedirs("output_demo", exist_ok=True)

    for filename in files:
        filepath = os.path.join(sample_dir, filename)
        print(f"\n[DEMO] Processing '{filename}'...")

        def log_step(msg, cur, total, code):
            print(f"  [{cur}/{total}] {code}: {msg}")

        def log_agent(agent_name, level, msg):
            print(f"    - [{agent_name}] {msg}")

        llm = LLMProvider(provider="offline")
        orchestrator = MultiAgentOrchestrator(
            llm_provider=llm,
            on_step_progress=log_step,
            on_agent_log=log_agent
        )

        with open(filepath, "r", encoding="utf-8") as f:
            report = orchestrator.analyze_document(f, filename)

        print("\n  >> ANALYSIS SUMMARY:")
        print(f"     Total Requirements: {report.metrics.total_requirements} (FR: {report.metrics.functional_count}, NFR: {report.metrics.non_functional_count})")
        print(f"     ISO 29148 Compliance Score: {report.metrics.iso_compliance_score:.1f}% (Grade: {report.compliance_scorecard.grade})")
        print(f"     Ambiguities Detected: {report.metrics.ambiguity_count} ({report.metrics.ambiguity_rate:.1f}% defect rate)")
        print(f"     Architecture Recommendation: {report.architecture.recommended_pattern}")
        print(f"     Test Cases Synthesized: {report.metrics.total_test_cases}")
        print(f"     Traceability Coverage: {report.metrics.traceability_coverage_pct:.1f}%")

        # Export PDF
        pdf_bytes = PDFReportGenerator.generate_pdf_bytes(report)
        pdf_path = os.path.join("output_demo", f"{filename}_report.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"     [+] Exported PDF: {pdf_path} ({len(pdf_bytes):,} bytes)")

        # Export JSON
        json_path = os.path.join("output_demo", f"{filename}_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(JSONReportExporter.to_json_str(report))
        print(f"     [+] Exported JSON: {json_path}")

        # Export Markdown
        md_path = os.path.join("output_demo", f"{filename}_report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(MarkdownReportExporter.to_markdown(report))
        print(f"     [+] Exported Markdown: {md_path}")

    print("\n" + "=" * 70)
    print("ALL DEMO ANALYSES AND EXPORTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
