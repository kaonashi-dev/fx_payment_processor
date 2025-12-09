"""Edge case tests for WalletService."""
import pytest
from decimal import Decimal
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.pool import StaticPool
from src.models import Wallet, Transaction, TransactionType
from src.models.currency import Currency
from src.services.wallet_service import WalletService


class TestEdgeCases:
    """Edge case tests for wallet operations."""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database in memory."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        yield engine
        SQLModel.metadata.drop_all(engine)
    
    @pytest.fixture
    def mock_fx_service(self, monkeypatch):
        """Mock FX rate service."""
        class MockFXRateService:
            @property
            def usd_to_mxn(self):
                return Decimal("18.70")
            
            @property
            def mxn_to_usd(self):
                return Decimal("0.053")
        
        mock_service = MockFXRateService()
        monkeypatch.setattr("src.services.wallet_service.fx_rate_service", mock_service)
        return mock_service
    
    # Note: Zero and negative amounts are validated at the API level via Pydantic
    # The service layer accepts Decimal amounts and trusts the caller has validated them
    
    def test_fund_wallet_very_large_amount(self, test_db, mock_fx_service):
        """Test funding with very large amount."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                large_amount = Decimal("999999999.99")
                result = WalletService.fund_wallet("user", Currency.USD, large_amount)
                assert result["new_balance"] == large_amount
            finally:
                ws.engine = original_engine
    
    def test_convert_precision(self, test_db, mock_fx_service):
        """Test currency conversion maintains precision."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "precision_user"
                wallet = Wallet(user_id=user_id, currency=Currency.USD, balance=Decimal("1000.00"))
                session.add(wallet)
                session.commit()
                
                # Convert small amount to test precision
                result = WalletService.convert_currency(
                    user_id=user_id,
                    from_currency=Currency.USD,
                    to_currency=Currency.MXN,
                    amount=Decimal("1.00")
                )
                
                # 1 USD * 18.70 = 18.70 MXN
                assert result["to_amount"] == Decimal("18.70")
                assert result["fx_rate"] == Decimal("18.70")
            finally:
                ws.engine = original_engine
    
    def test_multiple_operations_consistency(self, test_db, mock_fx_service):
        """Test multiple operations maintain consistency."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "consistency_user"
                
                # Fund USD
                WalletService.fund_wallet(user_id, Currency.USD, Decimal("1000.00"))
                
                # Convert USD to MXN
                WalletService.convert_currency(user_id, Currency.USD, Currency.MXN, Decimal("100.00"))
                
                # Withdraw MXN
                WalletService.withdraw_funds(user_id, Currency.MXN, Decimal("500.00"))
                
                # Check final balances
                balances = WalletService.get_balances(user_id)
                assert balances["USD"] == Decimal("900.00")  # 1000 - 100
                assert balances["MXN"] == Decimal("1370.00")  # 1870 - 500
            finally:
                ws.engine = original_engine
    
    def test_concurrent_operations_simulation(self, test_db, mock_fx_service):
        """Test simulating multiple operations to check balance consistency."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "concurrent_user"
                
                # Initial fund
                WalletService.fund_wallet(user_id, Currency.USD, Decimal("1000.00"))
                
                # Multiple operations
                for i in range(5):
                    WalletService.fund_wallet(user_id, Currency.USD, Decimal("100.00"))
                    WalletService.withdraw_funds(user_id, Currency.USD, Decimal("50.00"))
                
                # Final balance should be: 1000 + (5 * 100) - (5 * 50) = 1250
                balances = WalletService.get_balances(user_id)
                assert balances["USD"] == Decimal("1250.00")
            finally:
                ws.engine = original_engine
    
    def test_get_transactions_ordering(self, test_db, mock_fx_service):
        """Test transactions are returned in correct order (newest first)."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "ordering_user"
                
                # Create multiple transactions
                WalletService.fund_wallet(user_id, Currency.USD, Decimal("100.00"))
                WalletService.fund_wallet(user_id, Currency.USD, Decimal("200.00"))
                WalletService.fund_wallet(user_id, Currency.USD, Decimal("300.00"))
                
                transactions = WalletService.get_transactions(user_id)
                
                # Should be ordered by created_at desc (newest first)
                assert len(transactions) == 3
                # Last transaction should have highest amount (most recent)
                assert transactions[0].amount == Decimal("300.00")
            finally:
                ws.engine = original_engine

