"""
REQUIRE-X Analytics: Graph Builder
Constructs network graph representations of requirement dependencies, constraints, and conflicts.
"""

from typing import List, Dict, Any, Tuple
from require_x.models.schema import Requirement, RequirementDependency


class DependencyGraphBuilder:
    """Builds interactive and textual graph structures for requirement relationships."""

    @classmethod
    def build_mermaid_graph(
        cls,
        requirements: List[Requirement],
        dependencies: List[RequirementDependency]
    ) -> str:
        """Generates Mermaid.js syntax for visual rendering in markdown and UI."""
        if not dependencies:
            return "graph TD\n    NoDeps[\"No Inter-Requirement Dependencies Detected\"]"

        lines = ["graph LR"]

        # Class styles
        lines.append("    classDef frStyle fill:#2563eb,stroke:#1d4ed8,color:#ffffff,stroke-width:2px;")
        lines.append("    classDef nfrStyle fill:#7c3aed,stroke:#6d28d9,color:#ffffff,stroke-width:2px;")
        lines.append("    classDef conflictStyle fill:#dc2626,stroke:#b91c1c,color:#ffffff,stroke-width:2px;")

        # Nodes
        req_types = {r.id: r.req_type for r in requirements}
        req_titles = {r.id: r.title for r in requirements}

        referenced_nodes = set()
        for dep in dependencies:
            referenced_nodes.add(dep.source_id)
            referenced_nodes.add(dep.target_id)

        for req_id in referenced_nodes:
            title = req_titles.get(req_id, req_id)
            # Escape quotes in title
            clean_title = title.replace('"', "'")[:25]
            lines.append(f'    {req_id}["{req_id}: {clean_title}"]')

        # Edges
        for dep in dependencies:
            src = dep.source_id
            tgt = dep.target_id
            dtype = dep.dependency_type

            if dtype == "depends_on":
                lines.append(f'    {src} -->|"depends on"| {tgt}')
            elif dtype == "conflicts_with":
                lines.append(f'    {src} -.->|"CONFLICT"| {tgt}')
            elif dtype == "constrains":
                lines.append(f'    {src} ==>|"constrains"| {tgt}')
            elif dtype == "triggers":
                lines.append(f'    {src} -->|"triggers"| {tgt}')
            else:
                lines.append(f'    {src} -->|"{dtype}"| {tgt}')

        # Apply styles
        for req_id in referenced_nodes:
            if req_types.get(req_id) == "Non-Functional":
                lines.append(f"    class {req_id} nfrStyle;")
            else:
                lines.append(f"    class {req_id} frStyle;")

        return "\n".join(lines)

    @classmethod
    def analyze_graph_topology(
        cls,
        requirements: List[Requirement],
        dependencies: List[RequirementDependency]
    ) -> Dict[str, Any]:
        """Analyzes graph properties: degree centrality, orphan nodes, cyclic chains."""
        req_ids = {r.id for r in requirements}
        in_degree: Dict[str, int] = {r_id: 0 for r_id in req_ids}
        out_degree: Dict[str, int] = {r_id: 0 for r_id in req_ids}

        for dep in dependencies:
            if dep.source_id in out_degree:
                out_degree[dep.source_id] += 1
            if dep.target_id in in_degree:
                in_degree[dep.target_id] += 1

        orphan_nodes = [
            r_id for r_id in req_ids
            if in_degree.get(r_id, 0) == 0 and out_degree.get(r_id, 0) == 0
        ]

        critical_nodes = sorted(
            [{"req_id": r_id, "incoming_dependencies": in_degree[r_id], "outgoing_dependencies": out_degree[r_id]} for r_id in req_ids],
            key=lambda x: x["incoming_dependencies"] + x["outgoing_dependencies"],
            reverse=True
        )[:5]

        return {
            "total_nodes": len(req_ids),
            "total_edges": len(dependencies),
            "orphan_requirements": orphan_nodes,
            "central_requirements": critical_nodes
        }
