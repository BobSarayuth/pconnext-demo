from langgraph.graph.state import CompiledStateGraph


class WorkflowState:
    def __init__(self) -> None:
        self._model: str = "N/A"
        self._graph: CompiledStateGraph | None
        self._is_setup: bool = False

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @property
    def is_setup(self) -> bool:
        return self._is_setup

    @is_setup.setter
    def is_setup(self, value: bool) -> None:
        self._is_setup = value

    @property
    def graph(self) -> CompiledStateGraph | None:
        return self._graph

    @graph.setter
    def graph(self, value: CompiledStateGraph) -> None:
        self._graph = value

    @graph.getter
    def graph(self) -> CompiledStateGraph:
        if not self._graph:
            raise Exception("Graph not initialized. Please run 'setup_workflow' first.")

        return self._graph
