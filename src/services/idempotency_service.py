import hashlib
import json
import time
import uuid
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException, status
from pydantic import TypeAdapter

from src.core.config import settings
from src.db.redis_client import get_redis


class IdempotencyService:
    RESPONSE_PREFIX = "idempotency:response"
    LOCK_PREFIX = "idempotency:lock"

    @classmethod
    def build_fingerprint(cls, namespace: str, user_id: Any, payload: Any) -> str:
        serialized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        raw_value = f"{namespace}:{user_id}:{serialized_payload}"
        return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

    @classmethod
    def execute(
        cls,
        namespace: str,
        idempotency_key: Optional[str],
        user_id: Any,
        payload: Any,
        operation: Callable[[], Any],
        response_schema: Any,
    ) -> Any:
        if not idempotency_key or idempotency_key=='':
            return operation()

        redis = get_redis()
        fingerprint = cls.build_fingerprint(namespace, user_id, payload)
        response_key = cls._response_key(namespace, idempotency_key)
        lock_key = cls._lock_key(namespace, idempotency_key)
        adapter = TypeAdapter(response_schema)

        cached_response = cls._get_cached_response(redis, response_key, fingerprint, adapter)
        if cached_response is not None:
            return cached_response

        lock_token = str(uuid.uuid4())
        lock_acquired = redis.set(
            lock_key,
            lock_token,
            nx=True,
            ex=settings.IDEMPOTENCY_LOCK_TTL_SECONDS,
        )

        if not lock_acquired:
            return cls._wait_for_cached_response(redis, response_key, fingerprint, adapter)

        try:
            cached_response = cls._get_cached_response(redis, response_key, fingerprint, adapter)
            if cached_response is not None:
                return cached_response

            result = adapter.validate_python(operation())
            cls._cache_response(redis, response_key, fingerprint, result, adapter)
            return result
        finally:
            cls._release_lock(redis, lock_key, lock_token)

    @classmethod
    async def execute_async(
        cls,
        namespace: str,
        idempotency_key: Optional[str],
        user_id: Any,
        payload: Any,
        operation: Callable[[], Awaitable[Any]],
        response_schema: Any,
    ) -> Any:
        if not idempotency_key:
            return await operation()

        redis = get_redis()
        fingerprint = cls.build_fingerprint(namespace, user_id, payload)
        response_key = cls._response_key(namespace, idempotency_key)
        lock_key = cls._lock_key(namespace, idempotency_key)
        adapter = TypeAdapter(response_schema)

        cached_response = cls._get_cached_response(redis, response_key, fingerprint, adapter)
        if cached_response is not None:
            return cached_response

        lock_token = str(uuid.uuid4())
        lock_acquired = redis.set(
            lock_key,
            lock_token,
            nx=True,
            ex=settings.IDEMPOTENCY_LOCK_TTL_SECONDS,
        )

        if not lock_acquired:
            return cls._wait_for_cached_response(redis, response_key, fingerprint, adapter)

        try:
            cached_response = cls._get_cached_response(redis, response_key, fingerprint, adapter)
            if cached_response is not None:
                return cached_response

            result = adapter.validate_python(await operation())
            cls._cache_response(redis, response_key, fingerprint, result, adapter)
            return result
        finally:
            cls._release_lock(redis, lock_key, lock_token)

    @classmethod
    def _cache_response(cls, redis, response_key: str, fingerprint: str, result: Any, adapter: TypeAdapter) -> None:
        serialized_result = adapter.dump_python(adapter.validate_python(result), mode="json")
        record = {
            "fingerprint": fingerprint,
            "response": serialized_result,
        }
        redis.set(response_key, json.dumps(record), ex=settings.IDEMPOTENCY_RESPONSE_TTL_SECONDS)

    @classmethod
    def _wait_for_cached_response(
        cls,
        redis,
        response_key: str,
        fingerprint: str,
        adapter: TypeAdapter,
    ) -> Any:
        deadline = time.monotonic() + settings.IDEMPOTENCY_WAIT_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            cached_response = cls._get_cached_response(redis, response_key, fingerprint, adapter)
            if cached_response is not None:
                return cached_response
            time.sleep(settings.IDEMPOTENCY_WAIT_INTERVAL_SECONDS)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with the same Idempotency-Key is already being processed",
        )

    @classmethod
    def _get_cached_response(
        cls,
        redis,
        response_key: str,
        fingerprint: str,
        adapter: TypeAdapter,
    ) -> Optional[Any]:
        raw_record = redis.get(response_key)
        if raw_record is None:
            return None

        record = json.loads(raw_record)
        if record["fingerprint"] != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key reuse with different request payload is not allowed",
            )

        return adapter.validate_python(record["response"])

    @classmethod
    def _response_key(cls, namespace: str, idempotency_key: str) -> str:
        return f"{cls.RESPONSE_PREFIX}:{namespace}:{idempotency_key}"

    @classmethod
    def _lock_key(cls, namespace: str, idempotency_key: str) -> str:
        return f"{cls.LOCK_PREFIX}:{namespace}:{idempotency_key}"

    @staticmethod
    def _release_lock(redis, lock_key: str, lock_token: str) -> None:
        release_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
        """
        redis.eval(release_script, 1, lock_key, lock_token)