"""Integration tests for wallet API routes."""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from src.main import app
from src.models import Wallet, Transaction, User
from src.database.engine import get_session
import src.services.wallet_service as wallet_service_module
import src.api.dependencies as dependencies_module


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_client(test_engine):
    """Create a test client with in-memory database."""

    def get_test_session():
        with Session(test_engine) as session:
            yield session

    # Override the get_session dependency
    app.dependency_overrides[get_session] = get_test_session

    # Replace the engine in wallet_service module
    original_engine = wallet_service_module.engine
    wallet_service_module.engine = test_engine

    # Replace the engine in dependencies module
    original_deps_engine = dependencies_module.engine
    dependencies_module.engine = test_engine

    try:
        client = TestClient(app)
        yield client
    finally:
        app.dependency_overrides.clear()
        wallet_service_module.engine = original_engine
        dependencies_module.engine = original_deps_engine


@pytest.fixture(scope="function")
def test_session(test_engine, test_client):
    """Create a test session using the same engine as test_client."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_user(test_session):
    """Create a test user."""
    user = User(id=1, email="test@example.com", name="Test User")
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_users(test_session):
    """Create multiple test users."""
    users = [
        User(id=1, email="user1@example.com", name="User One"),
        User(id=2, email="user2@example.com", name="User Two"),
        User(id=3, email="user3@example.com", name="User Three"),
    ]
    for user in users:
        test_session.add(user)
    test_session.commit()
    for user in users:
        test_session.refresh(user)
    return users


class TestUserValidation:
    """Tests for user validation middleware."""
    
    def test_user_not_found_returns_404(self, test_client):
        """Test that non-existent user returns 404."""
        response = test_client.post(
            "/wallets/999/fund",
            json={"currency": "USD", "amount": "100.00"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_invalid_user_id_format_returns_400(self, test_client):
        """Test that invalid user_id format returns 400."""
        response = test_client.post(
            "/wallets/invalid_user/fund",
            json={"currency": "USD", "amount": "100.00"}
        )
        assert response.status_code == 400
        assert "Invalid user_id format" in response.json()["detail"]
    
    def test_user_validation_on_all_endpoints(self, test_client, test_user):
        """Test that user validation works on all endpoints."""
        user_id = str(test_user.id)
        
        # Test fund endpoint - should succeed (user exists)
        response = test_client.post(
            f"/wallets/{user_id}/fund",
            json={"currency": "USD", "amount": "100.00"}
        )
        assert response.status_code == 201
        
        # Test convert endpoint - should succeed now that user has balance
        response = test_client.post(
            f"/wallets/{user_id}/convert",
            json={"from_currency": "USD", "to_currency": "MXN", "amount": "50.00"}
        )
        # Should succeed (user exists and has balance)
        assert response.status_code == 200
        
        # Test withdraw endpoint - should succeed
        response = test_client.post(
            f"/wallets/{user_id}/withdraw",
            json={"currency": "MXN", "amount": "50.00"}
        )
        # Should succeed (user exists and has balance)
        assert response.status_code == 200
        
        # Test get balances endpoint - should succeed
        response = test_client.get(f"/wallets/{user_id}/balances")
        assert response.status_code == 200
        
        # Test get transactions endpoint - should succeed
        response = test_client.get(f"/wallets/{user_id}/transactions")
        assert response.status_code == 200


class TestFundWallet:
    """Tests for POST /wallets/{user_id}/fund endpoint."""
    
    def test_fund_wallet_success(self, test_client, test_session, test_user):
        """Test successful wallet funding."""
        user_id = str(test_user.id)
        response = test_client.post(
            f"/wallets/{user_id}/fund",
            json={"currency": "USD", "amount": "1000.00"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert data["currency"] == "USD"
        assert data["amount"] == "1000.00"
        assert data["new_balance"] == "1000.00"
        assert "message" in data
    
    def test_fund_wallet_existing_wallet(self, test_client, test_session, test_users):
        """Test funding existing wallet adds to balance."""
        user = test_users[1]  # Use user with id=2
        user_id = str(user.id)
        
        # Create initial wallet
        wallet = Wallet(user_id=user.id, currency="USD", balance=Decimal("500.00"))
        test_session.add(wallet)
        test_session.commit()
        
        response = test_client.post(
            f"/wallets/{user_id}/fund",
            json={"currency": "USD", "amount": "250.00"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["new_balance"] == "750.00"
    
    def test_fund_wallet_invalid_amount(self, test_client, test_user):
        """Test funding with invalid amount."""
        user_id = str(test_user.id)
        response = test_client.post(
            f"/wallets/{user_id}/fund",
            json={"currency": "USD", "amount": "-100.00"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_fund_wallet_missing_fields(self, test_client, test_user):
        """Test funding with missing required fields."""
        user_id = str(test_user.id)
        response = test_client.post(
            f"/wallets/{user_id}/fund",
            json={"currency": "USD"}
        )
        
        assert response.status_code == 422


class TestConvertCurrency:
    """Tests for POST /wallets/{user_id}/convert endpoint."""
    
    def test_convert_usd_to_mxn_success(self, test_client, test_session, test_user):
        """Test successful USD to MXN conversion."""
        user_id = str(test_user.id)
        # Create USD wallet with balance
        wallet = Wallet(user_id=test_user.id, currency="USD", balance=Decimal("1000.00"))
        test_session.add(wallet)
        test_session.commit()

        response = test_client.post(
            f"/wallets/{user_id}/convert",
            json={
                "from_currency": "USD",
                "to_currency": "MXN",
                "amount": "100.00"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "MXN"
        assert data["from_amount"] == "100.00"
        # Allow some decimal precision differences
        assert Decimal(data["to_amount"]) == Decimal("1870.00")  # 100 * 18.70
        assert Decimal(data["fx_rate"]) == Decimal("18.70")
    
    def test_convert_insufficient_balance(self, test_client, test_session, test_users):
        """Test conversion with insufficient balance."""
        user = test_users[1]  # Use user with id=2
        user_id = str(user.id)
        wallet = Wallet(user_id=user.id, currency="USD", balance=Decimal("50.00"))
        test_session.add(wallet)
        test_session.commit()
        
        response = test_client.post(
            f"/wallets/{user_id}/convert",
            json={
                "from_currency": "USD",
                "to_currency": "MXN",
                "amount": "100.00"
            }
        )
        
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]
    
    def test_convert_same_currency(self, test_client, test_user):
        """Test conversion with same currency fails."""
        user_id = str(test_user.id)
        response = test_client.post(
            f"/wallets/{user_id}/convert",
            json={
                "from_currency": "USD",
                "to_currency": "USD",
                "amount": "100.00"
            }
        )
        
        assert response.status_code == 400
        assert "Cannot convert currency to itself" in response.json()["detail"]


class TestWithdrawFunds:
    """Tests for POST /wallets/{user_id}/withdraw endpoint."""
    
    def test_withdraw_success(self, test_client, test_session, test_user):
        """Test successful withdrawal."""
        user_id = str(test_user.id)
        wallet = Wallet(user_id=test_user.id, currency="USD", balance=Decimal("1000.00"))
        test_session.add(wallet)
        test_session.commit()
        
        response = test_client.post(
            f"/wallets/{user_id}/withdraw",
            json={"currency": "USD", "amount": "300.00"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
        assert data["amount"] == "300.00"
        assert data["new_balance"] == "700.00"
    
    def test_withdraw_insufficient_balance(self, test_client, test_session, test_users):
        """Test withdrawal with insufficient balance."""
        user = test_users[2]  # Use user with id=3
        user_id = str(user.id)
        wallet = Wallet(user_id=user.id, currency="USD", balance=Decimal("100.00"))
        test_session.add(wallet)
        test_session.commit()
        
        response = test_client.post(
            f"/wallets/{user_id}/withdraw",
            json={"currency": "USD", "amount": "500.00"}
        )
        
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]
    
    def test_withdraw_invalid_amount(self, test_client, test_user):
        """Test withdrawal with invalid amount."""
        user_id = str(test_user.id)
        response = test_client.post(
            f"/wallets/{user_id}/withdraw",
            json={"currency": "USD", "amount": "-50.00"}
        )
        
        assert response.status_code == 422


class TestGetBalances:
    """Tests for GET /wallets/{user_id}/balances endpoint."""
    
    def test_get_balances_success(self, test_client, test_session, test_user):
        """Test getting balances for user with multiple currencies."""
        user_id = str(test_user.id)
        wallets = [
            Wallet(user_id=test_user.id, currency="USD", balance=Decimal("1000.00")),
            Wallet(user_id=test_user.id, currency="MXN", balance=Decimal("5000.00")),
        ]
        for wallet in wallets:
            test_session.add(wallet)
        test_session.commit()
        
        response = test_client.get(f"/wallets/{user_id}/balances")
        
        assert response.status_code == 200
        data = response.json()
        assert "balances" in data
        assert data["balances"]["USD"] == "1000.00"
        assert data["balances"]["MXN"] == "5000.00"
    
    def test_get_balances_empty(self, test_client, test_user):
        """Test getting balances for user with no wallets."""
        user_id = str(test_user.id)
        response = test_client.get(f"/wallets/{user_id}/balances")
        
        assert response.status_code == 200
        data = response.json()
        assert data["balances"] == {}


class TestGetTransactions:
    """Tests for GET /wallets/{user_id}/transactions endpoint."""
    
    def test_get_transactions_success(self, test_client, test_session, test_user):
        """Test getting transaction history."""
        user_id = str(test_user.id)
        # Create transactions
        transactions = [
            Transaction(
                user_id=test_user.id,
                transaction_type="fund",
                currency="USD",
                amount=Decimal("1000.00")
            ),
            Transaction(
                user_id=test_user.id,
                transaction_type="withdraw",
                currency="USD",
                amount=Decimal("200.00")
            ),
        ]
        for transaction in transactions:
            test_session.add(transaction)
        test_session.commit()
        
        response = test_client.get(f"/wallets/{user_id}/transactions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert len(data["transactions"]) == 2
        assert data["total"] == 2
    
    def test_get_transactions_with_limit(self, test_client, test_session, test_users):
        """Test getting transactions with limit."""
        user = test_users[0]  # Use user with id=1
        user_id = str(user.id)
        # Create multiple transactions
        for i in range(5):
            transaction = Transaction(
                user_id=user.id,
                transaction_type="fund",
                currency="USD",
                amount=Decimal(f"{100 * (i + 1)}.00")
            )
            test_session.add(transaction)
        test_session.commit()
        
        response = test_client.get(f"/wallets/{user_id}/transactions?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 3
    
    def test_get_transactions_empty(self, test_client, test_user):
        """Test getting transactions for user with no transactions."""
        user_id = str(test_user.id)
        response = test_client.get(f"/wallets/{user_id}/transactions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total"] == 0

