"""
REQUIRE-X: Multi-Agent AI Framework for Intelligent Software Requirement Engineering
Interactive Streamlit Dashboard & Engineering Workspace
Author: Rose Mariya Paul (TCR25MCA-2045), Guided by Maria Sofia S
Department of Computer Applications, Government Engineering College, Thrissur
"""

import os
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from require_x.models.schema import SRSAnalysisReport
from require_x.ingestion.parser import DocumentParser
from require_x.ingestion.srs_validator import assess_document_is_srs
from require_x.agents.llm_provider import LLMProvider
from require_x.agents.orchestrator import MultiAgentOrchestrator
from require_x.analytics.graph_builder import DependencyGraphBuilder
from require_x.analytics.metrics import MetricsAnalyzer
from require_x.reporting.pdf_exporter import PDFReportGenerator
from require_x.reporting.json_exporter import JSONReportExporter, MarkdownReportExporter

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), ".env")


def save_env_key(key: str, value: str):
    """Saves API key to local .env file for permanent persistence."""
    if not value:
        return
    os.environ[key] = value
    lines = []
    found = False
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# Configure Streamlit page
st.set_page_config(
    page_title="REQUIRE-X | Multi-Agent AI for Requirements Engineering",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4b5563;
        margin-bottom: 1.2rem;
    }
    .metric-box {
        background-color: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .badge-fr {
        background-color: #dbeafe;
        color: #1d4ed8;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-nfr {
        background-color: #f3e8ff;
        color: #7e22ce;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-critical {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-pass {
        background-color: #dcfce7;
        color: #15803d;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


def load_sample_file(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "samples", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# Initialize session states
if "report" not in st.session_state:
    st.session_state["report"] = None
if "agent_logs" not in st.session_state:
    st.session_state["agent_logs"] = []
if "custom_srs_text" not in st.session_state:
    st.session_state["custom_srs_text"] = load_sample_file("healthcare_srs.txt")


# ==========================================
# SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/brain.png", width=60)
    st.title("REQUIRE-X")
    st.caption("Intelligent Multi-Agent RE Framework\n**ISO/IEC/IEEE 29148:2018 Compliant**")
    st.divider()

    st.subheader("1. Ingestion & Input")
    input_mode = st.radio("Input Source", ["Upload Document", "Sample Benchmark SRS", "Paste Plain Text"])

    uploaded_file = None
    if input_mode == "Upload Document":
        uploaded_file = st.file_uploader(
            "Upload SRS Document",
            type=["pdf", "docx", "txt", "md"],
            help="Supports PDF, Microsoft Word (.docx), and Plain Text (.txt)"
        )

    elif input_mode == "Sample Benchmark SRS":
        sample_choice = st.selectbox(
            "Select Benchmark Project",
            [
                "SmartCare Hospital Management (Healthcare)",
                "GlobalMart Distributed Marketplace (E-Commerce)"
            ]
        )
        if sample_choice.startswith("SmartCare"):
            st.session_state["custom_srs_text"] = load_sample_file("healthcare_srs.txt")
        else:
            st.session_state["custom_srs_text"] = load_sample_file("ecommerce_srs.txt")

        st.info("Loaded pre-configured benchmark SRS.")

    elif input_mode == "Paste Plain Text":
        st.session_state["custom_srs_text"] = st.text_area(
            "Software Requirement Specification (SRS)",
            value=st.session_state["custom_srs_text"],
            height=260
        )

    st.divider()

    allow_non_srs_override = False
    if input_mode == "Upload Document":
        allow_non_srs_override = st.checkbox(
            "Run anyway even if it's not detected as an SRS",
            value=False,
            help="By default, REQUIRE-X blocks analysis if the uploaded document doesn't look "
                 "like a Software Requirement Specification. Check this to force a run anyway."
        )

    run_analysis = st.button("🚀 Run Multi-Agent RE Analysis", type="primary", use_container_width=True)

    st.caption("Department of Computer Applications\nGovt. Engineering College, Thrissur")


# ==========================================
# MAIN INTERFACE HEADER
# ==========================================
st.markdown('<div class="main-title">REQUIRE-X: Multi-Agent AI Framework</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Intelligent End-to-End Software Requirement Engineering, Ambiguity Auditing, ISO/IEC/IEEE 29148 Compliance, and Architecture Synthesis</div>',
    unsafe_allow_html=True
)


# ==========================================
# EXECUTION PIPELINE
# ==========================================
if run_analysis:
    st.session_state["agent_logs"] = []

    llm = LLMProvider()

    # ------------------------------------------------------------------
    # Pre-flight gate: block analysis outright if the uploaded document
    # doesn't look like an SRS, unless the user explicitly overrides it.
    # ------------------------------------------------------------------
    proceed = True
    if uploaded_file is not None:
        filename = uploaded_file.name
        try:
            preview_parsed = DocumentParser.parse_file(uploaded_file, filename)
            uploaded_file.seek(0)  # rewind so the orchestrator can read it again
        except Exception as parse_err:
            st.error(f"⚠️ Could not read the uploaded file: {parse_err}")
            st.stop()

        with st.spinner("Checking whether the uploaded document is an SRS..."):
            srs_check = assess_document_is_srs(
                llm, preview_parsed["raw_text"], preview_parsed["sections"], filename
            )

        if not srs_check["is_srs"]:
            checked_by = "LLM classifier" if srs_check.get("source") == "llm" else "heuristic fallback"
            doc_type = srs_check.get("document_type", "unknown")

            if not allow_non_srs_override:
                st.error(
                    "🚫 **Analysis blocked: this does not appear to be an SRS (Software "
                    f"Requirement Specification) document.** It looks more like: *{doc_type}*. "
                    f"{srs_check['reason']} "
                    f"(confidence: {int(srs_check['confidence'] * 100)}%, checked via {checked_by})\n\n"
                    "REQUIRE-X only analyzes SRS documents. Upload a genuine SRS, or check "
                    "**\"Run anyway even if it's not detected as an SRS\"** in the sidebar if you "
                    "still want to proceed."
                )
                proceed = False
            else:
                st.warning(
                    "⚠️ **This does not appear to be an SRS document** (looks more like: "
                    f"*{doc_type}*), but you chose to proceed anyway. Results will likely be "
                    "inaccurate or meaningless."
                )

    if not proceed:
        st.stop()

    # Progress UI placeholders
    progress_bar = st.progress(0)
    status_box = st.empty()
    log_expander = st.expander("⚡ Live Multi-Agent Execution Telemetry", expanded=True)
    log_container = log_expander.empty()

    def update_step(msg: str, cur: int, total: int, code: str):
        progress_bar.progress(int((cur / total) * 100))
        status_box.info(f"**Pipeline Progress:** {msg}")

    def update_log(agent_name: str, level: str, msg: str):
        st.session_state["agent_logs"].append(f"[{level}] **{agent_name}**: {msg}")
        log_container.markdown("\n\n".join(st.session_state["agent_logs"]))

    orchestrator = MultiAgentOrchestrator(
        llm_provider=llm,
        on_step_progress=update_step,
        on_agent_log=update_log
    )

    try:
        if uploaded_file is not None:
            report = orchestrator.analyze_document(uploaded_file, filename)
        else:
            text_content = st.session_state["custom_srs_text"]
            buffer = io.StringIO(text_content)
            filename = "Sample_SRS_Document.txt"
            report = orchestrator.analyze_document(buffer, filename)

        st.session_state["report"] = report
        status_box.success("🎉 Multi-Agent Analysis Complete! Results ready across tabs below.")
        progress_bar.progress(100)

    except Exception as e:
        st.error(f"Execution Error: {e}")
        st.exception(e)


# ==========================================
# RESULTS DASHBOARD
# ==========================================
report: SRSAnalysisReport = st.session_state.get("report")

if report is not None:
    tabs = st.tabs([
        "📊 1. Overview & KPIs",
        "📑 2. Requirements Catalog",
        "🔍 3. Ambiguity & Defects",
        "🏆 4. ISO 29148 Compliance",
        "🕸️ 5. Dependency Graph",
        "🏛️ 6. Architecture Blueprint",
        "🔗 7. Traceability Matrix (RTM)",
        "🧪 8. Test Cases",
        "📥 9. Export & Reports"
    ])

    m = report.metrics

    # ----------------------------------------------------
    # TAB 1: OVERVIEW & KPIs
    # ----------------------------------------------------
    with tabs[0]:
        st.subheader("Executive Requirements Engineering Overview")
        st.write(report.executive_summary)

        st.markdown("---")
        # KPI metric cards
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Total Requirements", m.total_requirements)
        k2.metric("Functional (FR)", m.functional_count)
        k3.metric("Non-Functional (NFR)", m.non_functional_count)
        k4.metric("ISO 29148 Score", f"{m.iso_compliance_score:.1f}%", delta=report.compliance_scorecard.grade)
        k5.metric("Ambiguity Defect Rate", f"{m.ambiguity_rate:.1f}%", delta=f"{m.ambiguity_count} issues", delta_color="inverse")
        k6.metric("Story Points (Effort)", f"{m.total_story_points} pts")

        st.markdown("---")
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("#### 🌟 Key Identified Strengths")
            for strength in report.key_strengths:
                st.success(f"✓ {strength}")

            st.markdown("#### ⚠️ Critical Quality & Architecture Risks")
            for risk in report.key_risks:
                st.warning(f"⚠ {risk}")

        with col_r:
            st.markdown("#### 📈 Requirement Category Distribution")
            cat_dist = MetricsAnalyzer.get_category_distribution(report.requirements)
            df_cat = pd.DataFrame(list(cat_dist.items()), columns=["Category", "Count"]).set_index("Category")
            st.bar_chart(df_cat)

            st.markdown("#### 🎯 Immediate Engineering Action Items")
            for action in report.action_items:
                st.info(f"👉 {action}")

    # ----------------------------------------------------
    # TAB 2: REQUIREMENTS CATALOG
    # ----------------------------------------------------
    with tabs[1]:
        st.subheader("Classified Requirements Catalog")
        
        # Filters
        c_filter1, c_filter2, c_search = st.columns([1, 1, 2])
        type_filter = c_filter1.selectbox("Filter Type", ["All", "Functional", "Non-Functional"])
        complexity_filter = c_filter2.selectbox("Filter Complexity", ["All", "Low", "Medium", "High"])
        search_query = c_search.text_input("Search statements...", "")

        filtered_reqs = report.requirements
        if type_filter != "All":
            filtered_reqs = [r for r in filtered_reqs if r.req_type == type_filter]
        if complexity_filter != "All":
            filtered_reqs = [r for r in filtered_reqs if r.complexity == complexity_filter]
        if search_query:
            q = search_query.lower()
            filtered_reqs = [r for r in filtered_reqs if q in r.statement.lower() or q in r.title.lower() or q in r.id.lower()]

        # Display as styled cards or interactive table
        st.write(f"Showing **{len(filtered_reqs)}** matching requirements:")

        for req in filtered_reqs:
            with st.expander(f"**{req.id}** — {req.title} [{req.req_type} | {req.category}]", expanded=False):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Statement:** {req.statement}")
                    if req.acceptance_criteria:
                        st.markdown("**Acceptance Criteria:**")
                        for ac in req.acceptance_criteria:
                            st.markdown(f"- {ac}")
                with col_b:
                    st.markdown(f"**Complexity:** `{req.complexity}` ({req.story_points} pts)")
                    st.markdown(f"**Priority:** `{req.priority}`")
                    st.caption(f"Rationale: {req.complexity_rationale}")

    # ----------------------------------------------------
    # TAB 3: AMBIGUITY & DEFECTS
    # ----------------------------------------------------
    with tabs[2]:
        st.subheader("Ambiguity Detection & Disambiguation Auditing")
        st.write(
            "The Ambiguity Detection Agent identifies vague adjectives, passive phrasing without actors, "
            "untestable statements, and open-ended qualifiers, providing measurable ISO 29148 rewrites."
        )

        if not report.ambiguities:
            st.success("🎉 No ambiguities detected! Requirements meet strict clarity standards.")
        else:
            amb_data = []
            for a in report.ambiguities:
                amb_data.append({
                    "Requirement ID": a.req_id,
                    "Flaw Category": a.flaw_category,
                    "Severity": a.severity,
                    "Ambiguous Phrase": a.ambiguous_text,
                    "Defect Rationale": a.explanation,
                    "ISO Disambiguated Rewrite": a.suggested_rewrite
                })
            df_amb = pd.DataFrame(amb_data)
            st.dataframe(df_amb, use_container_width=True)

            st.markdown("### Side-by-Side Disambiguation Comparison")
            for a in report.ambiguities[:6]:
                st.markdown(f"#### 🔎 `{a.req_id}`: *{a.flaw_category}* (Severity: **{a.severity}**)")
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"**Original Flawed Phrase:**\n\"{a.ambiguous_text}\"\n\n*Why:* {a.explanation}")
                with c2:
                    st.success(f"**Suggested Disambiguated Rewrite:**\n\"{a.suggested_rewrite}\"")

    # ----------------------------------------------------
    # TAB 4: ISO/IEC/IEEE 29148 COMPLIANCE
    # ----------------------------------------------------
    with tabs[3]:
        st.subheader("ISO/IEC/IEEE 29148:2018 Standards Compliance Scorecard")
        sc = report.compliance_scorecard

        c_score, c_summary = st.columns([1, 3])
        with c_score:
            st.metric("Overall Compliance Score", f"{sc.overall_score:.1f}%", f"Grade {sc.grade}")
        with c_summary:
            st.info(sc.summary)

        st.markdown("### 9 Quality Characteristics Rubric")
        for c in sc.criteria:
            col_cr1, col_cr2, col_cr3 = st.columns([2, 1, 4])
            with col_cr1:
                st.markdown(f"**{c.criterion_name}**")
            with col_cr2:
                if c.status == "Pass":
                    st.markdown(f"<span class='badge-pass'>Pass ({c.score:.0f}%)</span>", unsafe_allow_html=True)
                elif c.status == "Warning":
                    st.markdown(f"<span class='badge-critical' style='background:#fef3c7; color:#b45309;'>Warning ({c.score:.0f}%)</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='badge-critical'>Fail ({c.score:.0f}%)</span>", unsafe_allow_html=True)
            with col_cr3:
                st.write(f"💡 {c.remediation}")
            st.divider()

    # ----------------------------------------------------
    # TAB 5: DEPENDENCY GRAPH
    # ----------------------------------------------------
    with tabs[4]:
        st.subheader("Requirement Dependency & Constraint Graph")
        st.write(
            "Visualizes inter-requirement relationships (`depends_on`, `constrains`, `conflicts_with`, `triggers`)."
        )

        mermaid_syntax = DependencyGraphBuilder.build_mermaid_graph(report.requirements, report.dependencies)
        
        # Render Mermaid via HTML component
        mermaid_html = f"""
        <div class="mermaid" style="background:#ffffff; padding:15px; border-radius:8px; border:1px solid #e2e8f0;">
            {mermaid_syntax}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{startOnLoad:true, theme:'neutral'}});</script>
        """
        components.html(mermaid_html, height=450, scrolling=True)

        if report.dependencies:
            st.markdown("### Dependency Links Table")
            dep_rows = [
                {
                    "Source Req": d.source_id,
                    "Relationship": d.dependency_type,
                    "Target Req": d.target_id,
                    "Explanation": d.description
                }
                for d in report.dependencies
            ]
            st.dataframe(pd.DataFrame(dep_rows), use_container_width=True)

    # ----------------------------------------------------
    # TAB 6: ARCHITECTURE RECOMMENDATION
    # ----------------------------------------------------
    with tabs[5]:
        st.subheader("Software Architecture Recommendation & Blueprint")
        arch = report.architecture

        st.success(f"### Recommended Pattern: **{arch.recommended_pattern}**")
        if arch.secondary_pattern:
            st.caption(f"Complementary Pattern: {arch.secondary_pattern}")

        st.markdown(f"**Architectural Rationale:**\n{arch.rationale}")

        st.markdown("---")
        c_pro, c_con = st.columns(2)
        with c_pro:
            st.markdown("#### ✅ Architectural Benefits (Pros)")
            for p in arch.tradeoffs_pros:
                st.write(f"✓ {p}")
        with c_con:
            st.markdown("#### ⚠️ Trade-offs & Challenges (Cons)")
            for con in arch.tradeoffs_cons:
                st.write(f"⚠ {con}")

        st.markdown("### Recommended Component Decomposition")
        for comp in arch.components:
            with st.container():
                st.markdown(f"**{comp.name}** (`{comp.component_type}`)")
                st.write(comp.responsibility)
                st.caption(f"Mapped Requirements: {', '.join(comp.mapped_requirements)}")
                st.divider()

        st.markdown("### Architectural Topology Diagram")
        arch_html = f"""
        <div class="mermaid" style="background:#ffffff; padding:15px; border-radius:8px; border:1px solid #e2e8f0;">
            {arch.mermaid_diagram}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{startOnLoad:true, theme:'neutral'}});</script>
        """
        components.html(arch_html, height=450, scrolling=True)

    # ----------------------------------------------------
    # TAB 7: TRACEABILITY MATRIX (RTM)
    # ----------------------------------------------------
    with tabs[6]:
        st.subheader("Requirements Traceability Matrix (RTM)")
        st.write(
            "Bidirectional traceability linking each Requirement to Architectural Modules, Test Suites, and Verification Methods."
        )

        rtm_rows = [
            {
                "Req ID": item.req_id,
                "Requirement Title": item.req_title,
                "Type": item.req_type,
                "Category": item.category,
                "Architectural Module": item.architecture_module,
                "Mapped Test Cases": ", ".join(item.test_case_ids) if item.test_case_ids else "None",
                "Verification Method": item.verification_method,
                "Traceability Status": item.status
            }
            for item in report.traceability_matrix
        ]
        df_rtm = pd.DataFrame(rtm_rows)
        st.dataframe(df_rtm, use_container_width=True)

    # ----------------------------------------------------
    # TAB 8: TEST CASES
    # ----------------------------------------------------
    with tabs[7]:
        st.subheader("Synthesized Functional & Non-Functional Test Cases")
        st.write(f"Generated **{len(report.test_cases)}** structured verification test cases.")

        for tc in report.test_cases:
            with st.expander(f"**{tc.test_id}** — {tc.title} (Mapped to `{tc.req_id}` | Type: `{tc.test_type}`)", expanded=False):
                st.markdown(f"**Preconditions:** {tc.preconditions}")
                st.markdown("**Test Steps:**")
                for s in tc.steps:
                    st.write(f"- {s}")
                if tc.test_data:
                    st.markdown(f"**Test Data:** `{tc.test_data}`")
                st.success(f"**Expected Result:** {tc.expected_result}")

    # ----------------------------------------------------
    # TAB 9: EXPORT & REPORTS
    # ----------------------------------------------------
    with tabs[8]:
        st.subheader("Export & Download Engineering Artifacts")
        st.write("Download formal ISO-compliant engineering deliverables generated by REQUIRE-X.")

        col_p, col_j, col_c, col_m = st.columns(4)

        # 1. PDF Export
        pdf_bytes = PDFReportGenerator.generate_pdf_bytes(report)
        col_p.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"REQUIRE_X_Report_{report.analysis_timestamp.replace(':', '-')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

        # 2. JSON Export
        json_str = JSONReportExporter.to_json_str(report)
        col_j.download_button(
            label="📋 Download JSON Report",
            data=json_str,
            file_name="require_x_analysis.json",
            mime="application/json",
            use_container_width=True
        )

        # 3. CSV Export
        csv_df = pd.DataFrame([r.model_dump() for r in report.requirements])
        csv_bytes = csv_df.to_csv(index=False).encode("utf-8")
        col_c.download_button(
            label="📊 Download CSV Catalog",
            data=csv_bytes,
            file_name="requirements_catalog.csv",
            mime="text/csv",
            use_container_width=True
        )

        # 4. Markdown Export
        md_str = MarkdownReportExporter.to_markdown(report)
        col_m.download_button(
            label="📝 Download Markdown",
            data=md_str,
            file_name="REQUIRE_X_SRS_Report.md",
            mime="text/markdown",
            use_container_width=True
        )

else:
    # Initial landing guide when no analysis has been run yet
    st.info("👈 Select an SRS input from the sidebar (or choose a Benchmark Project) and click **'Run Multi-Agent RE Analysis'** to begin.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📥 1. Ingest & Classify")
        st.write("Upload PDF, Word (DOCX), or Text SRS documents. The framework automatically parses sections, segments statements, and classifies Functional (FR) vs Non-Functional (NFR) requirements.")
    with col2:
        st.markdown("### 🤖 2. Multi-Agent Audit")
        st.write("7 collaborative AI agents inspect ambiguities, check ISO/IEC/IEEE 29148:2018 compliance rubrics, map dependencies, and estimate implementation complexity.")
    with col3:
        st.markdown("### 🚀 3. Generate Artifacts")
        st.write("Automatically synthesizes software architecture patterns, Mermaid diagrams, bidirectional Traceability Matrices (RTM), test suites, and publication-ready PDF reports.")
