import json
import logging
import uuid
from itertools import cycle, islice
from typing import List, Optional

from aiokafka import AIOKafkaProducer

from src.core.config import settings

logger = logging.getLogger(__name__)

CARD_TYPES = ["key_terms", "facts", "fill_blank", "test_questions", "concepts"]


class MLService:
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.request_topic = settings.KAFKA_ML_REQUEST_TOPIC

        self.producer: Optional[AIOKafkaProducer] = None
        self._is_running = False

    async def startup(self):
        if self._is_running:
            return

        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda v: v.encode("utf-8"),
            acks="all",
        )

        await self.producer.start()
        self._is_running = True
        logger.info("MLService producer started")

    async def close(self):
        if self.producer:
            await self.producer.stop()
        self._is_running = False
        logger.info("MLService producer stopped")

    async def send_generation_requests(
        self,
        generation_id: str,
        text: str,
        count: int,
    ) -> int:
        if not self._is_running:
            await self.startup()

        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized")

        selected_types = list(islice(cycle(CARD_TYPES), count))

        for card_type in selected_types:
            payload = {
                "generation_id": generation_id,
                "correlation_id": str(uuid.uuid4()),
                "text": text,
                "generation_mode": card_type,
                "cards_count": 1,
            }

            await self.producer.send_and_wait(
                topic=self.request_topic,
                key=generation_id, 
                value=payload,
            )

            logger.debug(
                "Sent ML request: gen_id=%s type=%s",
                generation_id,
                card_type,
            )

        return len(selected_types)
    
ml_service = MLService()