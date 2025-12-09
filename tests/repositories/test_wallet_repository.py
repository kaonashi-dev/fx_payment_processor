"""Unit tests for WalletRepository."""
import pytest
from decimal import Decimal
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from src.repositories.wallet_repository import WalletRepository
from src.models import Wallet
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
def wallet_repository(session):
    """Create a WalletRepository instance."""
    return WalletRepository(session)


class TestWalletRepositoryCreate:
    """Tests for create method."""

    def test_create_wallet_default_balance(self, wallet_repository, session):
        """Test creating a wallet with default balance."""
        wallet = wallet_repository.create("user_001", Currency.USD)

        assert wallet.id is not None
        assert wallet.user_id == "user_001"
        assert wallet.currency == Currency.USD
        assert wallet.balance == Decimal("0.00")

    def test_create_wallet_custom_balance(self, wallet_repository, session):
        """Test creating a wallet with custom balance."""
        wallet = wallet_repository.create(
            "user_002",
            Currency.MXN,
            balance=Decimal("1000.00")
        )

        assert wallet.user_id == "user_002"
        assert wallet.currency == Currency.MXN
        assert wallet.balance == Decimal("1000.00")

    def test_create_multiple_wallets_same_user(self, wallet_repository, session):
        """Test creating multiple wallets for the same user."""
        wallet_usd = wallet_repository.create("user_003", Currency.USD)
        wallet_mxn = wallet_repository.create("user_003", Currency.MXN)

        assert wallet_usd.user_id == wallet_mxn.user_id
        assert wallet_usd.currency != wallet_mxn.currency
        assert wallet_usd.id != wallet_mxn.id


class TestWalletRepositoryGetByUserAndCurrency:
    """Tests for get_by_user_and_currency method."""

    def test_get_existing_wallet(self, wallet_repository, session):
        """Test getting an existing wallet."""
        created_wallet = wallet_repository.create(
            "user_004",
            Currency.USD,
            balance=Decimal("500.00")
        )

        retrieved_wallet = wallet_repository.get_by_user_and_currency(
            "user_004",
            Currency.USD
        )

        assert retrieved_wallet is not None
        assert retrieved_wallet.id == created_wallet.id
        assert retrieved_wallet.balance == Decimal("500.00")

    def test_get_nonexistent_wallet(self, wallet_repository, session):
        """Test getting a non-existent wallet returns None."""
        wallet = wallet_repository.get_by_user_and_currency(
            "nonexistent_user",
            Currency.USD
        )

        assert wallet is None

    def test_get_wallet_wrong_currency(self, wallet_repository, session):
        """Test getting a wallet with wrong currency returns None."""
        wallet_repository.create("user_005", Currency.USD)

        wallet = wallet_repository.get_by_user_and_currency(
            "user_005",
            Currency.MXN
        )

        assert wallet is None


class TestWalletRepositoryGetAllByUser:
    """Tests for get_all_by_user method."""

    def test_get_all_wallets_multiple_currencies(self, wallet_repository, session):
        """Test getting all wallets for a user with multiple currencies."""
        wallet_repository.create("user_006", Currency.USD, Decimal("1000.00"))
        wallet_repository.create("user_006", Currency.MXN, Decimal("5000.00"))

        wallets = wallet_repository.get_all_by_user("user_006")

        assert len(wallets) == 2
        currencies = {w.currency for w in wallets}
        assert currencies == {Currency.USD, Currency.MXN}

    def test_get_all_wallets_single_currency(self, wallet_repository, session):
        """Test getting all wallets for a user with single currency."""
        wallet_repository.create("user_007", Currency.USD)

        wallets = wallet_repository.get_all_by_user("user_007")

        assert len(wallets) == 1
        assert wallets[0].currency == Currency.USD

    def test_get_all_wallets_no_wallets(self, wallet_repository, session):
        """Test getting all wallets for a user with no wallets."""
        wallets = wallet_repository.get_all_by_user("user_008")

        assert wallets == []

    def test_get_all_wallets_multiple_users(self, wallet_repository, session):
        """Test that get_all_by_user only returns wallets for the specific user."""
        wallet_repository.create("user_009", Currency.USD)
        wallet_repository.create("user_010", Currency.USD)
        wallet_repository.create("user_010", Currency.MXN)

        wallets_user_009 = wallet_repository.get_all_by_user("user_009")
        wallets_user_010 = wallet_repository.get_all_by_user("user_010")

        assert len(wallets_user_009) == 1
        assert len(wallets_user_010) == 2


class TestWalletRepositoryUpdate:
    """Tests for update method."""

    def test_update_wallet_balance(self, wallet_repository, session):
        """Test updating a wallet balance."""
        wallet = wallet_repository.create("user_011", Currency.USD, Decimal("100.00"))

        wallet.balance = Decimal("500.00")
        updated_wallet = wallet_repository.update(wallet)

        assert updated_wallet.balance == Decimal("500.00")

        # Verify persistence
        retrieved_wallet = wallet_repository.get_by_user_and_currency(
            "user_011",
            Currency.USD
        )
        assert retrieved_wallet.balance == Decimal("500.00")

    def test_update_wallet_multiple_times(self, wallet_repository, session):
        """Test updating a wallet multiple times."""
        wallet = wallet_repository.create("user_012", Currency.USD, Decimal("0.00"))

        wallet.balance = Decimal("100.00")
        wallet_repository.update(wallet)

        wallet.balance = Decimal("200.00")
        wallet_repository.update(wallet)

        wallet.balance = Decimal("300.00")
        final_wallet = wallet_repository.update(wallet)

        assert final_wallet.balance == Decimal("300.00")


class TestWalletRepositoryGetOrCreate:
    """Tests for get_or_create method."""

    def test_get_or_create_existing_wallet(self, wallet_repository, session):
        """Test get_or_create returns existing wallet."""
        original_wallet = wallet_repository.create(
            "user_013",
            Currency.USD,
            Decimal("1000.00")
        )

        wallet = wallet_repository.get_or_create("user_013", Currency.USD)

        assert wallet.id == original_wallet.id
        assert wallet.balance == Decimal("1000.00")

    def test_get_or_create_new_wallet(self, wallet_repository, session):
        """Test get_or_create creates new wallet if it doesn't exist."""
        wallet = wallet_repository.get_or_create("user_014", Currency.USD)

        assert wallet.id is not None
        assert wallet.user_id == "user_014"
        assert wallet.currency == Currency.USD
        assert wallet.balance == Decimal("0.00")

    def test_get_or_create_idempotent(self, wallet_repository, session):
        """Test get_or_create is idempotent."""
        wallet1 = wallet_repository.get_or_create("user_015", Currency.USD)
        wallet2 = wallet_repository.get_or_create("user_015", Currency.USD)

        assert wallet1.id == wallet2.id

        # Verify only one wallet was created
        wallets = wallet_repository.get_all_by_user("user_015")
        assert len(wallets) == 1


class TestWalletRepositoryEdgeCases:
    """Edge case tests for WalletRepository."""

    def test_create_wallet_very_large_balance(self, wallet_repository, session):
        """Test creating a wallet with very large balance."""
        large_balance = Decimal("999999999.99")
        wallet = wallet_repository.create("user_016", Currency.USD, large_balance)

        assert wallet.balance == large_balance

    def test_update_wallet_to_zero_balance(self, wallet_repository, session):
        """Test updating a wallet to zero balance."""
        wallet = wallet_repository.create("user_017", Currency.USD, Decimal("1000.00"))

        wallet.balance = Decimal("0.00")
        updated_wallet = wallet_repository.update(wallet)

        assert updated_wallet.balance == Decimal("0.00")

    def test_currency_uniqueness_constraint(self, wallet_repository, session):
        """Test that user can have only one wallet per currency."""
        wallet_repository.create("user_018", Currency.USD)

        # Attempting to create another USD wallet for the same user should fail
        with pytest.raises(Exception):  # Should raise integrity error
            wallet = Wallet(user_id="user_018", currency=Currency.USD, balance=Decimal("0.00"))
            session.add(wallet)
            session.commit()
