"""
REQUIRE-X Base Agent Interface
Provides base classes, progress hooks, logging, and fallback mechanisms for specialized RE agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from require_x.agents.llm_provider import LLMProvider


class BaseAgent(ABC):
    """Abstract Base Class for all REQUIRE-X specialized AI agents."""

    def __init__(
        self,
        name: str,
        role: str,
        llm_provider: Optional[LLMProvider] = None,
        on_status_update: Optional[Callable[[str, str, str], None]] = None
    ):
        self.name = name
        self.role = role
        self.llm = llm_provider or LLMProvider(provider="offline")
        self.on_status_update = on_status_update
        self.logs: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """Logs an event and notifies the UI orchestrator."""
        formatted = f"[{self.name}] {message}"
        self.logs.append(formatted)
        if self.on_status_update:
            self.on_status_update(self.name, level, message)

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the agent's core responsibility on the shared workflow context."""
        pass
