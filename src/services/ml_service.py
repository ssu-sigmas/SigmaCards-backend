import asyncio
import json
import logging
import random
import uuid
from typing import Dict, List, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.core.config import settings
from src.schemas.card import CardType, MLGeneratedCard

logger = logging.getLogger(__name__)


class MLService:
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.request_topic = settings.KAFKA_ML_REQUEST_TOPIC
        self.response_topic = settings.KAFKA_ML_RESPONSE_TOPIC
        self.group_id = settings.KAFKA_ML_CONSUMER_GROUP
        self.request_timeout_ms = settings.ML_SERVICE_TIMEOUT * 1000

        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._is_running = False

    async def startup(self):
        if self._is_running:
            return

        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda v: v.encode("utf-8"),
            acks="all",
            request_timeout_ms=self.request_timeout_ms,
        )

        self.consumer = AIOKafkaConsumer(
            self.response_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            key_deserializer=lambda v: v.decode("utf-8") if v else None,
        )

        await self.producer.start()
        await self.consumer.start()
        self._is_running = True
        self._consumer_task = asyncio.create_task(self._consume_responses())
        logger.info("MLService Kafka client started")

    async def close(self):
        self._is_running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        logger.info("MLService Kafka client stopped")

    async def generate_cards(self, text: str, count: int = 5) -> List[MLGeneratedCard]:
        if not self._is_running:
            await self.startup()

        card_types = list(CardType)
        selected_types = random.sample(card_types * 2, min(count, len(card_types)))

        tasks = [self._generate_single_card(text, card_type) for card_type in selected_types]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        cards: List[MLGeneratedCard] = []

        for resp, card_type in zip(responses, selected_types):
            if isinstance(resp, Exception):
                logger.error("ML %s: %s", card_type.value, type(resp).__name__)
                cards.append(self._fallback_card(card_type, text))
                continue

            if resp and isinstance(resp, dict):
                try:
                    ml_cards = resp.get("cards", [])
                    ml_card = ml_cards[0] if ml_cards else {}
                    cards.append(
                        MLGeneratedCard(
                            content={
                                "front": ml_card.get("question", "No question"),
                                "back": ml_card.get("answer", "No answer"),
                            },
                            card_type=card_type,
                        )
                    )
                    logger.info("Generated %s", card_type.value)
                except Exception as e:
                    logger.error("ML %s parse: %s", card_type.value, e)
                    cards.append(self._fallback_card(card_type, text))
            else:
                cards.append(self._fallback_card(card_type, text))

        return cards[:count]

    async def _generate_single_card(self, text: str, card_type: CardType):
        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized")

        correlation_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[correlation_id] = future

        payload = {
            "correlation_id": correlation_id,
            "reply_topic": self.response_topic,
            "text": text,
            "generation_mode": card_type.value,
            "cards_count": 1,
        }

        try:
            await self.producer.send_and_wait(
                topic=self.request_topic,
                key=card_type.value,
                value=payload,
            )
            return await asyncio.wait_for(future, timeout=settings.ML_SERVICE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error("ML %s timeout via Kafka", card_type.value)
            return None
        finally:
            self._pending_requests.pop(correlation_id, None)

    async def _consume_responses(self):
        if not self.consumer:
            return

        try:
            async for message in self.consumer:
                payload = message.value if isinstance(message.value, dict) else {}
                correlation_id = payload.get("correlation_id")
                if not correlation_id:
                    continue

                future = self._pending_requests.get(correlation_id)
                if future and not future.done():
                    future.set_result(payload)
        except asyncio.CancelledError:
            logger.debug("Kafka response consumer cancelled")
            raise
        except Exception as exc:
            logger.exception("Kafka response consumer failed: %s", exc)

    def _fallback_card(self, card_type: CardType, text: str):
        return MLGeneratedCard(
            content={
                "front": f"[{card_type.value.upper()}]",
                "back": f"Text: {text[:100]}",
            },
            card_type=card_type,
        )


ml_service = MLService()