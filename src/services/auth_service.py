from sqlalchemy.orm import Session
from src.models import User, RefreshSession
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from src.schemas.auth import UserRegister
from uuid import uuid4
from datetime import datetime, timedelta
from src.core.config import settings

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserRegister):
        # Проверка на существующего юзера
        if db.query(User).filter(User.email == user_data.email).first():
            raise ValueError("Email already registered")
        if db.query(User).filter(User.username == user_data.username).first():
            raise ValueError("Username already taken")
        
        # Создание пользователя
        user = User(
            id=uuid4(),
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def login_user(db: Session, email: str, password: str):
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return user
        
    @staticmethod
    def create_tokens(user_id):
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        return access_token, refresh_token

