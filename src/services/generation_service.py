from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.models import CardGeneration, GeneratedCardResult, User
from src.schemas.card import CardContentWrite


class GenerationService:
    @staticmethod
    def save_generation_results(
        db: Session,
        user_id: UUID,
        generation_id: UUID,
        requested_count: int,
        cards: list[dict],
        is_stopped: bool,
    ) -> CardGeneration:
        generation = CardGeneration(
            id=generation_id,
            user_id=user_id,
            source_text=None,
            requested_count=requested_count,
            generated_count=len(cards),
            is_stopped=is_stopped,
            completed_at=datetime.utcnow(),
        )
        db.add(generation)
        db.flush()

        cards_data = [
            {
                "generation_id": generation.id,
                "position": i,
                "content": CardContentWrite.model_validate(card_data).model_dump(mode="json"),
            }
            for i, card_data in enumerate(cards)
        ]
        
        db.bulk_insert_mappings(GeneratedCardResult, cards_data)
        
        db.commit()
        db.refresh(generation)
        return generation

    @staticmethod
    def list_user_generations(db: Session, current_user: User, skip: int = 0, limit: int = 20) -> list[CardGeneration]:
        return (
            db.query(CardGeneration)
            .filter(CardGeneration.user_id == current_user.id)
            .order_by(CardGeneration.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_user_generation(db: Session, generation_id: UUID, current_user: User) -> CardGeneration:
        generation = (
            db.query(CardGeneration)
            .filter(
                CardGeneration.id == generation_id,
                CardGeneration.user_id == current_user.id,
            )
            .first()
        )
        if not generation:
            raise ValueError("Generation not found or access denied")
        return generation