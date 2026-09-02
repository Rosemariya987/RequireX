"""
Tests for REQUIRE-X Pydantic Schemas & Models
"""
import unittest
from require_x.models.schema import (
    Requirement, AmbiguityIssue, ComplianceCriterion,
    ComplianceScorecard
)


class TestModels(unittest.TestCase):
    def test_requirement_model(self):
        req = Requirement(
            id="FR-001",
            title="User Authentication",
            statement="The system shall authenticate users using email and password.",
            req_type="Functional",
            category="Security",
            complexity="Medium",
            story_points=3,
            complexity_rationale="Standard auth logic",
            acceptance_criteria=["Valid login returns JWT token"],
            priority="Must Have"
        )
        self.assertEqual(req.id, "FR-001")
        self.assertEqual(req.req_type, "Functional")
        self.assertEqual(req.story_points, 3)

    def test_ambiguity_model(self):
        issue = AmbiguityIssue(
            req_id="FR-008",
            ambiguous_text="fast",
            flaw_category="Unquantified Metric",
            severity="Warning",
            explanation="Untestable latency bounds",
            suggested_rewrite="The system shall respond in < 200ms"
        )
        self.assertEqual(issue.severity, "Warning")
        self.assertEqual(issue.req_id, "FR-008")

    def test_compliance_scorecard(self):
        scorecard = ComplianceScorecard(
            overall_score=88.5,
            grade="A",
            summary="Passed ISO 29148 assessment",
            criteria=[
                ComplianceCriterion(
                    criterion_name="Completeness",
                    score=90.0,
                    status="Pass",
                    strengths=["All sections covered"],
                    defects_found=[],
                    remediation="None"
                )
            ]
        )
        self.assertEqual(scorecard.grade, "A")
        self.assertEqual(len(scorecard.criteria), 1)


if __name__ == "__main__":
    unittest.main()
