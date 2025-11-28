import httpx
import asyncio
from typing import List
from src.core.config import settings
from src.schemas.card import CardType, MLGeneratedCard
import logging
import random

logger = logging.getLogger(__name__)

class MLService:
    def __init__(self):
        self.base_url = settings.ML_SERVICE_URL
        self.timeout = settings.ML_SERVICE_TIMEOUT
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def generate_cards(self, text: str, count: int = 5) -> List[MLGeneratedCard]:
        card_types = list(CardType)
        selected_types = random.sample(card_types * 2, min(count, len(card_types)))
        
        tasks = []
        for card_type in selected_types:
            tasks.append(
                self._generate_single_card(text, card_type)
            )
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        cards = []
        
        for resp, card_type in zip(responses, selected_types):
            if isinstance(resp, Exception):
                logger.error(f"ML {card_type.value}: {type(resp).__name__}")
                cards.append(self._fallback_card(card_type, text))
                continue
            
            if not isinstance(resp, httpx.Response):
                cards.append(self._fallback_card(card_type, text))
                continue
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    ml_cards = data.get("cards", [])
                    
                    ml_card = ml_cards[0] if ml_cards else {}
                    
                    cards.append(MLGeneratedCard(
                        content={
                            "front": ml_card.get("question", "No question"),
                            "back": ml_card.get("answer", "No answer")
                        },
                        card_type=card_type
                    ))
                    logger.info(f"Generated {card_type.value}")
                except Exception as e:
                    logger.error(f"ML {card_type.value} parse: {e}")
                    cards.append(self._fallback_card(card_type, text))
            else:
                logger.error(f"ML {card_type.value}: HTTP {resp.status_code}")
                cards.append(self._fallback_card(card_type, text))
        
        return cards[:count]
    
    async def _generate_single_card(self, text: str, card_type: CardType):
        payload = {
            "text": text,
            "generation_mode": card_type.value,
            "cards_count": 1
        }
        logger.debug(f"Sending to ML {card_type.value}: {payload}")
        return await self.client.post("/api/v1/cards/generate", json=payload)
    
    def _fallback_card(self, card_type: CardType, text: str):
        return MLGeneratedCard(
            content={
                "front": f"[{card_type.value.upper()}]",
                "back": f"Text: {text[:100]}"
            },
            card_type=card_type
        )
    
    async def close(self):
        await self.client.aclose()

ml_service = MLService()
