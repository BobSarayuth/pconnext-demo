import uvicorn

from agentic.workflow import setup_workflow
from chatapi.config.app import create_app_config, create_app_fastapi

if __name__ == "__main__":
    app = create_app_fastapi(
        setup_workflow=setup_workflow,
        title="Bobby AI",
        desc="AI Bot API Specification",
    )

    config = create_app_config()
    uvicorn.run(
        app,
        headers=[("server", config.log_name)],
        host=config.host,
        port=config.port,
        log_config=config.create_logger_config(),
    )
