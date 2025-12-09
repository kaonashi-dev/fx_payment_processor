"""Unit tests for UserRepository."""
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from src.repositories.user_repository import UserRepository
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


@pytest.fixture(scope="function")
def user_repository(session):
    """Create a UserRepository instance."""
    return UserRepository(session)


@pytest.fixture(scope="function")
def sample_user(session):
    """Create a sample user for testing."""
    user = User(email="test@example.com", name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestUserRepositoryGetById:
    """Tests for get_by_id method."""

    def test_get_existing_user(self, user_repository, sample_user):
        """Test getting an existing user by id."""
        retrieved_user = user_repository.get_by_id(sample_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == sample_user.id
        assert retrieved_user.email == sample_user.email
        assert retrieved_user.name == sample_user.name

    def test_get_nonexistent_user(self, user_repository):
        """Test getting a non-existent user returns None."""
        user = user_repository.get_by_id(999999)
        assert user is None

    def test_get_by_id_with_different_users(self, user_repository, session):
        """Test getting users by different IDs."""
        # Create multiple users
        user1 = User(email="user1@example.com", name="User One")
        user2 = User(email="user2@example.com", name="User Two")
        session.add(user1)
        session.add(user2)
        session.commit()
        session.refresh(user1)
        session.refresh(user2)

        # Get each user by ID
        retrieved_user1 = user_repository.get_by_id(user1.id)
        retrieved_user2 = user_repository.get_by_id(user2.id)

        assert retrieved_user1.id == user1.id
        assert retrieved_user2.id == user2.id
        assert retrieved_user1.email == "user1@example.com"
        assert retrieved_user2.email == "user2@example.com"


class TestUserRepositoryExists:
    """Tests for exists method."""

    def test_exists_for_existing_user(self, user_repository, sample_user):
        """Test that exists returns True for existing user."""
        assert user_repository.exists(sample_user.id) is True

    def test_exists_for_nonexistent_user(self, user_repository):
        """Test that exists returns False for non-existent user."""
        assert user_repository.exists(999999) is False

    def test_exists_after_user_creation(self, user_repository, session):
        """Test that exists returns True after creating a user."""
        # Check user doesn't exist
        assert user_repository.exists(1) is False

        # Create user
        user = User(email="new@example.com", name="New User")
        session.add(user)
        session.commit()
        session.refresh(user)

        # Check user now exists
        assert user_repository.exists(user.id) is True

    def test_exists_with_multiple_users(self, user_repository, session):
        """Test exists with multiple users."""
        # Create multiple users
        users = [
            User(email=f"user{i}@example.com", name=f"User {i}")
            for i in range(1, 4)
        ]
        for user in users:
            session.add(user)
        session.commit()
        for user in users:
            session.refresh(user)

        # All users should exist
        for user in users:
            assert user_repository.exists(user.id) is True

        # Non-existent user should not exist
        assert user_repository.exists(999) is False


class TestUserRepositoryEdgeCases:
    """Edge case tests for UserRepository."""

    def test_get_by_id_with_zero(self, user_repository):
        """Test getting user with id 0."""
        user = user_repository.get_by_id(0)
        assert user is None

    def test_get_by_id_with_negative(self, user_repository):
        """Test getting user with negative id."""
        user = user_repository.get_by_id(-1)
        assert user is None

    def test_exists_with_zero(self, user_repository):
        """Test exists with id 0."""
        assert user_repository.exists(0) is False

    def test_exists_with_negative(self, user_repository):
        """Test exists with negative id."""
        assert user_repository.exists(-1) is False

    def test_repository_reusable(self, session):
        """Test that repository can be reused for multiple operations."""
        repo = UserRepository(session)

        # Create user
        user1 = User(email="user1@example.com", name="User 1")
        session.add(user1)
        session.commit()
        session.refresh(user1)

        # Get user
        retrieved = repo.get_by_id(user1.id)
        assert retrieved is not None

        # Check exists
        assert repo.exists(user1.id) is True

        # Create another user
        user2 = User(email="user2@example.com", name="User 2")
        session.add(user2)
        session.commit()
        session.refresh(user2)

        # Both users should be accessible
        assert repo.exists(user1.id) is True
        assert repo.exists(user2.id) is True
