from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()

# ==========================================
# USERS & AUTHENTICATION
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    fsrs_settings = Column(JSONB, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    refresh_sessions = relationship("RefreshSession", back_populates="user", cascade="all, delete-orphan")
    decks = relationship("Deck", back_populates="user", foreign_keys="Deck.user_id", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="user", cascade="all, delete-orphan")
    deck_subscriptions = relationship("DeckSubscription", back_populates="user", cascade="all, delete-orphan")
    user_cards = relationship("UserCard", back_populates="user", cascade="all, delete-orphan")
    review_logs = relationship("ReviewLog", back_populates="user", cascade="all, delete-orphan")
    card_actions = relationship("CardAction", back_populates="user", cascade="all, delete-orphan")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(255), nullable=False, unique=True, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 может быть до 45 символов
    is_revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_sessions")


# ==========================================
# CONTENT MANAGEMENT
# ==========================================

class Deck(Base):
    __tablename__ = "decks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="private")  # private | public | shared
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="decks", foreign_keys=[user_id])
    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")
    subscriptions = relationship("DeckSubscription", back_populates="deck", cascade="all, delete-orphan")


class DeckSubscription(Base):
    __tablename__ = "deck_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        Index("ix_deck_subscriptions_user_deck", "user_id", "deck_id", unique=True),
    )

    user = relationship("User", back_populates="deck_subscriptions")
    deck = relationship("Deck", back_populates="subscriptions")


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # image | text | pdf
    content_text = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="sources")
    flashcards = relationship("Flashcard", back_populates="source")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    card_type = Column(String(50), nullable=False, default="key_terms")  # key_terms, facts, fill_blank, test_questions, concepts
    content = Column(JSONB, nullable=False)
    search_vector = Column(TSVECTOR, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    is_suspended = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    deck = relationship("Deck", back_populates="flashcards")
    source = relationship("Source", back_populates="flashcards")
    user_cards = relationship("UserCard", back_populates="card", cascade="all, delete-orphan")


# ==========================================
# SPACED REPETITION (FSRS)
# ==========================================

class UserCard(Base):
    __tablename__ = "user_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id = Column(UUID(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False, index=True)

    # SRS параметры
    due = Column(DateTime, nullable=False, index=True)  # ГЛАВНОЕ ПОЛЕ ДЛЯ ВЫБОРКИ
    state = Column(Integer, nullable=False, default=0)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    stability = Column(Float, nullable=False, default=0)
    difficulty = Column(Float, nullable=False, default=0)

    # История
    elapsed_days = Column(Integer, nullable=False, default=0)
    scheduled_days = Column(Integer, nullable=False, default=0)
    reps = Column(Integer, nullable=False, default=0)
    lapses = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)

    last_review = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="user_cards")
    card = relationship("Flashcard", back_populates="user_cards")
    review_logs = relationship("ReviewLog", back_populates="user_card", cascade="all, delete-orphan")
    card_actions = relationship("CardAction", back_populates="user_card", cascade="all, delete-orphan")


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_card_id = Column(UUID(as_uuid=True), ForeignKey("user_cards.id", ondelete="SET NULL"), nullable=True, index=True)

    # Rating
    rating = Column(Integer, nullable=False)  # 1=Again, 2=Hard, 3=Good, 4=Easy
    state_before = Column(Integer, nullable=False)

    # Predicted values after
    due_after = Column(DateTime, nullable=False)
    stability_after = Column(Float, nullable=False)
    difficulty_after = Column(Float, nullable=False)

    # Metadata
    duration_ms = Column(Integer, nullable=True)
    review_datetime = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="review_logs")
    user_card = relationship("UserCard", back_populates="review_logs")


class CardAction(Base):
    __tablename__ = "card_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_card_id = Column(UUID(as_uuid=True), ForeignKey("user_cards.id", ondelete="CASCADE"), nullable=False, index=True)

    action = Column(String(50), nullable=False)  # flag | mark_easy | suspend | custom_due
    action_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="card_actions")
    user_card = relationship("UserCard", back_populates="card_actions")
