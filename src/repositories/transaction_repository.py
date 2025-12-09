from typing import Optional
from sqlmodel import Session, select
from src.models import Transaction


class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, transaction: Transaction) -> Transaction:
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        return self.session.get(Transaction, transaction_id)

    def get_by_user(
        self, user_id: str, limit: Optional[int] = None
    ) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
        )

        if limit:
            statement = statement.limit(limit)

        return list[Transaction](self.session.exec(statement).all())

    def get_by_user_and_type(
        self, user_id: str, transaction_type: str, limit: Optional[int] = None
    ) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == transaction_type,
            )
            .order_by(Transaction.created_at.desc())
        )

        if limit:
            statement = statement.limit(limit)

        return list[Transaction](self.session.exec(statement).all())
