from decimal import Decimal
from typing import Optional
from sqlmodel import Session
from src.models import Transaction, TransactionType
from src.models.currency import Currency
from src.repositories import WalletRepository, TransactionRepository
from src.services.fx_rates import fx_rate_service
from src.database.engine import engine
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class WalletService:
    
    @staticmethod
    def fund_wallet(user_id: str, currency: Currency, amount: Decimal) -> dict:
        logger.info(
            "wallet_fund_requested",
            user_id=user_id,
            currency=currency.value,
            amount=str(amount)
        )

        with Session(engine) as session:
            wallet_repo = WalletRepository(session)
            transaction_repo = TransactionRepository(session)

            wallet = wallet_repo.get_or_create(user_id, currency)
            previous_balance = wallet.balance
            wallet.balance += amount
            wallet = wallet_repo.update(wallet)

            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=currency,
                amount=amount,
            )
            transaction = transaction_repo.create(transaction)

            logger.info(
                "wallet_funded",
                user_id=user_id,
                currency=currency.value,
                amount=str(amount),
                previous_balance=str(previous_balance),
                new_balance=str(wallet.balance),
                transaction_id=transaction.id
            )

            return {
                "user_id": user_id,
                "currency": currency,
                "amount": amount,
                "new_balance": wallet.balance,
            }
    
    @staticmethod
    def convert_currency(
        user_id: str,
        from_currency: Currency,
        to_currency: Currency,
        amount: Decimal
    ) -> dict:
        logger.info(
            "currency_conversion_requested",
            user_id=user_id,
            from_currency=from_currency.value,
            to_currency=to_currency.value,
            amount=str(amount)
        )

        if from_currency == to_currency:
            logger.error("currency_conversion_failed", reason="same_currency", user_id=user_id)
            raise ValueError("Cannot convert currency to itself")

        if from_currency == Currency.USD and to_currency == Currency.MXN:
            fx_rate = fx_rate_service.usd_to_mxn
            to_amount = amount * fx_rate
        elif from_currency == Currency.MXN and to_currency == Currency.USD:
            fx_rate = fx_rate_service.mxn_to_usd
            to_amount = amount * fx_rate
        else:
            logger.error(
                "currency_conversion_failed",
                reason="unsupported_pair",
                from_currency=from_currency.value,
                to_currency=to_currency.value
            )
            raise ValueError(f"Unsupported currency pair: {from_currency.value} -> {to_currency.value}")
        
        with Session(engine) as session:
            wallet_repo = WalletRepository(session)
            transaction_repo = TransactionRepository(session)

            from_wallet = wallet_repo.get_or_create(user_id, from_currency)

            if from_wallet.balance < amount:
                logger.error(
                    "currency_conversion_failed",
                    reason="insufficient_balance",
                    user_id=user_id,
                    currency=from_currency.value,
                    balance=str(from_wallet.balance),
                    required=str(amount)
                )
                raise ValueError(f"Insufficient balance. Available: {from_wallet.balance}, Required: {amount}")

            from_wallet.balance -= amount
            wallet_repo.update(from_wallet)

            to_wallet = wallet_repo.get_or_create(user_id, to_currency)
            to_wallet.balance += to_amount
            wallet_repo.update(to_wallet)

            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.CONVERT,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=amount,
                to_amount=to_amount,
                fx_rate=fx_rate,
            )
            transaction = transaction_repo.create(transaction)

            logger.info(
                "currency_converted",
                user_id=user_id,
                from_currency=from_currency.value,
                to_currency=to_currency.value,
                from_amount=str(amount),
                to_amount=str(to_amount),
                fx_rate=str(fx_rate),
                transaction_id=transaction.id
            )

            return {
                "user_id": user_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": amount,
                "to_amount": to_amount,
                "fx_rate": fx_rate,
            }
    
    @staticmethod
    def withdraw_funds(user_id: str, currency: Currency, amount: Decimal) -> dict:
        logger.info(
            "wallet_withdrawal_requested",
            user_id=user_id,
            currency=currency.value,
            amount=str(amount)
        )

        with Session(engine) as session:
            wallet_repo = WalletRepository(session)
            transaction_repo = TransactionRepository(session)

            wallet = wallet_repo.get_or_create(user_id, currency)

            if wallet.balance < amount:
                logger.error(
                    "wallet_withdrawal_failed",
                    reason="insufficient_balance",
                    user_id=user_id,
                    currency=currency.value,
                    balance=str(wallet.balance),
                    required=str(amount)
                )
                raise ValueError(f"Insufficient balance. Available: {wallet.balance}, Required: {amount}")

            previous_balance = wallet.balance
            wallet.balance -= amount
            wallet = wallet_repo.update(wallet)

            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.WITHDRAW,
                currency=currency,
                amount=amount,
            )
            transaction = transaction_repo.create(transaction)

            logger.info(
                "wallet_withdrawal_completed",
                user_id=user_id,
                currency=currency.value,
                amount=str(amount),
                previous_balance=str(previous_balance),
                new_balance=str(wallet.balance),
                transaction_id=transaction.id
            )

            return {
                "user_id": user_id,
                "currency": currency,
                "amount": amount,
                "new_balance": wallet.balance,
            }
    
    @staticmethod
    def get_balances(user_id: str) -> dict[str, Decimal]:
        with Session(engine) as session:
            wallet_repo = WalletRepository(session)
            wallets = wallet_repo.get_all_by_user(user_id)
            balances = {wallet.currency.value: wallet.balance for wallet in wallets}
            return balances

    @staticmethod
    def get_transactions(user_id: str, limit: Optional[int] = None) -> list[Transaction]:
        with Session(engine) as session:
            transaction_repo = TransactionRepository(session)
            return transaction_repo.get_by_user(user_id, limit)

