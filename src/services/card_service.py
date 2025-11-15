from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from src.models import Flashcard, User, Deck
from src.schemas.card import FlashcardCreate, FlashcardUpdate, FlashcardResponse
from typing import List

class CardService:
    @staticmethod
    def create_card(db: Session, card_data: FlashcardCreate, deck_id: UUID, current_user: User) -> Flashcard:
        # Проверяем, что колода принадлежит пользователю
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found or access denied")
        
        card = Flashcard(
            id=uuid4(),
            deck_id=deck_id,
            source_id=card_data.source_id,  # Пока None
            card_type="basic",  # Пока базовые
            content=card_data.content,
            position=card_data.position
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card
    
    @staticmethod
    def get_deck_cards(db: Session, deck_id: UUID, current_user: User, skip: int = 0, limit: int = 100) -> List[Flashcard]:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found or access denied")
        
        cards = db.query(Flashcard).filter(
            Flashcard.deck_id == deck_id
        ).order_by(Flashcard.position).offset(skip).limit(limit).all()
        return cards
    
    @staticmethod
    def get_card(db: Session, card_id: UUID, current_user: User) -> Flashcard:
        card = db.query(Flashcard).join(Deck).filter(
            Flashcard.id == card_id,
            Deck.user_id == current_user.id
        ).first()
        if not card:
            raise ValueError("Card not found or access denied")
        return card
    
    @staticmethod
    def update_card(db: Session, card_id: UUID, card_data: FlashcardUpdate, current_user: User) -> Flashcard:
        card = db.query(Flashcard).join(Deck).filter(
            Flashcard.id == card_id,
            Deck.user_id == current_user.id
        ).first()
        if not card:
            raise ValueError("Card not found or access denied")
        
        update_data = card_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)
        
        db.commit()
        db.refresh(card)
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
