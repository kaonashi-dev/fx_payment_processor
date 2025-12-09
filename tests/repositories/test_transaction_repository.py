"""Unit tests for TransactionRepository."""
import pytest
from decimal import Decimal
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from src.repositories.transaction_repository import TransactionRepository
from src.models import Transaction
from src.models.transaction import TransactionType
from src.models.currency import Currency


@pytest.fixture(scope="function")
def test_db():
    """Create a test database in memory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(test_db):
    """Create a test session."""
    with Session(test_db) as session:
        yield session


@pytest.fixture(scope="function")
def transaction_repository(session):
    """Create a TransactionRepository instance."""
    return TransactionRepository(session)


class TestTransactionRepositoryCreate:
    """Tests for create method."""

    def test_create_fund_transaction(self, transaction_repository, session):
        """Test creating a fund transaction."""
        transaction = Transaction(
            user_id="user_001",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("1000.00")
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.id is not None
        assert created_transaction.user_id == "user_001"
        assert created_transaction.transaction_type == TransactionType.FUND
        assert created_transaction.currency == Currency.USD
        assert created_transaction.amount == Decimal("1000.00")
        assert created_transaction.created_at is not None

    def test_create_withdraw_transaction(self, transaction_repository, session):
        """Test creating a withdraw transaction."""
        transaction = Transaction(
            user_id="user_002",
            transaction_type=TransactionType.WITHDRAW,
            currency=Currency.MXN,
            amount=Decimal("500.00")
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.transaction_type == TransactionType.WITHDRAW
        assert created_transaction.currency == Currency.MXN
        assert created_transaction.amount == Decimal("500.00")

    def test_create_convert_transaction(self, transaction_repository, session):
        """Test creating a convert transaction."""
        transaction = Transaction(
            user_id="user_003",
            transaction_type=TransactionType.CONVERT,
            from_currency=Currency.USD,
            to_currency=Currency.MXN,
            from_amount=Decimal("100.00"),
            to_amount=Decimal("1870.00"),
            fx_rate=Decimal("18.70")
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.transaction_type == TransactionType.CONVERT
        assert created_transaction.from_currency == Currency.USD
        assert created_transaction.to_currency == Currency.MXN
        assert created_transaction.from_amount == Decimal("100.00")
        assert created_transaction.to_amount == Decimal("1870.00")
        assert created_transaction.fx_rate == Decimal("18.70")


class TestTransactionRepositoryGetById:
    """Tests for get_by_id method."""

    def test_get_existing_transaction(self, transaction_repository, session):
        """Test getting an existing transaction by id."""
        transaction = Transaction(
            user_id="user_004",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("250.00")
        )
        created_transaction = transaction_repository.create(transaction)

        retrieved_transaction = transaction_repository.get_by_id(created_transaction.id)

        assert retrieved_transaction is not None
        assert retrieved_transaction.id == created_transaction.id
        assert retrieved_transaction.amount == Decimal("250.00")

    def test_get_nonexistent_transaction(self, transaction_repository, session):
        """Test getting a non-existent transaction returns None."""
        transaction = transaction_repository.get_by_id(999999)

        assert transaction is None


class TestTransactionRepositoryGetByUser:
    """Tests for get_by_user method."""

    def test_get_by_user_multiple_transactions(self, transaction_repository, session):
        """Test getting all transactions for a user."""
        user_id = "user_005"

        # Create multiple transactions
        for i in range(3):
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            transaction_repository.create(transaction)

        transactions = transaction_repository.get_by_user(user_id)

        assert len(transactions) == 3

    def test_get_by_user_ordered_by_created_at_desc(self, transaction_repository, session):
        """Test that transactions are ordered by created_at descending (newest first)."""
        user_id = "user_006"

        # Create transactions with different amounts
        amounts = [Decimal("100.00"), Decimal("200.00"), Decimal("300.00")]
        for amount in amounts:
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=amount
            )
            transaction_repository.create(transaction)

        transactions = transaction_repository.get_by_user(user_id)

        # First transaction should be the most recent (last created)
        assert transactions[0].amount == Decimal("300.00")
        assert transactions[-1].amount == Decimal("100.00")

    def test_get_by_user_with_limit(self, transaction_repository, session):
        """Test getting transactions with limit."""
        user_id = "user_007"

        # Create 5 transactions
        for i in range(5):
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            transaction_repository.create(transaction)

        transactions = transaction_repository.get_by_user(user_id, limit=3)

        assert len(transactions) == 3

    def test_get_by_user_no_transactions(self, transaction_repository, session):
        """Test getting transactions for user with no transactions."""
        transactions = transaction_repository.get_by_user("nonexistent_user")

        assert transactions == []

    def test_get_by_user_multiple_users_isolation(self, transaction_repository, session):
        """Test that get_by_user only returns transactions for the specific user."""
        # Create transactions for different users
        transaction1 = Transaction(
            user_id="user_008",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("100.00")
        )
        transaction_repository.create(transaction1)

        transaction2 = Transaction(
            user_id="user_009",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("200.00")
        )
        transaction_repository.create(transaction2)

        transactions_user_008 = transaction_repository.get_by_user("user_008")
        transactions_user_009 = transaction_repository.get_by_user("user_009")

        assert len(transactions_user_008) == 1
        assert len(transactions_user_009) == 1
        assert transactions_user_008[0].amount == Decimal("100.00")
        assert transactions_user_009[0].amount == Decimal("200.00")


class TestTransactionRepositoryGetByUserAndType:
    """Tests for get_by_user_and_type method."""

    def test_get_by_user_and_type_fund(self, transaction_repository, session):
        """Test getting only fund transactions for a user."""
        user_id = "user_010"

        # Create mixed transactions
        fund_tx = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("1000.00")
        )
        transaction_repository.create(fund_tx)

        withdraw_tx = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.WITHDRAW,
            currency=Currency.USD,
            amount=Decimal("500.00")
        )
        transaction_repository.create(withdraw_tx)

        transactions = transaction_repository.get_by_user_and_type(
            user_id,
            TransactionType.FUND
        )

        assert len(transactions) == 1
        assert transactions[0].transaction_type == TransactionType.FUND
        assert transactions[0].amount == Decimal("1000.00")

    def test_get_by_user_and_type_withdraw(self, transaction_repository, session):
        """Test getting only withdraw transactions for a user."""
        user_id = "user_011"

        # Create multiple withdraw transactions
        for i in range(2):
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.WITHDRAW,
                currency=Currency.USD,
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            transaction_repository.create(transaction)

        # Create a fund transaction
        fund_tx = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("1000.00")
        )
        transaction_repository.create(fund_tx)

        transactions = transaction_repository.get_by_user_and_type(
            user_id,
            TransactionType.WITHDRAW
        )

        assert len(transactions) == 2
        assert all(tx.transaction_type == TransactionType.WITHDRAW for tx in transactions)

    def test_get_by_user_and_type_convert(self, transaction_repository, session):
        """Test getting only convert transactions for a user."""
        user_id = "user_012"

        # Create a convert transaction
        convert_tx = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.CONVERT,
            from_currency=Currency.USD,
            to_currency=Currency.MXN,
            from_amount=Decimal("100.00"),
            to_amount=Decimal("1870.00"),
            fx_rate=Decimal("18.70")
        )
        transaction_repository.create(convert_tx)

        # Create other transactions
        fund_tx = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("1000.00")
        )
        transaction_repository.create(fund_tx)

        transactions = transaction_repository.get_by_user_and_type(
            user_id,
            TransactionType.CONVERT
        )

        assert len(transactions) == 1
        assert transactions[0].transaction_type == TransactionType.CONVERT

    def test_get_by_user_and_type_with_limit(self, transaction_repository, session):
        """Test getting transactions by type with limit."""
        user_id = "user_013"

        # Create 5 fund transactions
        for i in range(5):
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            transaction_repository.create(transaction)

        transactions = transaction_repository.get_by_user_and_type(
            user_id,
            TransactionType.FUND,
            limit=3
        )

        assert len(transactions) == 3

    def test_get_by_user_and_type_no_matching_transactions(self, transaction_repository, session):
        """Test getting transactions by type when none match."""
        user_id = "user_014"

        # Create only fund transactions
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=Decimal("1000.00")
        )
        transaction_repository.create(transaction)

        # Try to get withdraw transactions
        transactions = transaction_repository.get_by_user_and_type(
            user_id,
            TransactionType.WITHDRAW
        )

        assert transactions == []


class TestTransactionRepositoryEdgeCases:
    """Edge case tests for TransactionRepository."""

    def test_create_transaction_very_large_amount(self, transaction_repository, session):
        """Test creating a transaction with very large amount."""
        large_amount = Decimal("999999999.99")
        transaction = Transaction(
            user_id="user_015",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=large_amount
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.amount == large_amount

    def test_create_transaction_precision(self, transaction_repository, session):
        """Test that transaction amounts maintain precision."""
        precise_amount = Decimal("123.45")
        transaction = Transaction(
            user_id="user_016",
            transaction_type=TransactionType.FUND,
            currency=Currency.USD,
            amount=precise_amount
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.amount == precise_amount

    def test_convert_transaction_fx_rate_precision(self, transaction_repository, session):
        """Test that FX rates maintain precision."""
        transaction = Transaction(
            user_id="user_017",
            transaction_type=TransactionType.CONVERT,
            from_currency=Currency.MXN,
            to_currency=Currency.USD,
            from_amount=Decimal("1870.00"),
            to_amount=Decimal("99.11"),
            fx_rate=Decimal("0.053")  # 4 decimal places
        )

        created_transaction = transaction_repository.create(transaction)

        assert created_transaction.fx_rate == Decimal("0.053")

    def test_get_by_user_empty_limit(self, transaction_repository, session):
        """Test that limit=None returns all transactions."""
        user_id = "user_018"

        # Create 10 transactions
        for i in range(10):
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FUND,
                currency=Currency.USD,
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            transaction_repository.create(transaction)

        transactions = transaction_repository.get_by_user(user_id, limit=None)

        assert len(transactions) == 10
