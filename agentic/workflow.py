import json
import logging
from typing import Optional, Union

from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.graph.state import CompiledStateGraph
from langgraph.managed import IsLastStep, RemainingSteps
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentic.components.checkpoint import AsyncRedisSaver
from agentic.components.llm import LLMNode
from agentic.components.workflow import WorkflowState
from agentic.models.knowledge import formatLiteralList, getBasicKnowledge
from agentic.models.responsed import ActionType, EventType, MainResponded, MainTrusted
from agentic.tools import TOOLS, check_tools, execute_tool

logger = logging.getLogger("workflow")
tool_logger = logging.getLogger("workflow.tool_calls")
MAX_TOOL_LOG_CHARS = 4000

DEFAULT_MODEL_CONFIG = SettingsConfigDict(env_prefix="AGENTIC_")


class AgentContext(BaseSettings):
    AGENT_MODEL: str = "openai:gpt-4o-mini"
    SAFEGUARD_MODEL: str = "openai:gpt-4o-mini"
    CACHE_URI: str = "redis://localhost:6380"
    model_config = DEFAULT_MODEL_CONFIG


class AgentState(MessagesState):
    is_last_step: IsLastStep
    remaining_steps: RemainingSteps
    username: Optional[str]
    language: str
    ask_count: int
    has_error: bool
    prompt_config: Optional[dict]


class ResultState(MessagesState):
    artifact: Optional[MainResponded] | None


def find_messages_type(state: AgentState, message_type: str) -> AnyMessage:
    """Find all messages in state that match the specified type."""
    for msg in reversed(state["messages"]):
        if msg.type == message_type and msg.content:
            return msg

    return state["messages"][-1]


def is_reset_request(state: AgentState) -> bool:
    messages = state.get("messages") or []
    if not messages:
        return False
    last_message = messages[-1]
    return last_message.type == "human" and isinstance(last_message.content, str) and last_message.content.strip().lower() == "reset"


def _truncate_tool_log(value, max_chars: int = MAX_TOOL_LOG_CHARS) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)

    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...<truncated {len(text) - max_chars} chars>"


def log_tool_messages(messages: list[AnyMessage]) -> None:
    tool_calls: dict[str, dict] = {}

    for msg in messages:
        for call in getattr(msg, "tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            call_id = str(call.get("id") or "")
            name = call.get("name") or "unknown"
            args = call.get("args") or {}
            if call_id:
                tool_calls[call_id] = {"name": name, "args": args}
            tool_logger.info(
                "tool_call name=%s args=%s",
                name,
                _truncate_tool_log(args),
            )

    for msg in messages:
        if getattr(msg, "type", None) != "tool":
            continue
        call_id = str(getattr(msg, "tool_call_id", "") or "")
        call = tool_calls.get(call_id, {})
        content = getattr(msg, "content", "")
        artifact = getattr(msg, "artifact", None)
        tool_logger.info(
            "tool_result name=%s content=%s artifact=%s",
            call.get("name", "unknown"),
            _truncate_tool_log(content),
            _truncate_tool_log(artifact),
        )


async def clearly_response(llm, message: str):
    translate = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": "Make it short, clear, and grammatically correct. Ensure it answers the question directly.",
            },
            {"role": "human", "content": message},
        ]
    )
    return translate.content


def get_prompt_config(_config: RunnableConfig) -> dict:
    return {}


def render_main_prompt(llm: LLMNode, prompt_config: dict | None = None) -> str:
    basic_knowledge = formatLiteralList(getBasicKnowledge())
    return llm.get_prompt(prompt_config).replace("{BasicKnowledge}", basic_knowledge)


def init_main_thought(context: AgentContext) -> CompiledStateGraph:
    llm = LLMNode(template_name="llm_main_thought.md", fully_name=context.AGENT_MODEL)

    chosen_tools = check_tools(
        [
            "calculator",
            "faq",
            # Product Search and Information
            "skim_products",
            "search_specific_product",
            # Agent Handoff
            "switch_agent_fasttrack",
        ]
    )

    def prompt(state: AgentState):
        return [SystemMessage(content=render_main_prompt(llm, state.get("prompt_config"))), *state["messages"]]

    return create_react_agent(
        name="agent",
        model=llm.get_model(
            context.AGENT_MODEL,
            meta={"temperature": 0, "top_p": 0.7, "parallel_tool_calls": False},
        ),
        tools=chosen_tools,
        prompt=prompt,
        state_schema=AgentState,
        config_schema=RunnableConfig,
    )


def init_main_trusted(context: AgentContext):
    return LLMNode(template_name="llm_main_trusted.md", fully_name=context.SAFEGUARD_MODEL)


MAX_ATTEMPT = 5
ERROR_MESSAGE = {
    "MAX_ATTEMPT": "ขออภัยครับ บ๊อบบี๊ไม่สามารถให้คำตอบคุณลูกค้าได้ บ๊อบบี๊กำลังส่งข้อมูลต่อให้พี่ๆเจ้าหน้าที่ SCG Digital นะครับ"
}

COMMAND_NEXT = {
    "tool_calls": {
        "Thai": "โฟกัสกับการค้นหาและเรียกใช้เครื่องมือที่ถูกต้อง",
        "English": "Stay focused on finding and retrieving the right tools.",
    },
    "used_tools": [
        "คุณยังไม่ได้ใช้เครื่องมือใดๆ ในการค้นหา",
        "ระบบยังไม่พบการใช้เครื่องมือค้นหาใด ๆ",
        "ใช้เครื่องมืิอ `skim_product` เดี๋ยวนี้",
        "ยังไม่มีการเรียกใช้เครื่องมือค้นหาใด ๆ เลย",
        "เริ่มต้นการค้นหาด้วยเครื่องมือที่มีอยู่ทันที",
        "เริ่มใช้เครื่องมือ ในการค้นหา ทันที",
    ],
}

_INJECTION_PATTERNS = (
    "<script",
    "</script>",
    "eval(",
    "exec(",
    "SELECT * FROM",
    "DROP TABLE",
    "UNION SELECT",
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
)
_TOOL_NAMES_LOWER = frozenset(name.lower() for name in TOOLS.keys())


def is_prompt_injection(content) -> bool:
    """Heuristic short-circuit for prompt/code injection in user input."""
    if not content or not isinstance(content, str):
        return False
    lowered = content.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern.lower() in lowered:
            logger.warning(f"Prompt injection pattern matched: {pattern!r}")
            return True
    for tool_name in _TOOL_NAMES_LOWER:
        if tool_name in lowered:
            logger.warning(f"Prompt injection tool name matched: {tool_name!r}")
            return True
    return False


def set_state_fixed(state: AgentState, reason: MainTrusted, ATTEMPT):
    if reason.query or reason.event == EventType.TOOL_CALLS:
        state["messages"].append(SystemMessage(content=COMMAND_NEXT["tool_calls"]["Thai"]))

    logger.info(f"ATTEMPT: {ATTEMPT}")
    if 0 <= ATTEMPT < len(COMMAND_NEXT["used_tools"]):
        state["messages"].append(HumanMessage(content=COMMAND_NEXT["used_tools"][ATTEMPT]))


async def get_translate_language(react_llm, language: str, content: str) -> AIMessage:
    logger.info(f"translate to: {language}")
    if language == "Thai":
        return AIMessage(content)

    llm = react_llm.get_model(None, {"streaming": False})
    prompt = (
        "No questions to be answered,"
        "All you have to do is translate language to English"
        ", and If it is already in the English language, you can just return it to its original state."
        "\n **special names** "
        '\n - "บ๊อบบี๊" is mean Bobby'
    )
    translate = await llm.ainvoke([HumanMessage(content), SystemMessage(content=prompt)])
    return translate


def set_state_event(state: AgentState, reason: MainTrusted):
    if state.get("ask_count") and reason.event == EventType.CONFIRM_OPTION:
        state["ask_count"] += 1
    else:
        state["ask_count"] = 1


def set_prompt_username(state: AgentState, config: RunnableConfig):
    state["username"] = config.get("configurable", {}).get("username", "")
    state["messages"].append(
        SystemMessage(
            content=f"USER nickname is '{state['username']}', They are talking to you. (Do not translate the nickname.)"
        )
    )


async def handle_sticker_feeling(state: AgentState, react_agent: CompiledStateGraph, config: RunnableConfig):
    """Handle customer sticker messages and return appropriate responses."""
    state["messages"].append(
        SystemMessage(
            content="Acknowledge how users are feeling, saying comforting things to them if they are sad or angry, and expressing gratitude if they are feeling positive."
        )
    )
    return await react_agent.ainvoke(state, config)  # type: ignore


def _get_index_state(state, type: str):
    human_indices = [i for i, msg in enumerate(reversed(state["messages"])) if msg.type == type]
    return human_indices[0] if human_indices else 0


def _process_agent_response(state: AgentState, trusted: MainTrusted, ATTEMPT):
    # Log information for debugging
    human_idx = _get_index_state(state, "human") * -1
    if human_idx == 0:
        return False

    if "tool" not in [msg.type for msg in state["messages"][human_idx:]]:
        if trusted.event in [EventType.OPTION_PICKUP, EventType.TOOL_CALLS] or (
            trusted.query
            and trusted.event
            not in [EventType.CONTACT_OPERATOR, EventType.CONFIRM_OPTION, EventType.FOLLOW_UP, EventType.ASSISTANCE]
        ):
            state["messages"] = state["messages"][:-1]
            set_state_fixed(state, trusted, ATTEMPT)
            return False

    return True


CUSTOMER_STICKER_SENDED = "customer_send_sticker"


async def _error_switch_agent_state(state: AgentState, name: str, react_llm):
    """Handle error state by switching to fasttrack agent and providing error message to the user."""
    tool_message, tool_call = execute_tool(
        "switch_agent_fasttrack",
        {"situation_summary": "Unable to provide an answer", "fasttrack": False, "negative": False},
    )
    msg = await get_translate_language(react_llm, state.get("language", "Thai"), ERROR_MESSAGE["MAX_ATTEMPT"])
    switch_message = AIMessage(name=name, content=msg.content)  # type: ignore

    state["messages"].append(AIMessage(name=name, content="", tool_calls=[tool_call]))
    state["messages"].append(tool_message)
    state["messages"].append(switch_message)

    return state


def init_agent(state: AgentState, config: RunnableConfig):
    state["has_error"] = False
    state["prompt_config"] = get_prompt_config(config)
    identify = config.get("configurable", {}).get("content_type", [])
    logger.info(f"content-identify: {identify}")
    for name in identify:
        if name not in ["TEXT"]:
            system_prompt = LLMNode(template_name=f"content-identify/{name.lower()}.md").get_prompt(
                state.get("prompt_config")
            )
            if system_prompt:
                state["messages"].append(SystemMessage(content=system_prompt))

    if state.get("username"):
        set_prompt_username(state, config)

    return state


async def agent_invocation(  # noqa: C901
    state: AgentState, config: RunnableConfig, llm: BaseChatModel, trusted_prompt: str, react_agent: CompiledStateGraph
):
    """Invoke the agent with the given state"""
    try:
        state = init_agent(state, config)
        human_message = find_messages_type(state, "human")
        ATTEMPT = 0
        LEN_CHECK = False

        if isinstance(human_message.content, str) and is_prompt_injection(human_message.content):
            logger.warning("Prompt injection detected — routing to operator handoff")
            state["has_error"] = True
            return state

        if not state.get("language") and isinstance(human_message.content, str):
            system_prompt = SystemMessage(
                content=LLMNode(template_name="llm_language.md").get_prompt(state.get("prompt_config"))
            )
            try:
                resp = await llm.ainvoke([system_prompt, human_message])
                detected = str(resp.content).strip().lower()
                state["language"] = "Thai" if detected.startswith("thai") else "English"
            except Exception as ex:
                logger.warning(f"Language detection failed, defaulting to Thai: {ex}")
                state["language"] = "Thai"

        while ATTEMPT < MAX_ATTEMPT:
            try:
                # {**config.get('metadata', {}), "temperature": 1}
                previous_message_count = len(state["messages"])
                state = await react_agent.ainvoke(state, config)  # type: ignore
                log_tool_messages(state["messages"][previous_message_count:])

                # if state["messages"][-1].content:
                #     continue

                last_message = find_messages_type(state, "ai")
                metadata = last_message.response_metadata

                print(f"responsed: {len(state['messages'][-1].content)} char")

                if len(state["messages"][-1].content) == 0:
                    ATTEMPT += 1
                    continue

                if len(state["messages"][-1].content) > 1900:
                    state["messages"].pop()
                    if not LEN_CHECK:
                        state["messages"].append(
                            HumanMessage(
                                content="Summarize the details clearly and concisely and include the product URL, with a length not exceeding 1,800 characters."
                            )
                        )
                        LEN_CHECK = True

                    ATTEMPT += 1
                    continue

                finish_reason = metadata.get("finish_reason")
                if finish_reason and str(finish_reason).upper() != "STOP":
                    raise Exception(f"AI {finish_reason}: {finish_reason}")

                trusted = await llm.with_structured_output(MainTrusted).ainvoke(
                    [SystemMessage(content=trusted_prompt), AIMessage(content=last_message.content)]
                )
                if trusted is None:
                    logger.warning("MainTrusted structured output returned None, using default values")
                    trusted = MainTrusted(query=False)
                else:
                    trusted = MainTrusted(**trusted.__dict__)

                set_state_event(state, trusted)

                # fix bug cache in google
                if _process_agent_response(state, trusted, ATTEMPT):
                    break
                ATTEMPT += 1

            except Exception as ex:
                if state["messages"][-1].type in "ai":
                    state["messages"].pop()
                logger.error(ex)
                ATTEMPT += 1
                continue

        state["has_error"] = ATTEMPT >= MAX_ATTEMPT

    except Exception as ex:
        logger.error(ex)
        state["has_error"] = True

    return state


# {"name": "skim_products", "args": {"search_term": "บังไบ"}, "id": "82f2ee90-60b9-45b2-9c95-c5b64dac5077", "type": "tool_call"}
def _process_switch_agent_message(msg, responded):
    """Process switch_agent_fasttrack tool message"""

    if not responded:
        responded = MainResponded(action=ActionType.NORMAL)

    if isinstance(msg.artifact, dict):
        responded.action = msg.artifact.get("mode", ActionType.AGENT)
    elif isinstance(msg.artifact, list):
        responded.action = msg.artifact[0].get("mode", ActionType.AGENT)

    return responded


def _process_tool_messages(messages):
    """Process tool messages and extract relevant artifacts"""
    responded = None

    for msg in reversed(messages):
        # Skip if msg is not a message object (e.g., Command object)
        if not hasattr(msg, "type"):
            # responded = MainResponded(action=ActionType.NORMAL)
            # if isinstance(messages[0].artifact, dict):
            #     responded.action = messages[0].artifact.get("mode", ActionType.AGENT)

            continue

        if msg.type == "human" and msg.content:
            break

        if msg.type == "tool" and msg.tool_call_id:
            responded = _process_switch_agent_message(msg, responded)
    print(f"responded: {responded}")
    return responded


async def responded(state: AgentState, llm: LLMNode) -> Union[Command, AgentState, ResultState]:
    if state["has_error"]:
        state = await _error_switch_agent_state(state, "responded", llm)

    if state.get("language", "Thai") != "Thai":
        state["messages"].append(
            await get_translate_language(llm, state.get("language"), str(state["messages"][-1].content))
        )

    responded_artifact = _process_tool_messages(state["messages"])
    return ResultState(messages=state["messages"], artifact=responded_artifact)


# def safeguard(state: AgentState, context: AgentContext) -> ResultState:
#     prompt = retrieve_safeguard_prompt()
#     last_ai_message = next(
#         (msg for msg in reversed(state["messages"]) if isinstance(msg, AIMessage)),
#         AIMessage(content="I need to talk to a customer service agent."),
#     )

#     safe_guard = [SystemMessage(content=prompt)] + [last_ai_message]
#     guard_llm = llm_provider(
#         provider_model=context.SAFEGUARD_MODEL,
#     ).with_structured_output(AgentCustomResponse)

#     result = guard_llm.ainvoke(safe_guard)
#     result_value = construct_result(last_ai_message, result)
#     return ResultState(messages=state["messages"], result=result_value)


state = WorkflowState()


# Set up the workflow by creating the nodes and adding edges
async def setup_workflow():
    """Set up the workflow by creating the nodes and adding edges"""
    global state

    context = AgentContext()
    state.model = context.AGENT_MODEL

    workflow = StateGraph(AgentState, output=ResultState)

    main_thought = init_main_thought(context)
    main_trusted = init_main_trusted(context)

    llm = main_trusted.get_model(None, {"streaming": False})

    # Create async wrapper function for agent_invocation
    async def agent_node(state, config):
        prompt_config = get_prompt_config(config)
        return await agent_invocation(
            state=state,
            config=config,
            llm=llm,
            trusted_prompt=main_trusted.get_prompt(prompt_config),
            react_agent=main_thought,
        )

    async def reset_node(state, config):
        thread_id = config.get("configurable", {}).get("thread_id")
        deleted = await checkpointer.adel_tuple(thread_id) if thread_id else 0
        logger.info("chat history reset thread_id=%s deleted_keys=%s", thread_id, deleted)
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                AIMessage(content="เริ่มต้นการสนทนาใหม่เรียบร้อยแล้วครับ"),
            ],
            "language": "Thai",
            "ask_count": 0,
            "has_error": False,
            "prompt_config": get_prompt_config(config),
        }

    def route_start(state):
        return "reset" if is_reset_request(state) else "agent"

    async def responded_node(state):
        return await responded(state=state, llm=main_trusted)

    workflow.add_node("agent", RunnableLambda(agent_node))
    workflow.add_node("reset", RunnableLambda(reset_node))
    workflow.add_node("responded", RunnableLambda(responded_node))

    # workflow.add_node("safeguard", lambda state: safeguard(state=state, context=context))

    workflow.add_conditional_edges(START, route_start, {"reset": "reset", "agent": "agent"})
    # workflow.add_edge(START, "init")
    # workflow.add_edge("init", "agent")
    workflow.add_edge("reset", "responded")
    workflow.add_edge("agent", "responded")
    workflow.add_edge("responded", END)

    logger.info("setup workflow")

    async with AsyncRedisSaver.from_conn_uri(uri=context.CACHE_URI) as checkpointer:
        state.graph = workflow.compile(checkpointer=checkpointer)
        state.is_setup = True
