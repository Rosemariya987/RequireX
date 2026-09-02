"""
REQUIRE-X: Test Case Generation Agent
Automatically generates functional and non-functional test suites mapped directly to software requirements.
"""

from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement, TestCase


class TestCaseGenerationAgent(BaseAgent):
    """Specialized Agent for synthesizing structured, verifiable test cases from requirements."""

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Test Case Generation Agent",
            role="Synthesizes functional, integration, security, and performance test cases mapped to requirements",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting automated test case synthesis...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])

        test_cases: List[TestCase] = []

        # Try LLM if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for test case generation...", "INFO")
            test_cases = self._generate_with_llm(requirements)

        # Fallback to rule-based test case synthesis
        if not test_cases:
            self.log("Executing heuristic test case generation engine...", "INFO")
            test_cases = self._generate_with_rules(requirements)

        self.log(
            f"Successfully generated {len(test_cases)} structured test cases across functional and non-functional categories.",
            "SUCCESS"
        )
        context["test_cases"] = test_cases
        return context

    def _generate_with_llm(self, requirements: List[Requirement]) -> List[TestCase]:
        """Generates test cases using LLM."""
        req_list = [
            f"ID: {r.id} ({r.req_type} - {r.category}): {r.statement}"
            for r in requirements[:15]
        ]
        user_prompt = "Generate comprehensive test cases for each of the following requirements:\n\n" + "\n".join(req_list)

        system_prompt = (
            "You are a Senior QA Automation & Test Architect. "
            "Generate rigorous test cases covering positive paths, boundary conditions, and negative error flows. "
            "Return a strictly valid JSON object with the key 'test_cases', containing an array of objects. "
            "Each object must have:\n"
            "- test_id: string (e.g. 'TC-001', 'TC-002')\n"
            "- req_id: string (matching requirement ID)\n"
            "- title: string (descriptive test scenario title)\n"
            "- test_type: 'Functional', 'Integration', 'Security', 'Performance', 'Boundary / Edge Case', or 'Usability'\n"
            "- preconditions: string\n"
            "- steps: array of string instructions\n"
            "- test_data: string\n"
            "- expected_result: string (concrete pass criteria)"
        )

        response_text = self.llm.generate(system_prompt, user_prompt, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "test_cases" in data:
            tests = []
            for item in data["test_cases"]:
                try:
                    tests.append(TestCase(**item))
                except Exception as e:
                    self.log(f"Skipping malformed test case: {e}", "WARNING")
            return tests
        return []

    def _generate_with_rules(self, requirements: List[Requirement]) -> List[TestCase]:
        """Deterministic test case generator covering positive and edge tests."""
        test_cases: List[TestCase] = []
        tc_counter = 1

        for req in requirements:
            # 1. Positive Functional Test Case
            if req.req_type == "Functional":
                test_cases.append(TestCase(
                    test_id=f"TC-{tc_counter:03d}",
                    req_id=req.id,
                    title=f"Verify Successful Execution of {req.title}",
                    test_type="Functional",
                    preconditions="System is active, database is connected, user has valid role permissions.",
                    steps=[
                        f"1. Navigate to the interface corresponding to '{req.title}'.",
                        f"2. Supply valid operational input parameters.",
                        f"3. Trigger action defined in '{req.statement}'.",
                        "4. Inspect system response and database state."
                    ],
                    test_data="Valid authorized user credentials & standard input payload.",
                    expected_result=f"System successfully executes {req.title} with HTTP 200/201 status and persists expected state."
                ))
                tc_counter += 1

                # 2. Boundary / Negative Test Case
                test_cases.append(TestCase(
                    test_id=f"TC-{tc_counter:03d}",
                    req_id=req.id,
                    title=f"Negative Validation & Boundary Check for {req.title}",
                    test_type="Boundary / Edge Case",
                    preconditions="System is active.",
                    steps=[
                        f"1. Trigger '{req.title}' with malformed, empty, or out-of-range input data.",
                        "2. Attempt action with expired authentication token or unauthorized role.",
                        "3. Inspect error telemetry and user feedback."
                    ],
                    test_data="Null strings, SQL metacharacters, oversized payloads, invalid types.",
                    expected_result="System safely rejects malformed input with user-friendly error message (HTTP 400/403/422) without crashing."
                ))
                tc_counter += 1

            # NFR Test Case
            else:
                test_type = "Security" if req.category == "Security" else ("Performance" if req.category == "Performance" else "Integration")
                test_cases.append(TestCase(
                    test_id=f"TC-{tc_counter:03d}",
                    req_id=req.id,
                    title=f"Validate Quality Attribute SLA: {req.title}",
                    test_type=test_type,
                    preconditions=f"Automated benchmark test harness configured for {req.category} testing.",
                    steps=[
                        f"1. Initialize telemetry monitoring for '{req.category}'.",
                        f"2. Execute automated test harness simulating target operational conditions.",
                        f"3. Measure response metrics against statement: '{req.statement}'.",
                        "4. Compare recorded metrics against ISO 29148 acceptance thresholds."
                    ],
                    test_data=f"Benchmark load profile / Security penetration payload for {req.category}.",
                    expected_result=f"System fully complies with {req.category} SLA criteria with zero unhandled exceptions."
                ))
                tc_counter += 1

        return test_cases
