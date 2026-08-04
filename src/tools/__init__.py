from src.tools.k8s_tools import get_k8s_tools
from src.tools.log_reader import get_log_tools

ACTION_TOOL_NAMES = {"restart_kubernetes_pod"}


def get_agent_tools() -> list:
    """Get every tool available to the agent."""
    return get_log_tools() + get_k8s_tools()


__all__ = ["ACTION_TOOL_NAMES", "get_agent_tools", "get_log_tools", "get_k8s_tools"]
