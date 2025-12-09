from typing import Optional
from sqlmodel import Session, select
from src.models import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def exists(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        return user is not None
