"""
REQUIRE-X: Dependency Analysis Agent
Identifies functional and non-functional relationships, prerequisites, constraints, and conflicts among software requirements.
"""

from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement, RequirementDependency


class DependencyAnalysisAgent(BaseAgent):
    """Specialized Agent for mapping inter-requirement dependencies and constructing relationship graphs."""

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Dependency Analysis Agent",
            role="Identifies relationships, prerequisites, conflicts, and constraints across software requirements",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting requirement dependency analysis and graph construction...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])

        dependencies: List[RequirementDependency] = []

        if len(requirements) < 2:
            self.log("Insufficient requirement count for inter-dependency mapping.", "INFO")
            context["dependencies"] = []
            return context

        # Try LLM if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for semantic dependency identification...", "INFO")
            dependencies = self._analyze_with_llm(requirements)

        # Fallback to rule-based semantic linking
        if not dependencies:
            self.log("Executing heuristic dependency and constraint mapping...", "INFO")
            dependencies = self._analyze_with_rules(requirements)

        self.log(f"Discovered {len(dependencies)} inter-requirement dependencies and constraints.", "SUCCESS")
        context["dependencies"] = dependencies
        return context

    def _analyze_with_llm(self, requirements: List[Requirement]) -> List[RequirementDependency]:
        """Identifies dependencies using LLM."""
        req_list = [
            f"ID: {r.id}, Type: {r.req_type}, Category: {r.category}, Text: {r.statement}"
            for r in requirements[:20]
        ]
        user_prompt = "Identify all dependencies, constraints, prerequisites, and relationships between these requirements:\n\n" + "\n".join(req_list)

        system_prompt = (
            "You are a Software Architect and Requirements Traceability Specialist. "
            "Analyze the given requirements and identify all meaningful dependencies among them. "
            "Return a strictly valid JSON object with the key 'dependencies', containing an array of objects. "
            "Each object must have:\n"
            "- source_id: string (e.g. 'FR-002')\n"
            "- target_id: string (e.g. 'FR-001')\n"
            "- dependency_type: 'depends_on', 'conflicts_with', 'extends', 'triggers', or 'constrains'\n"
            "- description: string (clear rationale for the dependency)"
        )

        response_text = self.llm.generate(system_prompt, user_prompt, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "dependencies" in data:
            deps = []
            req_ids = {r.id for r in requirements}
            for item in data["dependencies"]:
                try:
                    dep = RequirementDependency(**item)
                    if dep.source_id in req_ids and dep.target_id in req_ids and dep.source_id != dep.target_id:
                        deps.append(dep)
                except Exception as e:
                    self.log(f"Skipping malformed dependency: {e}", "WARNING")
            return deps
        return []

    def _analyze_with_rules(self, requirements: List[Requirement]) -> List[RequirementDependency]:
        """Deterministic dependency mapping based on domain ontology and keywords."""
        dependencies: List[RequirementDependency] = []
        req_by_id = {r.id: r for r in requirements}

        # Find Auth / Security prerequisites
        auth_reqs = [r for r in requirements if "auth" in r.category.lower() or "security" in r.category.lower() or "login" in r.statement.lower()]
        data_reqs = [r for r in requirements if "data" in r.category.lower() or "database" in r.statement.lower()]
        nfr_security = [r for r in requirements if r.req_type == "Non-Functional" and r.category == "Security"]
        nfr_perf = [r for r in requirements if r.req_type == "Non-Functional" and r.category == "Performance"]

        for req in requirements:
            stmt_lower = req.statement.lower()

            # 1. Business logic depends on Authentication if not auth itself
            if auth_reqs and req not in auth_reqs and req.req_type == "Functional":
                primary_auth = auth_reqs[0]
                if any(k in stmt_lower for k in ["payment", "profile", "order", "view", "edit", "upload", "submit", "manage"]):
                    dependencies.append(RequirementDependency(
                        source_id=req.id,
                        target_id=primary_auth.id,
                        dependency_type="depends_on",
                        description=f"Execution of '{req.title}' requires prior user authentication ({primary_auth.id})."
                    ))

            # 2. Operations with persistence depend on Data Management
            if data_reqs and req not in data_reqs and req.req_type == "Functional":
                if any(k in stmt_lower for k in ["save", "store", "persist", "record", "archive", "history", "log"]):
                    primary_data = data_reqs[0]
                    dependencies.append(RequirementDependency(
                        source_id=req.id,
                        target_id=primary_data.id,
                        dependency_type="depends_on",
                        description=f"State persistence for '{req.title}' relies on data storage mechanisms ({primary_data.id})."
                    ))

            # 3. Security NFRs constrain sensitive Functional Requirements
            if nfr_security and req.req_type == "Functional":
                if any(k in stmt_lower for k in ["password", "token", "payment", "pii", "confidential", "credential", "auth"]):
                    for sec in nfr_security[:2]:
                        dependencies.append(RequirementDependency(
                            source_id=sec.id,
                            target_id=req.id,
                            dependency_type="constrains",
                            description=f"Security standard ({sec.id}) strictly constrains functional handling of '{req.title}'."
                        ))

            # 4. Performance NFRs constrain transaction / search FRs
            if nfr_perf and req.req_type == "Functional":
                if any(k in stmt_lower for k in ["search", "filter", "query", "load", "upload", "process", "download"]):
                    for perf in nfr_perf[:1]:
                        dependencies.append(RequirementDependency(
                            source_id=perf.id,
                            target_id=req.id,
                            dependency_type="constrains",
                            description=f"Performance latency SLA ({perf.id}) constrains runtime throughput of '{req.title}'."
                        ))

            # 5. Sequential flow between sequential FRs (e.g. FR-002 extends/triggers FR-001)
            # Link notification/reporting to core transactions
            if "notif" in req.category.lower() or "email" in stmt_lower or "sms" in stmt_lower:
                tx_reqs = [r for r in requirements if r.req_type == "Functional" and ("payment" in r.statement.lower() or "order" in r.statement.lower() or "submit" in r.statement.lower())]
                if tx_reqs:
                    dependencies.append(RequirementDependency(
                        source_id=req.id,
                        target_id=tx_reqs[0].id,
                        dependency_type="triggers",
                        description=f"Notification event '{req.title}' is triggered by completion of '{tx_reqs[0].title}'."
                    ))

        # Deduplicate dependencies
        unique_deps = []
        seen_pairs = set()
        for d in dependencies:
            key = (d.source_id, d.target_id, d.dependency_type)
            if key not in seen_pairs:
                seen_pairs.add(key)
                unique_deps.append(d)

        return unique_deps
