from decimal import Decimal
from typing import Optional
from sqlmodel import Session, select
from src.models import Wallet
from src.models.currency import Currency


class WalletRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_user_and_currency(
        self, user_id: str, currency: Currency
    ) -> Optional[Wallet]:
        statement = select(Wallet).where(
            Wallet.user_id == user_id, Wallet.currency == currency
        )
        return self.session.exec(statement).first()

    def get_all_by_user(self, user_id: str) -> list[Wallet]:
        statement = select(Wallet).where(Wallet.user_id == user_id)
        return list(self.session.exec(statement).all())

    def create(
        self, user_id: str, currency: Currency, balance: Decimal = Decimal("0.00")
    ) -> Wallet:
        wallet = Wallet(user_id=user_id, currency=currency, balance=balance)
        self.session.add(wallet)
        self.session.commit()
        self.session.refresh(wallet)
        return wallet

    def update(self, wallet: Wallet) -> Wallet:
        self.session.add(wallet)
        self.session.commit()
        self.session.refresh(wallet)
        return wallet

    def get_or_create(self, user_id: str, currency: Currency) -> Wallet:
        wallet = self.get_by_user_and_currency(user_id, currency)
        if not wallet:
            wallet = self.create(user_id, currency)
        return wallet
