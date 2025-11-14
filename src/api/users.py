from fastapi import APIRouter, Depends
from src.schemas.auth import UserResponse
from src.core.dependencies import get_current_user
from src.models import User

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Получить информацию о текущем пользователе
    """
    return current_user
