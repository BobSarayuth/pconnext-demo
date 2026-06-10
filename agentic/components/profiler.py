import logging
import time

logger = logging.getLogger("profiler")


class ProfilerContext:
    def __init__(self, name: str, session_id: str | None = None) -> None:
        self.name = name
        self.session_id = session_id
        self.start_time = None
        self.profiling_data = {}

    def __enter__(self) -> "ProfilerContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if self.start_time is None:
            self.start_time = time.time()
        elapsed = time.time() - self.start_time
        self.profiling_data[self.name] = elapsed

    def mark(self, name: str) -> None:
        if self.start_time is None:
            self.start_time = time.time()
        elapsed = time.time() - self.start_time
        self.profiling_data[name] = elapsed
        logger.info(
            f"PROFILING: {name} reached at {elapsed:.4f}s",
            extra={"session_id": self.session_id} if self.session_id else {},
        )
        self.profiling_data[name] = elapsed
        logger.info(
            f"PROFILING: {name} reached at {elapsed:.4f}s",
            extra={"session_id": self.session_id} if self.session_id else {},
        )

    def get_results(self) -> dict:
        return self.profiling_data
