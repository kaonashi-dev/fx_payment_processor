from fastapi import HTTPException, status, Path
from sqlmodel import Session
from src.database.engine import engine
from src.repositories import UserRepository


def validate_user_exists(user_id: str = Path(..., description="User ID")) -> str:
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user_id format: {user_id}. Must be a valid integer.",
        )

    with Session(engine) as session:
        user_repo = UserRepository(session)
        if not user_repo.exists(user_id_int):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

    return user_id
