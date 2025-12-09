"""Pytest configuration and fixtures."""
import pytest
from decimal import Decimal
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from src.models import Wallet, Transaction
from src.services.fx_rates import FXRateService


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
def sample_wallet(session):
    """Create a sample wallet for testing."""
    wallet = Wallet(
        user_id="test_user_001",
        currency="USD",
        balance=Decimal("1000.00")
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


@pytest.fixture(scope="function")
def sample_wallets(session):
    """Create multiple sample wallets for testing."""
    wallets = [
        Wallet(user_id="test_user_001", currency="USD", balance=Decimal("1000.00")),
        Wallet(user_id="test_user_001", currency="MXN", balance=Decimal("5000.00")),
        Wallet(user_id="test_user_002", currency="USD", balance=Decimal("500.00")),
    ]
    for wallet in wallets:
        session.add(wallet)
    session.commit()
    for wallet in wallets:
        session.refresh(wallet)
    return wallets


@pytest.fixture(scope="function")
def mock_fx_rate_service(monkeypatch):
    """Mock FX rate service for testing."""
    class MockFXRateService:
        def __init__(self):
            self._usd_to_mxn = 18.70
            self._mxn_to_usd = 0.053
        
        @property
        def usd_to_mxn(self):
            return Decimal(str(self._usd_to_mxn))
        
        @property
        def mxn_to_usd(self):
            return Decimal(str(self._mxn_to_usd))
    
    mock_service = MockFXRateService()
    monkeypatch.setattr("src.services.wallet_service.fx_rate_service", mock_service)
    return mock_service

