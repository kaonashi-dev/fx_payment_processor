from decimal import Decimal
from sqlmodel import Session, select
from src.database.engine import engine
from src.models import User, Wallet, Transaction, TransactionType
from src.models.currency import Currency
from src.config.config import settings


def seed_users():
    with Session(engine) as session:
        statement = select(User)
        existing_users = session.exec(statement).all()

        if existing_users:
            print("Users already seeded. Skipping...")
            return

        users = [
            User(id=1, email="user001@example.com", name="John Doe"),
            User(id=2, email="user002@example.com", name="Jane Smith"),
            User(id=3, email="user003@example.com", name="Bob Johnson"),
        ]

        for user in users:
            session.add(user)

        session.commit()
        print(f"✓ Seeded {len(users)} users")


def seed_wallets():
    with Session(engine) as session:
        # Check if wallets already exist
        statement = select(Wallet)
        existing_wallets = session.exec(statement).all()

        if existing_wallets:
            print("Wallets already seeded. Skipping...")
            return

        # Create sample wallets
        wallets = [
            Wallet(user_id=1, currency=Currency.USD, balance=Decimal("1000.00")),
            Wallet(user_id=1, currency=Currency.MXN, balance=Decimal("5000.00")),
            Wallet(user_id=2, currency=Currency.USD, balance=Decimal("2500.00")),
            Wallet(user_id=2, currency=Currency.MXN, balance=Decimal("0.00")),
            Wallet(user_id=3, currency=Currency.USD, balance=Decimal("500.00")),
            Wallet(user_id=3, currency=Currency.MXN, balance=Decimal("9350.00")),
        ]

        for wallet in wallets:
            session.add(wallet)

        session.commit()
        print(f"✓ Seeded {len(wallets)} wallets")


def seed_transactions():
    with Session(engine) as session:
        statement = select(Transaction)
        existing_transactions = session.exec(statement).all()

        if existing_transactions:
            print("Transactions already seeded. Skipping...")
            return

        transactions = [
            Transaction(
                user_id=1,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal("1000.00"),
            ),
            Transaction(
                user_id=1,
                transaction_type=TransactionType.FUND,
                currency=Currency.MXN,
                amount=Decimal("5000.00"),
            ),
            Transaction(
                user_id=2,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal("2500.00"),
            ),
            Transaction(
                user_id=3,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal("500.00"),
            ),
            Transaction(
                user_id=3,
                transaction_type=TransactionType.FUND,
                currency=Currency.MXN,
                amount=Decimal("9350.00"),
            ),
            Transaction(
                user_id=1,
                transaction_type=TransactionType.CONVERT,
                from_currency=Currency.USD,
                to_currency=Currency.MXN,
                from_amount=Decimal("100.00"),
                to_amount=Decimal("1870.00"),
                fx_rate=Decimal("18.70"),
            ),
            Transaction(
                user_id=2,
                transaction_type=TransactionType.CONVERT,
                from_currency=Currency.USD,
                to_currency=Currency.MXN,
                from_amount=Decimal("500.00"),
                to_amount=Decimal("9350.00"),
                fx_rate=Decimal("18.70"),
            ),
            Transaction(
                user_id=3,
                transaction_type=TransactionType.CONVERT,
                from_currency=Currency.MXN,
                to_currency=Currency.USD,
                from_amount=Decimal("1870.00"),
                to_amount=Decimal("100.00"),
                fx_rate=Decimal("0.053"),
            ),
            Transaction(
                user_id=1,
                transaction_type=TransactionType.WITHDRAW,
                currency=Currency.USD,
                amount=Decimal("200.00"),
            ),
            Transaction(
                user_id=2,
                transaction_type=TransactionType.WITHDRAW,
                currency=Currency.USD,
                amount=Decimal("100.00"),
            ),
        ]

        for transaction in transactions:
            session.add(transaction)

        session.commit()
        print(f"✓ Seeded {len(transactions)} transactions")


def seed_all():
    print("Starting database seeding...")
    print(f"Database URL: {settings.database_url}")
    print("-" * 50)

    try:
        seed_users()
        seed_wallets()
        seed_transactions()
        print("-" * 50)
        print("✓ Database seeding completed successfully!")
    except Exception as e:
        print(f"✗ Error seeding database: {e}")
        raise


if __name__ == "__main__":
    seed_all()
