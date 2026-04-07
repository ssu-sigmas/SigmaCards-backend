import asyncio
import json
import logging
from typing import Dict

from aiokafka import AIOKafkaConsumer

from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaRouter:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None

        self._queues: Dict[str, asyncio.Queue] = {}

        self._running = False

    async def start(self):
        if self._running:
            return

        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_ML_RESPONSE_TOPIC,
            settings.KAFKA_OCR_RESPONSE_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_ML_CONSUMER_GROUP,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )

        await self.consumer.start()

        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

        logger.info("KafkaRouter started")

    async def stop(self):
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            await self.consumer.stop()

        logger.info("KafkaRouter stopped")

    def subscribe(self, generation_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._queues[generation_id] = queue
        return queue

    def unsubscribe(self, generation_id: str):
        self._queues.pop(generation_id, None)

    async def _consume_loop(self):
        try:
            async for message in self.consumer:
                payload = message.value

                generation_id = payload.get("generation_id")
                if not generation_id:
                    continue

                queue = self._queues.get(generation_id)
                if queue:
                    await queue.put(payload)

        except asyncio.CancelledError:
            logger.info("KafkaRouter stopped consuming")
            raise
        except Exception:
            logger.exception("KafkaRouter crashed")

kafka_router = KafkaRouter()