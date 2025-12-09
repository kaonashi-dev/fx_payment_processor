"""End-to-end tests for complete wallet workflows."""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from src.main import app
from src.database.engine import get_session
from src.models.currency import Currency
from src.models import User
import src.services.wallet_service as wallet_service_module
import src.api.dependencies as dependencies_module


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(test_engine):
    """Create test client with test database."""

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


@pytest.fixture(name="test_user")
def test_user_fixture(test_session):
    """Create a test user."""
    user = User(email="e2e@example.com", name="E2E Test User")
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(name="test_users")
def test_users_fixture(test_session):
    """Create multiple test users."""
    users = [
        User(email=f"e2e{i}@example.com", name=f"E2E User {i}")
        for i in range(1, 4)
    ]
    for user in users:
        test_session.add(user)
    test_session.commit()
    for user in users:
        test_session.refresh(user)
    return users


def test_complete_user_journey(client, test_user):
    """Test complete user journey: fund -> convert -> withdraw.

    Scenario:
    1. User funds USD wallet with $1000
    2. User converts $500 USD to MXN
    3. User withdraws $200 USD
    4. User withdraws 1000 MXN
    5. Verify final balances
    6. Verify transaction history
    """
    user_id = str(test_user.id)

    # Step 1: Fund USD wallet with $1000
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "1000.00"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["currency"] == "USD"
    assert Decimal(data["new_balance"]) == Decimal("1000.00")

    # Step 2: Convert $500 USD to MXN
    response = client.post(
        f"/wallets/{user_id}/convert",
        json={
            "from_currency": "USD",
            "to_currency": "MXN",
            "amount": "500.00",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["from_currency"] == "USD"
    assert data["to_currency"] == "MXN"
    assert Decimal(data["from_amount"]) == Decimal("500.00")
    # With default rate of 18.70, should get 9350 MXN
    expected_mxn = Decimal("500.00") * Decimal("18.70")
    assert Decimal(data["to_amount"]) == expected_mxn

    # Step 3: Withdraw $200 USD
    response = client.post(
        f"/wallets/{user_id}/withdraw",
        json={"currency": "USD", "amount": "200.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["new_balance"]) == Decimal("300.00")  # 1000 - 500 - 200

    # Step 4: Withdraw 1000 MXN
    response = client.post(
        f"/wallets/{user_id}/withdraw",
        json={"currency": "MXN", "amount": "1000.00"},
    )
    assert response.status_code == 200
    data = response.json()
    expected_mxn_balance = expected_mxn - Decimal("1000.00")
    assert Decimal(data["new_balance"]) == expected_mxn_balance

    # Step 5: Verify final balances
    response = client.get(f"/wallets/{user_id}/balances")
    assert response.status_code == 200
    balances = response.json()["balances"]
    assert Decimal(balances["USD"]) == Decimal("300.00")
    assert Decimal(balances["MXN"]) == expected_mxn_balance

    # Step 6: Verify transaction history
    response = client.get(f"/wallets/{user_id}/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["total"] == 4  # 1 fund + 1 convert + 2 withdrawals

    transactions = data["transactions"]
    # Transactions are ordered newest first
    assert transactions[0]["transaction_type"] == "withdraw"  # Last MXN withdrawal
    assert transactions[1]["transaction_type"] == "withdraw"  # USD withdrawal
    assert transactions[2]["transaction_type"] == "convert"
    assert transactions[3]["transaction_type"] == "fund"


def test_multi_currency_operations(client, test_users):
    """Test multiple operations across different currencies.

    Scenario:
    1. Fund USD and MXN separately
    2. Convert between currencies multiple times
    3. Verify balances are accurate
    """
    user_id = str(test_users[0].id)

    # Fund USD
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "1000.00"},
    )
    assert response.status_code == 201

    # Fund MXN
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "MXN", "amount": "5000.00"},
    )
    assert response.status_code == 201

    # Convert USD to MXN
    client.post(
        f"/wallets/{user_id}/convert",
        json={
            "from_currency": "USD",
            "to_currency": "MXN",
            "amount": "100.00",
        },
    )

    # Convert MXN to USD
    client.post(
        f"/wallets/{user_id}/convert",
        json={
            "from_currency": "MXN",
            "to_currency": "USD",
            "amount": "1000.00",
        },
    )

    # Verify balances
    response = client.get(f"/wallets/{user_id}/balances")
    balances = response.json()["balances"]

    # USD: 1000 - 100 (converted out) + 53.00 (converted in from 1000 MXN at rate 0.053)
    expected_usd = Decimal("1000.00") - Decimal("100.00") + (
        Decimal("1000.00") * Decimal("0.053")
    )
    assert Decimal(balances["USD"]) == expected_usd

    # MXN: 5000 + 1870 (from 100 USD at rate 18.70) - 1000 (converted out)
    expected_mxn = (
        Decimal("5000.00")
        + (Decimal("100.00") * Decimal("18.70"))
        - Decimal("1000.00")
    )
    assert Decimal(balances["MXN"]) == expected_mxn


def test_insufficient_balance_scenarios(client, test_users):
    """Test error handling for insufficient balance.

    Scenario:
    1. Try to withdraw from empty wallet
    2. Try to convert more than available
    3. Fund wallet and retry
    """
    user_id = str(test_users[1].id)

    # Try to withdraw from empty wallet
    response = client.post(
        f"/wallets/{user_id}/withdraw",
        json={"currency": "USD", "amount": "100.00"},
    )
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

    # Fund wallet with $50
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "50.00"},
    )
    assert response.status_code == 201

    # Try to convert $100 (more than available)
    response = client.post(
        f"/wallets/{user_id}/convert",
        json={
            "from_currency": "USD",
            "to_currency": "MXN",
            "amount": "100.00",
        },
    )
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

    # Fund more money
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "100.00"},
    )
    assert response.status_code == 201

    # Now conversion should work
    response = client.post(
        f"/wallets/{user_id}/convert",
        json={
            "from_currency": "USD",
            "to_currency": "MXN",
            "amount": "100.00",
        },
    )
    assert response.status_code == 200


def test_transaction_history_ordering(client, test_users):
    """Test that transaction history is ordered correctly (newest first)."""
    user_id = str(test_users[2].id)

    # Perform multiple operations
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "100.00"},
    )
    assert response.status_code == 201

    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "200.00"},
    )
    assert response.status_code == 201

    response = client.post(
        f"/wallets/{user_id}/withdraw",
        json={"currency": "USD", "amount": "50.00"},
    )
    assert response.status_code == 200

    # Get transaction history with limit
    response = client.get(f"/wallets/{user_id}/transactions?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 2
    assert data["total"] == 2

    # First transaction should be the withdrawal (newest)
    assert data["transactions"][0]["transaction_type"] == "withdraw"
    assert Decimal(data["transactions"][0]["amount"]) == Decimal("50.00")

    # Second should be the second fund
    assert data["transactions"][1]["transaction_type"] == "fund"
    assert Decimal(data["transactions"][1]["amount"]) == Decimal("200.00")


def test_invalid_currency_validation(client, test_user):
    """Test that invalid currencies are rejected."""
    user_id = str(test_user.id)

    # Try to fund with invalid currency
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "EUR", "amount": "100.00"},  # EUR not supported
    )
    assert response.status_code == 422  # Validation error


def test_zero_and_negative_amount_validation(client, test_user):
    """Test that zero and negative amounts are rejected."""
    user_id = str(test_user.id)

    # Try zero amount
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "0.00"},
    )
    assert response.status_code == 422

    # Try negative amount
    response = client.post(
        f"/wallets/{user_id}/fund",
        json={"currency": "USD", "amount": "-100.00"},
    )
    assert response.status_code == 422
