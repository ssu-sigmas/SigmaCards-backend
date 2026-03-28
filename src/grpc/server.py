import asyncio
import logging
from typing import AsyncIterator
import uuid
from src.services.kafka_router import kafka_router

import grpc

import src.grpc.card_generation_pb2 as card_generation_pb2
import src.grpc.card_generation_pb2_grpc as card_generation_pb2_grpc
from src.grpc.auth_interceptor import AuthInterceptor, current_user_id_ctx
from src.services.ml_service import ml_service
from src.db.redis_client import get_redis

logger = logging.getLogger(__name__)


class CardGenerationService(card_generation_pb2_grpc.CardGenerationServiceServicer):
    async def GenerateCards(self, request_iterator, context):
        current_user_id = current_user_id_ctx.get()
        if not current_user_id:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing authenticated context")

        stop_event = asyncio.Event()

        try:
            first_request = await anext(request_iterator)
        except StopAsyncIteration:
            yield self._error("empty stream")
            return

        if first_request.WhichOneof("payload") != "generate":
            yield self._error("first message must contain generate payload")
            return

        yield self._status("начинаем обработку")

        text = first_request.generate.text
        count = max(1, first_request.generate.count)

        self.generation_id = str(uuid.uuid4())
        logger.info("generation_id=%s", self.generation_id)

        queue = kafka_router.subscribe(self.generation_id)

        try:
            real_tasks = await ml_service.send_generation_requests(
                generation_id=self.generation_id,
                text=text,
                count=count,
            )

            logger.info("sent %s tasks to kafka", real_tasks)

            asyncio.create_task(self._listen_stop(request_iterator, stop_event))

            yield self._status("анализируем текст")

            received_tasks = 0

            while received_tasks < real_tasks:
                if stop_event.is_set():
                    logger.info("stopped by user")
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    logger.error("timeout waiting kafka")
                    break

                cards = payload.get("cards", [])

                for card_data in cards:
                    if stop_event.is_set():
                        break

                    yield card_generation_pb2.GenerateCardsStreamResponse(
                        card=self._build_card(card_data)
                    )

                received_tasks += 1

        except Exception:
            logger.exception("gRPC stream crashed")
            yield self._error("generation failed")

        finally:
            kafka_router.unsubscribe(self.generation_id)

        yield card_generation_pb2.GenerateCardsStreamResponse(
            completed=card_generation_pb2.CompletedMessage(
                stopped_by_user=stop_event.is_set()
            )
        )

    async def _listen_stop(self, request_iterator, stop_event):
        try:
            async for incoming in request_iterator:
                if incoming.WhichOneof("payload") == "stop":
                    stop_event.set()
                    get_redis().set(f"generation:skip:{self.generation_id}",1)
                    return
        except Exception:
            stop_event.set()

    def _status(self, message: str):
        return card_generation_pb2.GenerateCardsStreamResponse(
            status=card_generation_pb2.StatusMessage(message=message)
        )

    def _error(self, message: str):
        return card_generation_pb2.GenerateCardsStreamResponse(
            error=card_generation_pb2.ErrorMessage(message=message)
        )

    def _build_card(self, card_data: dict):
        def _map_block(block: dict):
            logger.info(f"type: {block.get('type', '')}")
            return card_generation_pb2.TextBlock(
                type=block.get("type", ""),
                id=block.get("id", ""),
                content=block.get("content", ""),
            )
        return card_generation_pb2.GeneratedCard(
            content=card_generation_pb2.CardContent(
                front=[_map_block(b) for b in card_data.get("front", [])],
                back=[_map_block(b) for b in card_data.get("back", [])],
            )
        )


class CardGenerationGrpcServer:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._server = grpc.aio.server(
            interceptors=[
                AuthInterceptor(
                    protected_methods={"/sigmacards.cards.v1.CardGenerationService/GenerateCards"}
                )
            ]
        )
        card_generation_pb2_grpc.add_CardGenerationServiceServicer_to_server(
            CardGenerationService(),
            self._server,
        )

    async def start(self):
        address = f"{self._host}:{self._port}"
        logger.info("gRPC card generation server adding port")
        self._server.add_insecure_port(address)
        logger.info("gRPC card generation server start starting at %s", address)
        await self._server.start()
        logger.info("gRPC card generation server started at %s", address)

    async def stop(self):
        await self._server.stop(grace=5)
        logger.info("gRPC card generation server stopped")