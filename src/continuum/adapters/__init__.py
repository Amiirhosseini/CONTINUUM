"""Framework adapters for CONTINUUM."""

from continuum.adapters.actions import (
    AdapterAction,
    AdapterResult,
    run_action,
)
from continuum.adapters.base import AgentAdapter
from continuum.adapters.browser import BrowserAdapter
from continuum.adapters.container import ContainerAdapter
from continuum.adapters.filesystem import FilesystemSandboxAdapter
from continuum.adapters.generic import GenericAgentAdapter
from continuum.adapters.kubernetes import KubernetesAdapter
from continuum.adapters.langchain import LangChainAgentAdapter, langchain_available
from continuum.adapters.langgraph import LangGraphAgentAdapter, langgraph_available
from continuum.adapters.openai import ContinuumContext, OpenAIAgentAdapter, openai_agents_available
from continuum.adapters.python_inproc import PythonInProcAdapter
from continuum.adapters.registry import (
    AdapterRegistry,
    get_adapter,
    list_adapters,
    recover,
    register_adapter,
)

__all__ = [
    "AdapterAction",
    "AdapterRegistry",
    "AdapterResult",
    "AgentAdapter",
    "BrowserAdapter",
    "ContainerAdapter",
    "ContinuumContext",
    "FilesystemSandboxAdapter",
    "GenericAgentAdapter",
    "KubernetesAdapter",
    "LangChainAgentAdapter",
    "LangGraphAgentAdapter",
    "OpenAIAgentAdapter",
    "PythonInProcAdapter",
    "get_adapter",
    "langchain_available",
    "langgraph_available",
    "list_adapters",
    "openai_agents_available",
    "recover",
    "register_adapter",
    "run_action",
]
