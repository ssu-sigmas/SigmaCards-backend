# src/services/card_service.py
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from src.models import Flashcard, User, Deck, UserCard, Source
from src.services.fsrs_service import FsrsService
from src.services.image_service import ImageService
from src.schemas.card import FlashcardCreate, FlashcardUpdate, CardContentWrite, CardContentRead

class CardService:
    @staticmethod
    def create_card(db: Session, card_data: FlashcardCreate, deck_id: UUID, current_user: User) -> Flashcard:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found or access denied")
        
        if card_data.source_id is not None:
            source = db.query(Source).filter(
                Source.id == card_data.source_id,
                Source.user_id == current_user.id
            ).first()
            if not source:
                raise ValueError("Source not found or access denied")

        card = Flashcard(
            id=uuid4(),
            deck_id=deck_id,
            source_id=card_data.source_id,
            content=card_data.content.model_dump(mode='json'),
            position=card_data.position
        )
        db.add(card)
        db.flush()
        
        initial_card = FsrsService.create_initial_card()
        user_card = UserCard(
            id=uuid4(),
            user_id=current_user.id,
            card_id=card.id,
            due=initial_card.due.replace(tzinfo=None),
            state=int(initial_card.state),
            step=initial_card.step,
            stability=0.0,
            difficulty=0.0,
            elapsed_days=0,
            scheduled_days=0,
            reps=0,
            lapses=0
        )
        db.add(user_card)

        content_model = CardContentWrite.model_validate(card.content)
        image_ids = ImageService.extract_ids_from_content(content_model)

        ImageService.sync_card_images(db, card, image_ids)

        db.commit()
        db.refresh(card)

        card.content = ImageService.enrich_content_with_urls(db, content_model)
        
        return card
    
    @staticmethod
    def get_deck_cards(db: Session, deck_id: UUID, current_user: User, skip: int = 0, limit: int = 100) -> list:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found or access denied")
        
        cards = db.query(Flashcard).filter(
            Flashcard.deck_id == deck_id
        ).order_by(Flashcard.position).offset(skip).limit(limit).all()
        for card in cards:
            card.content = ImageService.enrich_content_with_urls(db, 
                                                                 CardContentWrite.model_validate(card.content))
        return cards
    
    @staticmethod
    def get_card(db: Session, card_id: UUID, current_user: User) -> Flashcard:
        card = db.query(Flashcard).join(Deck).filter(
            Flashcard.id == card_id,
            Deck.user_id == current_user.id
        ).first()
        if not card:
            raise ValueError("Card not found or access denied")
        
        card.content = ImageService.enrich_content_with_urls(db, CardContentWrite.model_validate(card.content))
        return card
    
    @staticmethod
    def update_card(db: Session, card_id: UUID, card_data: FlashcardUpdate, current_user: User) -> Flashcard:
        card = db.query(Flashcard).join(Deck).filter(
            Flashcard.id == card_id,
            Deck.user_id == current_user.id
        ).first()

        if not card:
            raise ValueError("Card not found or access denied")

        if card.version != card_data.version:
            raise ValueError("Version conflict: card has been modified")

        update_data = card_data.model_dump(mode='json', exclude_unset=True, exclude={"version"})

        if "content" in update_data and update_data["content"] is not None:
            content_model = CardContentWrite.model_validate(update_data["content"])

            image_ids = ImageService.extract_ids_from_content(content_model)
            ImageService.sync_card_images(db, card, image_ids)

            card.content = content_model.model_dump(mode="json")

        for field, value in update_data.items():
            if field != "content":
                setattr(card, field, value)

        card.version += 1
        db.commit()
        db.refresh(card)

        card.content = ImageService.enrich_content_with_urls(db, CardContentWrite.model_validate(card.content))
        return card
            
    @staticmethod
    def delete_card(db: Session, card_id: UUID, current_user: User):
        card = db.query(Flashcard).join(Deck).filter(
            Flashcard.id == card_id,
            Deck.user_id == current_user.id
        ).first()
        if not card:
            raise ValueError("Card not found or access denied")
        
        db.delete(card)
        db.commit()
