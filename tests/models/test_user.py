"""Unit tests for User model."""
import pytest
from datetime import datetime
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from src.models import User


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


class TestUserCreation:
    """Tests for User model creation."""

    def test_create_user_with_all_fields(self, session):
        """Test creating a user with all required fields."""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.created_at is not None
        assert user.updated_at is None

    def test_user_id_is_autoincrement(self, session):
        """Test that user id is auto-incremented."""
        user1 = User(email="user1@example.com", name="User 1")
        session.add(user1)
        session.commit()
        session.refresh(user1)

        user2 = User(email="user2@example.com", name="User 2")
        session.add(user2)
        session.commit()
        session.refresh(user2)

        assert user2.id > user1.id

    def test_user_created_at_auto_set(self, session):
        """Test that created_at is automatically set."""
        before_creation = datetime.utcnow()

        user = User(email="auto@example.com", name="Auto User")
        session.add(user)
        session.commit()
        session.refresh(user)

        after_creation = datetime.utcnow()

        assert user.created_at is not None
        assert before_creation <= user.created_at <= after_creation

    def test_user_email_required(self, session):
        """Test that email is required."""
        with pytest.raises(Exception):  # Should raise validation error
            user = User(name="No Email User")
            session.add(user)
            session.commit()

    def test_user_name_required(self, session):
        """Test that name is required."""
        with pytest.raises(Exception):  # Should raise validation error
            user = User(email="noemail@example.com")
            session.add(user)
            session.commit()


class TestUserRetrieval:
    """Tests for User model retrieval."""

    def test_get_user_by_id(self, session):
        """Test retrieving a user by id."""
        user = User(email="retrieve@example.com", name="Retrieve User")
        session.add(user)
        session.commit()
        session.refresh(user)

        retrieved_user = session.get(User, user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "retrieve@example.com"
        assert retrieved_user.name == "Retrieve User"

    def test_get_user_by_query(self, session):
        """Test retrieving a user using query."""
        user = User(email="query@example.com", name="Query User")
        session.add(user)
        session.commit()

        statement = select(User).where(User.email == "query@example.com")
        retrieved_user = session.exec(statement).first()

        assert retrieved_user is not None
        assert retrieved_user.email == "query@example.com"
        assert retrieved_user.name == "Query User"

    def test_get_nonexistent_user(self, session):
        """Test retrieving a non-existent user returns None."""
        retrieved_user = session.get(User, 999999)
        assert retrieved_user is None

    def test_get_all_users(self, session):
        """Test retrieving all users."""
        users = [
            User(email="user1@example.com", name="User 1"),
            User(email="user2@example.com", name="User 2"),
            User(email="user3@example.com", name="User 3"),
        ]
        for user in users:
            session.add(user)
        session.commit()

        statement = select(User)
        all_users = session.exec(statement).all()

        assert len(all_users) == 3
        emails = {user.email for user in all_users}
        assert emails == {"user1@example.com", "user2@example.com", "user3@example.com"}


class TestUserUpdate:
    """Tests for User model updates."""

    def test_update_user_email(self, session):
        """Test updating user email."""
        user = User(email="old@example.com", name="Test User")
        session.add(user)
        session.commit()
        session.refresh(user)

        user.email = "new@example.com"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.email == "new@example.com"

    def test_update_user_name(self, session):
        """Test updating user name."""
        user = User(email="test@example.com", name="Old Name")
        session.add(user)
        session.commit()
        session.refresh(user)

        user.name = "New Name"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.name == "New Name"

    def test_update_user_updated_at(self, session):
        """Test that updated_at can be set manually."""
        user = User(email="update@example.com", name="Update User")
        session.add(user)
        session.commit()
        session.refresh(user)

        initial_updated_at = user.updated_at
        update_time = datetime.utcnow()

        user.updated_at = update_time
        user.name = "Updated User"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.updated_at == update_time
        assert user.name == "Updated User"

    def test_update_multiple_fields(self, session):
        """Test updating multiple fields at once."""
        user = User(email="old@example.com", name="Old Name")
        session.add(user)
        session.commit()
        session.refresh(user)

        user.email = "new@example.com"
        user.name = "New Name"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.email == "new@example.com"
        assert user.name == "New Name"


class TestUserDeletion:
    """Tests for User model deletion."""

    def test_delete_user(self, session):
        """Test deleting a user."""
        user = User(email="delete@example.com", name="Delete User")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

        session.delete(user)
        session.commit()

        retrieved_user = session.get(User, user_id)
        assert retrieved_user is None

    def test_delete_user_by_id(self, session):
        """Test deleting a user by id."""
        user = User(email="delete2@example.com", name="Delete User 2")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

        user_to_delete = session.get(User, user_id)
        session.delete(user_to_delete)
        session.commit()

        assert session.get(User, user_id) is None


class TestUserValidation:
    """Tests for User model validation."""

    def test_user_email_max_length(self, session):
        """Test that email respects max_length constraint."""
        # Create email at max length (255 chars)
        # "@example.com" is 12 chars, so we need 243 chars for the prefix
        long_email = "a" * 243 + "@example.com"  # 255 chars total
        user = User(email=long_email, name="Long Email User")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert len(user.email) == 255

    def test_user_name_max_length(self, session):
        """Test that name respects max_length constraint."""
        # Create name at max length (255 chars)
        long_name = "A" * 255
        user = User(email="longname@example.com", name=long_name)
        session.add(user)
        session.commit()
        session.refresh(user)

        assert len(user.name) == 255

    def test_user_repr(self, session):
        """Test user string representation."""
        user = User(email="repr@example.com", name="Repr User")
        session.add(user)
        session.commit()
        session.refresh(user)

        repr_str = repr(user)
        assert str(user.id) in repr_str
        assert "repr@example.com" in repr_str
        assert "Repr User" in repr_str


class TestUserTimestamps:
    """Tests for User timestamp fields."""

    def test_created_at_persists(self, session):
        """Test that created_at persists across sessions."""
        user = User(email="timestamp@example.com", name="Timestamp User")
        session.add(user)
        session.commit()
        session.refresh(user)

        original_created_at = user.created_at

        # Simulate update
        user.name = "Updated"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.created_at == original_created_at

    def test_updated_at_starts_as_none(self, session):
        """Test that updated_at starts as None."""
        user = User(email="updatedat@example.com", name="Update At User")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.updated_at is None

    def test_created_at_not_nullable(self, session):
        """Test that created_at cannot be None."""
        user = User(email="notnull@example.com", name="Not Null User")
        # created_at should be set automatically
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.created_at is not None


class TestUserIntegration:
    """Tests for User integration with other models."""

    def test_user_id_as_string_in_wallets(self, session):
        """Test that user_id in wallets can be a string (not tied to User table)."""
        from src.models import Wallet
        from decimal import Decimal

        # Note: Wallet.user_id is a string and doesn't have FK to User table
        # This allows flexible user identification
        wallet1 = Wallet(user_id="external_user_123", currency="USD", balance=Decimal("1000.00"))
        wallet2 = Wallet(user_id="external_user_123", currency="MXN", balance=Decimal("5000.00"))
        session.add(wallet1)
        session.add(wallet2)
        session.commit()

        # Verify wallets exist
        from sqlmodel import select
        statement = select(Wallet).where(Wallet.user_id == "external_user_123")
        wallets = session.exec(statement).all()
        assert len(wallets) == 2

    def test_user_id_as_string_in_transactions(self, session):
        """Test that user_id in transactions can be a string."""
        from src.models import Transaction, TransactionType
        from decimal import Decimal

        # Note: Transaction.user_id is a string and doesn't have FK to User table
        transaction = Transaction(
            user_id="external_user_456",
            transaction_type=TransactionType.FUND,
            currency="USD",
            amount=Decimal("1000.00")
        )
        session.add(transaction)
        session.commit()

        # Verify transaction exists
        from sqlmodel import select
        statement = select(Transaction).where(Transaction.user_id == "external_user_456")
        transactions = session.exec(statement).all()
        assert len(transactions) == 1

