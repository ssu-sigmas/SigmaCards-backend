import json
import logging
import uuid
import random
from itertools import cycle, islice
from typing import List, Optional

from aiokafka import AIOKafkaProducer

from src.core.config import settings
from src.services.storage_service import StorageService
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)
#TODO: более гибкая система раздачи

CARD_TYPES = ["key_terms", "facts", "fill_blank", "test_questions", "concepts"]

class MLService:
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.request_topic = settings.KAFKA_ML_REQUEST_TOPIC

        self.producer: Optional[AIOKafkaProducer] = None
        self._is_running = False
        self.sentences_amount = 5
        self.batch_size_max = 7

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

        sentences = self._split_into_sentences(text)

        chunks = self._build_chunks(
            sentences,
            chunk_size=self.sentences_amount,
            overlap=1,
        )

        if not chunks:
            return 0

        cards_per_chunk = self._allocate_cards_per_chunk(
            num_chunks=len(chunks),
            total_cards=count,
            max_per_chunk=self.batch_size_max,
        )

        sent = 0

        for chunk_id, (chunk, card_count) in enumerate(zip(chunks, cards_per_chunk)):
            if card_count <= 0:
                continue

            chunk_text = " ".join(chunk)
            key = StorageService.build_chunk_key(generation_id, chunk_id)
            StorageService.upload_chunk_object(
                object_name=key,
                text=chunk_text
            )
            s3_url = StorageService.get_chunk_object_url(key)
            s3_url = s3_url.replace('localhost', 'rustfs') # TODO: normal change

            card_type = random.choice(CARD_TYPES)

            payload = {
                "generation_id": generation_id,
                "correlation_id": str(uuid.uuid4()),
                "text_url": s3_url,
                "generation_mode": card_type,
                "cards_count": card_count
            }

            await self.producer.send_and_wait(
                topic=self.request_topic,
                key=generation_id,
                value=payload,
            )

            sent += 1

            logger.debug(
                "Sent chunk ML requests: gen_id=%s chunk=%s cards=%s",
                generation_id,
                chunk_id,
                card_count,
            )

        return sent

    def _build_chunks(self, sentences: list[str], chunk_size: int, overlap: int = 1):
        chunks = []
        i = 0

        while i < len(sentences):
            chunk = sentences[i : i + chunk_size]
            if not chunk:
                break

            chunks.append(chunk)
            i += max(1, chunk_size - overlap)

        return chunks

    def _allocate_cards_per_chunk(self, num_chunks: int, total_cards: int, max_per_chunk: int):
        base = total_cards // num_chunks
        rem = total_cards % num_chunks

        result = []

        for i in range(num_chunks):
            cards = base + (1 if i < rem else 0)
            cards = min(cards, max_per_chunk)
            result.append(cards)

        return result

    def _split_into_sentences(self, text: str) -> list[str]:
        return sent_tokenize(text)

ml_service = MLService()