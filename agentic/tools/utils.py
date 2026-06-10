import hashlib
import logging
import os
import re
import threading
import time

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
MAX_PRODUCT_SEARCH_SIZE = 50
PRODUCT_SEARCH_FIELDS = [
    "display_name_th",
    "display_name_en",
    "short_description.text",
    "brand",
    "color",
    "barcode",
    "mat_no",
    "sap_id",
    "scghome_id",
    "basic_data",
    "b2c_selling_point",
    "material",
    "installation_tips",
    "usage_tips",
    "care_warning_instruction",
    "standard_list",
    "warranty_description",
    "height_unit",
    "height_number",
    "length_unit",
    "length_number",
    "weight_unit",
    "weight_number",
    "width_unit",
    "width_number",
    "custom_short_description",
    "custom_basic_data",
    "custom_b2c_selling_point",
    "custom_care_warning_instruction",
    "custom_warranty_description",
    "custom_usage_tips",
    "custom_installation_tips",
    "content",
]
KNOWLEDGE_SEARCH_FIELDS = ["id","title","content","tag","keyword"]

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

    def _get_max_size(self, limit: int) -> int:
        return limit if limit < MAX_PRODUCT_SEARCH_SIZE else MAX_PRODUCT_SEARCH_SIZE

    def _build_product_search_body(self, product_name: str, limit: int) -> dict:
        return {
            "_source": PRODUCT_SEARCH_FIELDS,
            "sort": [{"_score": {"order": "desc"}}],
            "size": self._get_max_size(limit),
            "min_score": 50,
            "query": {
                "bool": {
                    "filter": {"bool": {"must": [{"match": {"@deleted": "false"}}]}},
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {"prefix": {"display_name_th.keyword": {"value": product_name, "boost": 60}}},
                                    {"wildcard": {"display_name_th.keyword": {"value": f"*{product_name}*", "boost": 50}}},
                                    {"match": {"display_name_th.n4gram": {"query": product_name, "boost": 5}}},
                                    {"match": {"display_name_th.n5gram": {"query": product_name, "boost": 5}}},
                                    {
                                        "match": {
                                            "display_name_th.shingle": {
                                                "query": product_name,
                                                "fuzziness": "auto",
                                                "boost": 1,
                                            }
                                        }
                                    },
                                    {
                                        "multi_match": {
                                            "query": product_name,
                                            "fields": ["display_name_th^2", "display_name_en^2", "keyword"],
                                            "operator": "and",
                                            "fuzziness": "AUTO",
                                            "boost": 50,
                                        }
                                    },
                                    {
                                        "multi_match": {
                                            "query": product_name,
                                            "type": "bool_prefix",
                                            "fields": [
                                                "barcode^3",
                                                "brand",
                                                "display_name_th^2",
                                                "display_name_en^2",
                                                "keyword",
                                            ],
                                            "operator": "and",
                                            "boost": 100,
                                        }
                                    },
                                ]
                            }
                        }
                    ],
                    "should": [{"semantic": {"field": "concat_display_name", "query": product_name, "boost": 40}}],
                }
            },
        }

    def _build_knowledge_search_body(self, query: str, limit: int) -> dict:
        return {
            "_source": KNOWLEDGE_SEARCH_FIELDS,
            "sort": [{"_score": {"order": "desc"}}],
            "size": self._get_max_size(limit),
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "keyword^5",
                        "title^4",
                        "content"
                    ],
                    "operator": "or",
                }
            },
        }

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

    def get_product_by_name(self, name: str, limit: int) -> httpx.Response:
        endpoint = f"{self.base_url.rstrip('/')}/api/km/v1/query/home-product"
        body = self._build_product_search_body(name, limit)
        res = self._post(endpoint, body)
        return res

    def get_knowledge_by_name(self, name: str, limit: int) -> httpx.Response:
        endpoint = f"{self.base_url.rstrip('/')}/api/km/v1/query/af-basic-knowledge"
        body = self._build_knowledge_search_body(name, limit)
        logging.getLogger("content_service").info(
            "Content service knowledge query index=%s query=%s",
            "af-basic-knowledge",
            name,
        )
        return self._post(endpoint, body)


def normalize_product_name(name: str) -> str:
    """
    Normalize a product name to avoid mismatches caused by extra spaces,
    different kinds of whitespace, or case differences.
    """
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_markdown(text: str) -> str:
    """
    Replaces multiple consecutive newlines and carriage returns with a single newline.
    """
    return re.sub(r"(\r\n|\n)+", "\n", text)


def _product_hit_to_dict(hit: dict) -> dict:
    source = hit.get("_source", {})
    product = dict(source)
    short_description = product.get("short_description")
    if isinstance(short_description, dict):
        product["short_description"] = short_description.get("text")

    metadata = dict(product.get("metadata") or {})
    metadata.update(
        {
            "score": hit.get("_score"),
            "barcode": product.get("barcode"),
            "mat_no": product.get("mat_no"),
            "sap_id": product.get("sap_id"),
        }
    )
    product["metadata"] = metadata
    return product


def _text_value(value) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or "")
    return str(value or "")


def _knowledge_hit_to_dict(hit: dict) -> dict:
    source = hit.get("_source", {})
    return {
        "id": source.get("id"),
        "title": _text_value(source.get("title")),
        "content": _text_value(source.get("content")),
        "published": source.get("published"),
        "keywords": source.get("keywords"),
        "metadata": {"score": hit.get("_score")},
    }


def parse_product_response(data: dict) -> tuple[list[dict], str | None]:
    if data.get("success") is True:
        return data.get("data") or [], None

    hits = data.get("hits")
    if isinstance(hits, dict):
        raw_hits = hits.get("hits") or []
        return [_product_hit_to_dict(hit) for hit in raw_hits], None

    return [], f"API unsuccessful: {data}"


def parse_knowledge_response(data: dict) -> tuple[list[dict], str | None]:
    if data.get("success") is True:
        return data.get("data") or [], None

    hits = data.get("hits")
    if isinstance(hits, dict):
        raw_hits = hits.get("hits") or []
        return [_knowledge_hit_to_dict(hit) for hit in raw_hits], None

    return [], f"API unsuccessful: {data}"


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
