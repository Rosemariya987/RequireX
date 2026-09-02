"""
REQUIRE-X Analytics: Metrics Computation
Calculates requirement quality statistics, distributions, and scorecard rubrics.
"""

from typing import List, Dict, Any
from require_x.models.schema import Requirement, AmbiguityIssue, ComplianceScorecard


class MetricsAnalyzer:
    """Computes distributions and aggregations for UI and reports."""

    @classmethod
    def get_category_distribution(cls, requirements: List[Requirement]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for req in requirements:
            dist[req.category] = dist.get(req.category, 0) + 1
        return dist

    @classmethod
    def get_complexity_distribution(cls, requirements: List[Requirement]) -> Dict[str, int]:
        dist = {"Low": 0, "Medium": 0, "High": 0}
        for req in requirements:
            dist[req.complexity] = dist.get(req.complexity, 0) + 1
        return dist

    @classmethod
    def get_priority_distribution(cls, requirements: List[Requirement]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for req in requirements:
            dist[req.priority] = dist.get(req.priority, 0) + 1
        return dist

    @classmethod
    def get_flaw_category_distribution(cls, ambiguities: List[AmbiguityIssue]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for amb in ambiguities:
            dist[amb.flaw_category] = dist.get(amb.flaw_category, 0) + 1
        return dist
