from langgraph.graph.state import CompiledStateGraph

from agentic.workflow import AgentContext, state


def get_name() -> str:
    return "บ๊อบบี๊"


def get_display() -> str:
    return "Bobby AI"


def get_model() -> str:
    context = AgentContext()
    return context.AGENT_MODEL


def get_graph() -> CompiledStateGraph | None:
    return state.graph


def is_setup() -> bool:
    return state.is_setup
