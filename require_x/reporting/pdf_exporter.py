"""
REQUIRE-X PDF Report Generator
Generates publication-quality formal Engineering Reports using ReportLab.
"""

import io
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from require_x.models.schema import SRSAnalysisReport


class PDFReportGenerator:
    """Generates formal Software Requirement Engineering PDF Reports."""

    @classmethod
    def generate_pdf_bytes(cls, report: SRSAnalysisReport) -> bytes:
        """Compiles SRSAnalysisReport into a styled PDF document in memory."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom typography styles
        primary_color = colors.HexColor("#1e3a8a")   # Dark Navy
        secondary_color = colors.HexColor("#3b82f6") # Bright Blue
        dark_text = colors.HexColor("#1f2937")       # Charcoal
        light_bg = colors.HexColor("#f8fafc")

        title_style = ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=primary_color,
            alignment=0,
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            "CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=14
        )

        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=primary_color,
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        )

        h2_style = ParagraphStyle(
            "Heading2_Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=secondary_color,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            "Body_Custom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=dark_text,
            spaceAfter=6
        )

        cell_style = ParagraphStyle(
            "Cell_Custom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=dark_text
        )

        cell_bold = ParagraphStyle(
            "Cell_Bold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("REQUIRE-X ENGINEERING REPORT", title_style))
        story.append(Paragraph(
            f"<b>Project:</b> {report.project_title} &nbsp;|&nbsp; <b>Timestamp:</b> {report.analysis_timestamp} &nbsp;|&nbsp; <b>Framework:</b> Multi-Agent AI",
            subtitle_style
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=2, spaceAfter=10))

        # 2. Executive Summary
        story.append(Paragraph("1. Executive Summary", h1_style))
        story.append(Paragraph(report.executive_summary, body_style))

        # 3. KPI Metrics Summary Table
        story.append(Paragraph("2. Requirements Engineering Quality Metrics", h1_style))
        m = report.metrics
        kpi_data = [
            [
                Paragraph("<b>Metric</b>", cell_bold),
                Paragraph("<b>Value</b>", cell_bold),
                Paragraph("<b>Metric</b>", cell_bold),
                Paragraph("<b>Value</b>", cell_bold)
            ],
            [
                Paragraph("Total Requirements", cell_style),
                Paragraph(str(m.total_requirements), cell_style),
                Paragraph("ISO 29148 Compliance", cell_style),
                Paragraph(f"<b>{m.iso_compliance_score:.1f}% ({report.compliance_scorecard.grade})</b>", cell_style)
            ],
            [
                Paragraph("Functional Requirements (FR)", cell_style),
                Paragraph(str(m.functional_count), cell_style),
                Paragraph("Ambiguity Rate", cell_style),
                Paragraph(f"{m.ambiguity_rate:.1f}% ({m.ambiguity_count} flaws)", cell_style)
            ],
            [
                Paragraph("Non-Functional Requirements (NFR)", cell_style),
                Paragraph(str(m.non_functional_count), cell_style),
                Paragraph("Traceability Coverage", cell_style),
                Paragraph(f"{m.traceability_coverage_pct:.1f}%", cell_style)
            ],
            [
                Paragraph("Total Dependencies", cell_style),
                Paragraph(str(m.total_dependencies), cell_style),
                Paragraph("Estimated Story Points", cell_style),
                Paragraph(f"{m.total_story_points} pts", cell_style)
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[1.8 * inch, 1.2 * inch, 1.8 * inch, 1.2 * inch])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 10))

        # 4. ISO/IEC/IEEE 29148:2018 Standards Compliance Scorecard
        story.append(Paragraph("3. ISO/IEC/IEEE 29148:2018 Standards Compliance Audit", h1_style))
        iso_data = [
            [
                Paragraph("<b>ISO 29148 Characteristic</b>", cell_bold),
                Paragraph("<b>Score</b>", cell_bold),
                Paragraph("<b>Status</b>", cell_bold),
                Paragraph("<b>Remediation / Finding</b>", cell_bold)
            ]
        ]
        for c in report.compliance_scorecard.criteria:
            status_color = "#16a34a" if c.status == "Pass" else ("#ca8a04" if c.status == "Warning" else "#dc2626")
            iso_data.append([
                Paragraph(f"<b>{c.criterion_name}</b>", cell_style),
                Paragraph(f"{c.score:.0f}%", cell_style),
                Paragraph(f"<font color='{status_color}'><b>{c.status}</b></font>", cell_style),
                Paragraph(c.remediation, cell_style)
            ])

        iso_table = Table(iso_data, colWidths=[1.7 * inch, 0.7 * inch, 0.9 * inch, 2.7 * inch])
        iso_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(iso_table)
        story.append(Spacer(1, 10))

        # 5. Classified Requirements Table
        story.append(Paragraph("4. Classified Requirements Catalog", h1_style))
        req_data = [
            [
                Paragraph("<b>ID</b>", cell_bold),
                Paragraph("<b>Type</b>", cell_bold),
                Paragraph("<b>Category</b>", cell_bold),
                Paragraph("<b>Statement</b>", cell_bold),
                Paragraph("<b>Pts</b>", cell_bold)
            ]
        ]
        for r in report.requirements[:15]:
            req_data.append([
                Paragraph(f"<b>{r.id}</b>", cell_style),
                Paragraph(r.req_type, cell_style),
                Paragraph(r.category, cell_style),
                Paragraph(r.statement, cell_style),
                Paragraph(str(r.story_points), cell_style)
            ])

        req_table = Table(req_data, colWidths=[0.8 * inch, 0.9 * inch, 1.2 * inch, 2.7 * inch, 0.4 * inch])
        req_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(req_table)
        story.append(Spacer(1, 10))

        # 6. Ambiguity & Quality Defects
        if report.ambiguities:
            story.append(Paragraph("5. Ambiguity Detection & Disambiguation Rewrites", h1_style))
            amb_data = [
                [
                    Paragraph("<b>Req ID</b>", cell_bold),
                    Paragraph("<b>Defect Type</b>", cell_bold),
                    Paragraph("<b>Flawed Phrase / Explanation</b>", cell_bold),
                    Paragraph("<b>ISO Disambiguated Rewrite</b>", cell_bold)
                ]
            ]
            for a in report.ambiguities[:8]:
                amb_data.append([
                    Paragraph(f"<b>{a.req_id}</b>", cell_style),
                    Paragraph(f"<b>{a.flaw_category}</b><br/>({a.severity})", cell_style),
                    Paragraph(f"<i>'{a.ambiguous_text}'</i><br/>{a.explanation}", cell_style),
                    Paragraph(a.suggested_rewrite, cell_style)
                ])

            amb_table = Table(amb_data, colWidths=[0.8 * inch, 1.3 * inch, 2.0 * inch, 2.2 * inch])
            amb_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b91c1c")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(amb_table)
            story.append(Spacer(1, 10))

        # 7. Architecture Recommendation Blueprint
        story.append(Paragraph("6. Software Architecture Recommendation", h1_style))
        arch = report.architecture
        story.append(Paragraph(f"<b>Recommended Pattern:</b> {arch.recommended_pattern}", h2_style))
        story.append(Paragraph(f"<b>Rationale:</b> {arch.rationale}", body_style))
        
        # 8. Requirements Traceability Matrix (RTM)
        story.append(Paragraph("7. Requirements Traceability Matrix (RTM)", h1_style))
        rtm_data = [
            [
                Paragraph("<b>Req ID</b>", cell_bold),
                Paragraph("<b>Requirement Title</b>", cell_bold),
                Paragraph("<b>Architectural Module</b>", cell_bold),
                Paragraph("<b>Mapped Test Cases</b>", cell_bold),
                Paragraph("<b>Coverage</b>", cell_bold)
            ]
        ]
        for item in report.traceability_matrix[:12]:
            tc_str = ", ".join(item.test_case_ids) if item.test_case_ids else "None"
            rtm_data.append([
                Paragraph(f"<b>{item.req_id}</b>", cell_style),
                Paragraph(item.req_title, cell_style),
                Paragraph(item.architecture_module, cell_style),
                Paragraph(tc_str, cell_style),
                Paragraph(item.status, cell_style)
            ])

        rtm_table = Table(rtm_data, colWidths=[0.8 * inch, 1.8 * inch, 1.8 * inch, 1.1 * inch, 0.8 * inch])
        rtm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(rtm_table)
        story.append(Spacer(1, 10))

        # 9. Automated Test Cases Sample
        story.append(Paragraph("8. Synthesized Test Suite (Sample)", h1_style))
        for tc in report.test_cases[:4]:
            tc_text = (
                f"<b>{tc.test_id} [{tc.test_type}] &mdash; {tc.title}</b> (Maps to: {tc.req_id})<br/>"
                f"<b>Preconditions:</b> {tc.preconditions}<br/>"
                f"<b>Steps:</b> {' '.join(tc.steps)}<br/>"
                f"<b>Expected Result:</b> {tc.expected_result}"
            )
            story.append(Paragraph(tc_text, body_style))
            story.append(Spacer(1, 4))

        # Build PDF document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
