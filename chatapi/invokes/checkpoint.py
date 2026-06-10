import logging

from agentic import get_graph

logger = logging.getLogger("fastapi.checkpoint")


async def checkpoint_delete(session_id: str | list[str]) -> str:
    graph = get_graph()
    _affected = await graph.checkpointer.adel_tuple(session_id)  # type: ignore

    logger.info(f"affected {_affected} rows", extra={"session_id": session_id})
    return f"affected {_affected} rows"


async def checkpoint_flush() -> None:
    graph = get_graph()
    await graph.checkpointer.aflushdb()  # type: ignore
