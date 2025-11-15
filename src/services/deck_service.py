from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4, UUID
from src.models import Deck, User
from src.schemas.deck import DeckCreate, DeckUpdate, DeckResponse

class DeckService:
    @staticmethod
    def create_deck(db: Session, deck_data: DeckCreate, current_user: User) -> Deck:
        deck = Deck(
            id=uuid4(),
            user_id=current_user.id,
            title=deck_data.title,
            description=deck_data.description,
            status="private"
        )
        db.add(deck)
        db.commit()
        db.refresh(deck)
        return deck
    
    @staticmethod
    def get_user_decks(db: Session, current_user: User, skip: int = 0, limit: int = 100) -> list[Deck]:
        decks = db.query(Deck).filter(
            Deck.user_id == current_user.id
        ).order_by(Deck.created_at.desc()).offset(skip).limit(limit).all()
        return decks
    
    @staticmethod
    def get_deck(db: Session, deck_id: UUID, current_user: User) -> Deck:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id  # Только свои колоды!
        ).first()
        if not deck:
            raise ValueError("Deck not found")
        return deck
    
    @staticmethod
    def update_deck(db: Session, deck_id: UUID, deck_data: DeckUpdate, current_user: User) -> Deck:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found")
        
        update_data = deck_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(deck, field, value)
        
        db.commit()
        db.refresh(deck)
        return deck
    
    @staticmethod
    def delete_deck(db: Session, deck_id: UUID, current_user: User):
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id
        ).first()
        if not deck:
            raise ValueError("Deck not found")
        
        db.delete(deck)
        db.commit()
    
    @staticmethod
    def get_deck_count(deck: Deck, db: Session) -> int:
        """Подсчёт карточек в колоде"""
        return db.query(func.count(Deck.flashcards)).filter(Deck.id == deck.id).scalar()
