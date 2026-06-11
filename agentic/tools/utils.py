import hashlib
import logging
import os
import re
import threading
import time
from typing import Any

import httpx
import redis
from langchain_core.messages import AnyMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import ToolException
from langgraph.types import Command
from pydantic_settings import BaseSettings, SettingsConfigDict

from chatapi.config.logger import CTX_TRACE_ID, HEADER_TRACE_NAME

# Reusable HTTPX client
_client = httpx.Client(
    verify=False,  # noqa: S501
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
)


class ContentServiceConfig(BaseSettings):
    SERVICE_URL: str = "http://localhost:8000"
    TOKEN_URL: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    AUDIENCE: str = ""
    KNOWLEDGE_INDEX: str = "home-content-article"
    model_config = SettingsConfigDict(env_prefix="CAP_CONTENT_")


MAX_RETRY = 3
TOKEN_REFRESH_MARGIN_SECONDS = 60
TOKEN_CACHE_KEY_PREFIX = "content_service:token"
SKU_QUERY_MAX_SIZE = 100
SKU_INDEX_NAME = "cpo-sku-dev"
SKU_SEARCH_FIELDS = [
    "product_sku_id",
    "id",
    "code",
    "name",
    "description",
    "search_keyword",
    "active",
]
SKU_SEMANTIC_WEIGHT = 0.75
SKU_LEXICAL_WEIGHT = 0.25
RRF_K = 60
FAQ_CONTAINER_KEYS = {
    "faq",
    "faqs",
    "product_faq",
    "product_faqs",
    "frequently_asked_questions",
    "question_answer",
    "question_answers",
    "questions",
    "answers",
    "question_list",
    "answer_list",
    "qa",
    "qas",
    "q&a",
    "คำถาม",
    "คำตอบ",
    "คำถามที่พบบ่อย",
}
FAQ_QUESTION_KEYS = {"question", "questions", "q", "title", "topic", "คำถาม"}
FAQ_ANSWER_KEYS = {"answer", "answers", "a", "content", "detail", "details", "description", "คำตอบ"}

_content_service_token_cache: dict[str, str | float] = {"access_token": "", "expires_at": 0.0, "cache_key": ""}
_content_service_token_lock = threading.Lock()
_content_service_redis_client: redis.Redis | None = None
_content_service_redis_client_lock = threading.Lock()


def _get_content_service_redis_client() -> redis.Redis | None:
    cache_uri = os.getenv("CAP_CONTENT_TOKEN_CACHE_URI") or os.getenv("AGENTIC_CACHE_URI") or ""
    if not cache_uri:
        return None

    global _content_service_redis_client
    if _content_service_redis_client is not None:
        return _content_service_redis_client

    with _content_service_redis_client_lock:
        if _content_service_redis_client is None:
            _content_service_redis_client = redis.Redis.from_url(cache_uri, decode_responses=True)
        return _content_service_redis_client


class ContentService:
    def __init__(self) -> None:
        config = ContentServiceConfig()
        self.config = config
        self.base_url = config.SERVICE_URL
        base_url = self.base_url.rstrip("/")
        token_url = config.TOKEN_URL.rstrip("/") if config.TOKEN_URL else ""
        self.token_url = f"{token_url or base_url}/api/oauth2/token" if token_url in ("", base_url) else token_url
        self.token_cache_key = f"{self.token_url}|{config.CLIENT_ID}|{config.AUDIENCE}"
        cache_key_digest = hashlib.sha256(self.token_cache_key.encode()).hexdigest()
        self.redis_token_cache_key = f"{TOKEN_CACHE_KEY_PREFIX}:{cache_key_digest}"

    def _request_access_token(self) -> tuple[str, float]:
        if not self.config.CLIENT_ID or not self.config.CLIENT_SECRET or not self.config.AUDIENCE:
            raise ToolException("Content service auth error: client_id, client_secret, or audience is missing")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.CLIENT_ID,
            "client_secret": self.config.CLIENT_SECRET,
            "audience": self.config.AUDIENCE,
        }
        res = _client.post(self.token_url, json=payload)
        logger = logging.getLogger("content_service")
        logger.info("Content service token request completed with status %s", res.status_code)
        res.raise_for_status()

        token_data = res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            logger.error("Content service token response missing access_token")
            raise ToolException("Content service auth error: access_token is missing")

        expires_in = int(token_data.get("expires_in", 3600))
        expires_at = time.time() + max(expires_in - TOKEN_REFRESH_MARGIN_SECONDS, 0)
        logger.info("Content service token acquired successfully; expires_in=%s", expires_in)
        return access_token, expires_at

    def _get_memory_access_token(self) -> str:
        cached_token = str(_content_service_token_cache.get("access_token") or "")
        cached_expires_at = float(_content_service_token_cache.get("expires_at") or 0)
        cached_key = str(_content_service_token_cache.get("cache_key") or "")
        if cached_token and cached_key == self.token_cache_key and cached_expires_at > time.time():
            ttl_seconds = max(int(cached_expires_at - time.time()), 0)
            logging.getLogger("content_service").info("Content service token cache hit (memory); ttl=%s", ttl_seconds)
            return cached_token
        return ""

    def _get_redis_access_token(self) -> str:
        logger = logging.getLogger("content_service")
        redis_client = _get_content_service_redis_client()
        if redis_client is None:
            return ""

        try:
            cached_token = redis_client.get(self.redis_token_cache_key)
            if not cached_token:
                return ""

            ttl_seconds = redis_client.ttl(self.redis_token_cache_key)
            if ttl_seconds <= 0:
                redis_client.delete(self.redis_token_cache_key)
                return ""

            expires_at = time.time() + max(ttl_seconds, 0)
            _content_service_token_cache["access_token"] = cached_token
            _content_service_token_cache["expires_at"] = expires_at
            _content_service_token_cache["cache_key"] = self.token_cache_key
            logger.info("Content service token cache hit (redis); ttl=%s", ttl_seconds)
            return cached_token
        except redis.RedisError as exc:
            logger.warning("Content service token redis cache read failed: %s", exc)
            return ""

    def _get_cached_access_token(self) -> str:
        return self._get_memory_access_token() or self._get_redis_access_token()

    def _store_access_token(self, access_token: str, expires_at: float) -> None:
        logger = logging.getLogger("content_service")
        ttl_seconds = max(int(expires_at - time.time()), 1)
        _content_service_token_cache["access_token"] = access_token
        _content_service_token_cache["expires_at"] = time.time() + ttl_seconds
        _content_service_token_cache["cache_key"] = self.token_cache_key

        redis_client = _get_content_service_redis_client()
        if redis_client is None:
            logger.info("Content service token cached in memory; ttl=%s", ttl_seconds)
            return

        try:
            redis_client.set(self.redis_token_cache_key, access_token, ex=ttl_seconds)
            logger.info("Content service token cached in redis; ttl=%s", ttl_seconds)
        except redis.RedisError as exc:
            logger.warning("Content service token redis cache write failed: %s", exc)

    def _get_access_token(self) -> str:
        cached_token = self._get_cached_access_token()
        if cached_token:
            return cached_token

        with _content_service_token_lock:
            cached_token = self._get_cached_access_token()
            if cached_token:
                return cached_token

            logging.getLogger("content_service").info("Content service token cache miss; requesting new token")
            access_token, expires_at = self._request_access_token()
            self._store_access_token(access_token, expires_at)
            return access_token

    def _clear_access_token(self) -> None:
        with _content_service_token_lock:
            _content_service_token_cache["access_token"] = ""
            _content_service_token_cache["expires_at"] = 0.0
            _content_service_token_cache["cache_key"] = ""
            redis_client = _get_content_service_redis_client()
            if redis_client is not None:
                try:
                    redis_client.delete(self.redis_token_cache_key)
                except redis.RedisError as exc:
                    logging.getLogger("content_service").warning(
                        "Content service token redis cache delete failed: %s", exc
                    )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            HEADER_TRACE_NAME: CTX_TRACE_ID.get() if CTX_TRACE_ID.get() else "",
        }

    def _get(self, endpoint: str, params: dict) -> httpx.Response:
        res = _client.get(endpoint, params=params, headers=self._headers())
        if res.status_code != 401:
            return res

        self._clear_access_token()
        return _client.get(endpoint, params=params, headers=self._headers())

    def _post(self, endpoint: str, body: dict) -> httpx.Response:
        res = _client.post(endpoint, json=body, headers=self._headers())
        if res.status_code != 401:
            return res

        self._clear_access_token()
        return _client.post(endpoint, json=body, headers=self._headers())

    def _parse_response(self, res: httpx.Response, barcode: str) -> dict:
        if res.status_code != 200:
            return {"barcode": barcode, "price": None, "note": f"API error: {res.status_code} => {res.text}"}

        json_data = res.json()
        if not json_data.get("success"):
            return {"barcode": barcode, "price": None, "note": f"Unsuccessful response: {json_data}"}

        prices = [i.get("price") for i in json_data.get("data", []) if isinstance(i.get("price"), int | float)]
        if not prices:
            return {"barcode": barcode, "price": None, "note": "No valid numeric price found"}

        return {"barcode": barcode, "price": min(prices), "note": ""}

    def _query_sku_index(self, body: dict) -> dict:
        endpoint = f"{self.base_url.rstrip('/')}/api/km/v1/query/{SKU_INDEX_NAME}"
        res = self._post(endpoint, body)
        if res.status_code != 200:
            raise ToolException(f"SKU content API error {res.status_code}: {res.text}")
        return res.json()

    def search_sku_products_by_name(self, name: str, limit: int) -> tuple[list[dict], str | None]:
        text = normalize_search_text(name)
        if not text:
            return [], None

        result_limit = min(max(limit, 1), SKU_QUERY_MAX_SIZE)
        fetch_k = min(max(result_limit * 3, result_limit), SKU_QUERY_MAX_SIZE)
        filters = [{"term": {"active": True}}]
        source = {"includes": SKU_SEARCH_FIELDS}
        semantic_hits = self._query_sku_index(
            _semantic_sku_query(text, source, fetch_k, filters)
        ).get("hits", {}).get("hits", [])
        lexical_hits = self._query_sku_index(
            _lexical_sku_query(text, source, fetch_k, filters)
        ).get("hits", {}).get("hits", [])
        rows = merge_hits_by_weighted_rrf(
            [(semantic_hits, SKU_SEMANTIC_WEIGHT), (lexical_hits, SKU_LEXICAL_WEIGHT)],
            result_limit,
            ("_id",),
        )
        return [_sku_hit_to_product(row, rank) for rank, row in enumerate(rows, start=1)], None

    def search_sku_products_by_id(self, sku_id: str, limit: int = 1) -> tuple[list[dict], str | None]:
        text = normalize_search_text(sku_id)
        if not text:
            return [], None

        result_limit = min(max(limit, 1), SKU_QUERY_MAX_SIZE)
        hits = self._query_sku_index(_sku_id_query(text, True, result_limit)).get("hits", {}).get("hits", [])
        return [_sku_hit_to_detail(hit, rank) for rank, hit in enumerate(hits, start=1)], None

def normalize_product_name(name: str) -> str:
    """
    Normalize a product name to avoid mismatches caused by extra spaces,
    different kinds of whitespace, or case differences.
    """
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:2000]


def extract_strong_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for candidate in re.findall(r"\b(?=[A-Za-z0-9./_-]*\d)[A-Za-z0-9][A-Za-z0-9./_-]{2,}\b", text):
        token = candidate.strip(".,;:()[]{}")
        if len(token) < 4 or token.lower() in seen:
            continue
        seen.add(token.lower())
        tokens.append(token)
        if len(tokens) == 8:
            break
    return tokens


def _semantic_sku_query(
    text: str,
    source: bool | list[str] | dict[str, Any],
    size: int,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    clause = {"semantic": {"field": "embed_description", "query": text}}
    query = {"bool": {"must": [clause], "filter": filters}} if filters else clause
    return {"size": size, "_source": source, "query": query}


def _lexical_sku_query(
    text: str,
    source: bool | list[str] | dict[str, Any],
    size: int,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bool_query: dict[str, Any] = {"should": _sku_clauses(text), "minimum_should_match": 1}
    if filters:
        bool_query["filter"] = filters
    return {"size": size, "_source": source, "query": {"bool": bool_query}}


def _sku_clauses(text: str) -> list[dict[str, Any]]:
    clauses = []
    if text.isdigit():
        clauses += [
            {"term": {"_id": {"value": text, "boost": 20}}},
            {"term": {"id": {"value": text, "boost": 16}}},
        ]
    for token in extract_strong_tokens(text):
        clauses += [
            {"match_phrase": {"code": {"query": token, "boost": 12}}},
            {"match_phrase": {"search_keyword": {"query": token, "boost": 10}}},
        ]
    return clauses + [
        {"match_phrase": {"code": {"query": text, "boost": 8}}},
        {"match_phrase": {"search_keyword": {"query": text, "boost": 7}}},
        {"match_phrase": {"name": {"query": text, "boost": 5}}},
        {"match_phrase": {"description": {"query": text, "boost": 5}}},
        {"match": {"code": {"query": text, "boost": 5}}},
        {"match": {"search_keyword": {"query": text, "boost": 4}}},
        {"match": {"name": {"query": text, "boost": 3}}},
        {"match": {"description": {"query": text, "boost": 2}}},
        {"match": {"DESCRIPTION": {"query": text, "boost": 2}}},
        {"match": {"ITEMTEXT": {"query": text, "boost": 2}}},
    ]


def _sku_id_query(
    sku_id: str,
    source: bool | list[str] | dict[str, Any],
    size: int,
) -> dict[str, Any]:
    return {
        "size": size,
        "_source": source,
        "query": {
            "bool": {
                "filter": [{"term": {"active": True}}],
                "should": [
                    {"term": {"_id": {"value": sku_id, "boost": 20}}},
                    {"term": {"id": {"value": sku_id, "boost": 16}}},
                    {"term": {"product_sku_id": {"value": sku_id, "boost": 16}}},
                    {"term": {"code": {"value": sku_id, "boost": 12}}},
                ],
                "minimum_should_match": 1,
            }
        },
    }


def merge_hits_by_weighted_rrf(
    hit_groups: list[tuple[list[dict[str, Any]], float]],
    top_k: int,
    id_path: tuple[str, ...],
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    best_hits: dict[str, dict[str, Any]] = {}
    for hits, weight in hit_groups:
        for rank, hit in enumerate(hits, start=1):
            item_id = _nested_value(hit, id_path)
            if item_id in (None, ""):
                continue
            key = str(item_id)
            scores[key] = scores.get(key, 0.0) + weight / (RRF_K + rank)
            best_hits.setdefault(key, hit)
    ordered_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [{"id": key, "score": scores[key], "hit": best_hits[key]} for key in ordered_keys[:top_k]]


def _nested_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def normalize_markdown(text: str) -> str:
    """
    Replaces multiple consecutive newlines and carriage returns with a single newline.
    """
    return re.sub(r"(\r\n|\n)+", "\n", text)


def _sku_hit_to_product(row: dict[str, Any], rank: int) -> dict[str, Any]:
    hit = row.get("hit", {})
    source = hit.get("_source", {}) if isinstance(hit, dict) else {}
    sku_id = str(source.get("product_sku_id") or source.get("id") or row.get("id") or "").strip()
    name = _text_value(source.get("name")) or _text_value(source.get("description")) or sku_id
    product = {
        "display_name_th": name,
        "description": _text_value(source.get("description")),
        "code": source.get("code"),
        "search_keyword": source.get("search_keyword"),
        "active": source.get("active"),
        "metadata": {
            "score": row.get("score"),
            "search_rank": rank,
            "product_sku_id": sku_id,
            "code": source.get("code"),
        },
    }
    return product


def _sku_hit_to_detail(hit: dict[str, Any], rank: int) -> dict[str, Any]:
    source = dict(hit.get("_source", {}) or {})
    sku_id = str(source.get("product_sku_id") or source.get("id") or hit.get("_id") or "").strip()
    metadata = dict(source.get("metadata") or {})
    metadata.update(
        {
            "score": hit.get("_score"),
            "search_rank": rank,
            "product_sku_id": sku_id,
            "code": source.get("code"),
        }
    )
    source["metadata"] = metadata
    product_faq = extract_product_faq(source)
    if product_faq:
        source["product_faq"] = product_faq
    return source


def _text_value(value) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or "")
    return str(value or "")


def extract_product_faq(source: dict[str, Any]) -> list[dict[str, str]]:
    faqs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(question: Any, answer: Any) -> None:
        question_text = _text_value(question).strip()
        answer_text = _text_value(answer).strip()
        if not question_text and not answer_text:
            return
        key = (question_text.lower(), answer_text.lower())
        if key in seen:
            return
        seen.add(key)
        faqs.append({"question": question_text, "answer": answer_text})

    def key_name(value: Any) -> str:
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    def normalize_candidate(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                normalize_candidate(item)
            return
        if isinstance(value, dict):
            question = next((value.get(key) for key in value if key_name(key) in FAQ_QUESTION_KEYS), "")
            answer = next((value.get(key) for key in value if key_name(key) in FAQ_ANSWER_KEYS), "")
            if question or answer:
                add(question, answer)
                return
            for item in value.values():
                normalize_candidate(item)
            return
        if isinstance(value, str):
            add("", value)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = key_name(key)
                if normalized_key in FAQ_CONTAINER_KEYS or "faq" in normalized_key:
                    normalize_candidate(item)
                elif isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(source)
    return faqs[:20]


def tool_exception_react(err: str, tool_call_id: str) -> Command:
    return Command(
        goto="agent",
        update={
            "messages": [
                SystemMessage("Contact Team Online operator now due to system error."),
                ToolMessage(err, tool_call_id=tool_call_id),
            ],
        },
    )


def tool_exception_tuple(err: str) -> tuple[str, dict]:
    return f"Contact Team Online operator now due to system error.\n {err}", {}


def reply(
    msgs: list[BaseMessage] | AnyMessage | str,
    instructions: list[str] = [],
    tool_call_id: str | None = None,
):
    if isinstance(msgs, str):
        if not tool_call_id:
            raise Exception("tool_call_id is empty.")

        msgs = ToolMessage(msgs, artifact={}, tool_call_id=tool_call_id)

    system_instract = [SystemMessage("\n".join(instructions))] if instructions else []

    return Command(update={"messages": system_instract + (msgs if isinstance(msgs, list) else [msgs])})
