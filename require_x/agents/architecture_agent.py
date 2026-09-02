"""
REQUIRE-X: Traceability & Architecture Recommendation Agent
Recommends software architecture patterns, decomposes system into components, and generates Mermaid architectural blueprints.
"""

from typing import Dict, Any, List
from require_x.agents.base_agent import BaseAgent
from require_x.models.schema import Requirement, ArchitectureRecommendation, ArchitecturalComponent


class ArchitectureRecommendationAgent(BaseAgent):
    """Specialized Agent for recommending software architecture patterns and component topology."""

    def __init__(self, llm_provider=None, on_status_update=None):
        super().__init__(
            name="Traceability & Architecture Agent",
            role="Recommends optimal software architecture patterns, tech stacks, and Mermaid blueprints based on requirements",
            llm_provider=llm_provider,
            on_status_update=on_status_update
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Starting Software Architecture Analysis and Blueprint Recommendation...", "INFO")
        requirements: List[Requirement] = context.get("requirements", [])

        arch: ArchitectureRecommendation = None

        # Try LLM if online
        if self.llm.provider != "offline":
            self.log("Invoking LLM for architectural pattern synthesis...", "INFO")
            arch = self._recommend_with_llm(requirements)

        # Fallback to deterministic architectural analysis
        if not arch:
            self.log("Executing heuristic architectural pattern mapping...", "INFO")
            arch = self._recommend_with_rules(requirements)

        self.log(
            f"Recommended Software Architecture: {arch.recommended_pattern} (Components: {len(arch.components)})",
            "SUCCESS"
        )
        context["architecture"] = arch
        return context

    def _recommend_with_llm(self, requirements: List[Requirement]) -> ArchitectureRecommendation:
        """Synthesizes architecture using LLM."""
        req_texts = [
            f"[{r.id}] ({r.req_type} - {r.category}): {r.statement}"
            for r in requirements[:20]
        ]
        user_prompt = "Analyze these requirements and propose the optimal software architecture pattern, component breakdown, tech stack, and Mermaid diagram:\n\n" + "\n".join(req_texts)

        system_prompt = (
            "You are a Chief Software Architect. "
            "Analyze the software requirements and determine the most suitable software architectural pattern "
            "(e.g., Event-Driven Microservices, Clean / Hexagonal Architecture, Modular Monolith, CQRS, Layered MVC). "
            "Return a strictly valid JSON object with:\n"
            "- recommended_pattern: string\n"
            "- secondary_pattern: string or null\n"
            "- rationale: string (detailed justification based on NFRs and domain)\n"
            "- tradeoffs_pros: array of strings\n"
            "- tradeoffs_cons: array of strings\n"
            "- components: array of objects with (name, component_type, responsibility, mapped_requirements)\n"
            "- tech_stack_recommendation: key-value object (Frontend, Backend, Database, Cache, Messaging, Auth, CI_CD)\n"
            "- mermaid_diagram: valid Mermaid.js graph string (e.g. 'graph TD\\n  ...')"
        )

        response_text = self.llm.generate(system_prompt, user_prompt, json_mode=True)
        data = self.llm.extract_json_block(response_text)

        if data and isinstance(data, dict) and "recommended_pattern" in data:
            try:
                return ArchitectureRecommendation(**data)
            except Exception as e:
                self.log(f"Skipping malformed architecture response: {e}", "WARNING")
        return None

    def _recommend_with_rules(self, requirements: List[Requirement]) -> ArchitectureRecommendation:
        """Deterministic architectural inference based on NFR profile and requirement volume."""
        nfr_categories = {r.category for r in requirements if r.req_type == "Non-Functional"}
        total_reqs = len(requirements)
        high_complexity_count = sum(1 for r in requirements if r.complexity == "High")

        # Determine architecture pattern
        if "Scalability" in nfr_categories or "Performance" in nfr_categories or high_complexity_count >= 3:
            pattern = "Event-Driven Microservices Architecture"
            secondary = "CQRS (Command Query Responsibility Segregation)"
            rationale = (
                "Selected Event-Driven Microservices architecture due to demanding non-functional requirements "
                "in Scalability, high throughput, and independent domain decoupling. Asynchronous messaging isolates "
                "failure domains and supports horizontal elastic autoscaling."
            )
            pros = [
                "High horizontal scalability and fault isolation",
                "Independent deployment lifecycles per domain service",
                "Asynchronous message-driven decoupling",
                "Fine-grained security and resource allocation"
            ]
            cons = [
                "Higher distributed tracing and operational complexity",
                "Eventual consistency data management across services"
            ]
            tech_stack = {
                "Frontend": "React / Next.js / TailwindCSS",
                "API Gateway": "Kong / Envoy / FastAPI Gateway",
                "Backend Services": "Python (FastAPI) / Go / Java Spring Boot",
                "Event Bus": "Apache Kafka / RabbitMQ",
                "Primary Database": "PostgreSQL (Relational) + Redis (Cache)",
                "Security": "OAuth2 / OIDC + Keycloak / JWT",
                "Deployment": "Docker + Kubernetes (K8s) + Helm"
            }
            mermaid = """graph TD
    Client["Client Apps (Web / Mobile)"] --> Gateway["API Gateway (Auth & Rate Limit)"]
    Gateway --> ServiceA["Auth & Identity Service"]
    Gateway --> ServiceB["Core Business Engine Service"]
    Gateway --> ServiceC["Processing & Transaction Service"]
    Gateway --> ServiceD["Analytics & Reporting Service"]
    
    ServiceB <--> EventBus[("Event Bus (Kafka / RabbitMQ)")]
    ServiceC <--> EventBus
    ServiceD <--> EventBus
    
    ServiceA --> DB_Auth[("Auth Database")]
    ServiceB --> DB_Core[("Core DB (PostgreSQL)")]
    ServiceC --> DB_Trans[("Tx Store")]
    ServiceD --> DB_Analytics[("Analytics Warehouse")]"""

        else:
            pattern = "Clean / Hexagonal Architecture (Modular Monolith)"
            secondary = "Layered Domain-Driven Design (DDD)"
            rationale = (
                "Selected Clean / Hexagonal Architecture within a Modular Monolith. "
                "This guarantees high maintainability, testability, and clear separation of concerns without "
                "the operational overhead of distributed microservices, allowing future microservice extraction if needed."
            )
            pros = [
                "Domain business logic is 100% decoupled from external frameworks and UI",
                "Exceptional unit and integration testability",
                "Low deployment and operational complexity",
                "Zero distributed network latency overhead"
            ]
            cons = [
                "Requires discipline to preserve domain boundary encapsulation",
                "Scales as a single unified deployment unit"
            ]
            tech_stack = {
                "Frontend": "Modern Responsive Web UI (TypeScript / React)",
                "Application Core": "Python (FastAPI / Pydantic Clean Arch)",
                "Persistence Layer": "SQLAlchemy 2.0 / PostgreSQL",
                "Caching": "Redis In-Memory Cache",
                "Security": "JWT / Role-Based Access Control (RBAC)",
                "CI/CD": "GitHub Actions + Docker Containers"
            }
            mermaid = """graph TD
    subgraph UI_Layer ["Presentation / UI Layer"]
        Web["Web Interface & REST Endpoints"]
    end
    
    subgraph Application_Layer ["Application & Use Case Layer"]
        UseCases["Use Case Interactors / Orchestrators"]
    end
    
    subgraph Domain_Layer ["Domain Core (Entities & Business Rules)"]
        Entities["Core Domain Entities & Value Objects"]
    end
    
    subgraph Infrastructure_Layer ["Infrastructure Layer"]
        DB[("Database Repository (PostgreSQL)")]
        ExternalAPI["External Service Gateways"]
        AuthModule["Identity & Security Provider"]
    end
    
    Web --> UseCases
    UseCases --> Entities
    UseCases --> Infrastructure_Layer
    Infrastructure_Layer -.-> Entities"""

        # Map requirements to components
        components = self._derive_components(requirements, pattern)

        return ArchitectureRecommendation(
            recommended_pattern=pattern,
            secondary_pattern=secondary,
            rationale=rationale,
            tradeoffs_pros=pros,
            tradeoffs_cons=cons,
            components=components,
            tech_stack_recommendation=tech_stack,
            mermaid_diagram=mermaid
        )

    def _derive_components(self, requirements: List[Requirement], pattern: str) -> List[ArchitecturalComponent]:
        """Maps requirements to modular system components."""
        auth_reqs = [r.id for r in requirements if "auth" in r.category.lower() or "user" in r.category.lower() or "security" in r.category.lower()]
        core_reqs = [r.id for r in requirements if r.req_type == "Functional" and r.id not in auth_reqs]
        data_reqs = [r.id for r in requirements if "data" in r.category.lower() or "report" in r.category.lower()]
        infra_reqs = [r.id for r in requirements if r.req_type == "Non-Functional" and r.id not in auth_reqs]

        return [
            ArchitecturalComponent(
                name="API Gateway & Security Provider",
                component_type="Gateway / Auth",
                responsibility="Handles TLS termination, routing, JWT token verification, rate limiting, and CORS.",
                mapped_requirements=auth_reqs or ["FR-001"]
            ),
            ArchitecturalComponent(
                name="Core Business Logic Engine",
                component_type="Domain Service",
                responsibility="Executes primary application workflows, business validation, and entity state transitions.",
                mapped_requirements=core_reqs[:5] if core_reqs else ["FR-001", "FR-002"]
            ),
            ArchitecturalComponent(
                name="Data Management & Persistence Service",
                component_type="Repository / Store",
                responsibility="Manages relational schemas, transaction integrity, indexing, and backup persistence.",
                mapped_requirements=data_reqs or (core_reqs[5:8] if len(core_reqs) > 5 else ["NFR-001"])
            ),
            ArchitecturalComponent(
                name="Telemetry, Monitoring & Quality Guard",
                component_type="Cross-Cutting",
                responsibility="Collects performance metrics, audit logs, error traces, and health status.",
                mapped_requirements=infra_reqs or ["NFR-001", "NFR-002"]
            )
        ]
