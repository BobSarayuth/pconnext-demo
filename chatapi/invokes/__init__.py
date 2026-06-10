import hashlib

from langchain_core.runnables import RunnableConfig


def create_config(session_id: str, config: dict, content_type: list[str]) -> RunnableConfig:
    username = config.get("username", None)
    built = {
        "trace_id": session_id,
        "session_id": session_id,
        "thread_id": session_id,
        "user_id": hashlib.sha256(username.encode()).hexdigest() if username else None,
        "username": username,
        "content_type": content_type,
    }
    return RunnableConfig({"configurable": {**config, **built}})
