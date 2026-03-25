import contextvars
import logging
from uuid import UUID

import grpc
from sqlalchemy.exc import SQLAlchemyError

from src.core.security import verify_token
from src.db.database import SessionLocal
from src.models import User

logger = logging.getLogger(__name__)

current_user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_id",
    default=None,
)


class AuthInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, protected_methods: set[str]):
        self._protected_methods = protected_methods

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None or handler_call_details.method not in self._protected_methods:
            return handler

        if handler.stream_stream is None:
            return handler

        async def auth_stream_stream(request_iterator, context):
            user_id = await self._authenticate_user(context)
            token = current_user_id_ctx.set(user_id)
            try:
                async for response in handler.stream_stream(request_iterator, context):
                    yield response
            finally:
                current_user_id_ctx.reset(token)

        return grpc.stream_stream_rpc_method_handler(
            auth_stream_stream,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    async def _authenticate_user(self, context: grpc.aio.ServicerContext) -> str:
        metadata = {item.key.lower(): item.value for item in context.invocation_metadata()}
        authorization = metadata.get("authorization", "")

        if not authorization.startswith("Bearer "):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing Bearer token")

        token = authorization.removeprefix("Bearer ").strip()
        user_id = verify_token(token, expected_type="access")
        if not user_id:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")

        try:
            user_uuid = UUID(user_id)
        except ValueError:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token payload")

        db = SessionLocal()
        try:
            user_exists = db.query(User.id).filter(User.id == user_uuid).first() is not None
        except SQLAlchemyError as db_exc:
            logger.exception("Auth DB check failed: %s", db_exc)
            await context.abort(grpc.StatusCode.INTERNAL, "Authentication backend unavailable")
        finally:
            db.close()

        if not user_exists:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "User not found")

        return user_id