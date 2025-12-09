"""Unit tests for WalletService."""
import pytest
from decimal import Decimal
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.pool import StaticPool
from src.models import Wallet, Transaction, TransactionType
from src.models.currency import Currency
from src.services.wallet_service import WalletService
from src.services.fx_rates import fx_rate_service


class TestWalletServiceFund:
    """Tests for fund_wallet method."""
    
    def test_fund_wallet_new_wallet(self, test_db, mock_fx_rate_service):
        """Test funding a new wallet creates it."""
        with Session(test_db) as session:
            # Mock the engine to use test_db
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                result = WalletService.fund_wallet(
                    user_id="new_user",
                    currency=Currency.USD,
                    amount=Decimal("500.00")
                )

                assert result["user_id"] == "new_user"
                assert result["currency"] == Currency.USD
                assert result["amount"] == Decimal("500.00")
                assert result["new_balance"] == Decimal("500.00")

                # Verify wallet was created
                wallet = session.get(Wallet, 1)
                assert wallet is not None
                assert wallet.user_id == "new_user"
                assert wallet.currency == Currency.USD
                assert wallet.balance == Decimal("500.00")
                
                # Verify transaction was created
                transactions = session.exec(
                    select(Transaction).where(Transaction.user_id == "new_user")
                ).all()
                assert len(transactions) == 1
                assert transactions[0].transaction_type == TransactionType.FUND
            finally:
                ws.engine = original_engine
    
    def test_fund_wallet_existing_wallet(self, test_db, sample_wallet, mock_fx_rate_service):
        """Test funding an existing wallet adds to balance."""
        import src.services.wallet_service as ws
        original_engine = ws.engine
        ws.engine = test_db

        try:
            initial_balance = sample_wallet.balance
            fund_amount = Decimal("250.00")

            result = WalletService.fund_wallet(
                user_id=sample_wallet.user_id,
                currency=sample_wallet.currency,
                amount=fund_amount
            )

            assert result["new_balance"] == initial_balance + fund_amount

            # Verify wallet balance was updated in the database
            with Session(test_db) as session:
                updated_wallet = session.get(Wallet, sample_wallet.id)
                assert updated_wallet.balance == initial_balance + fund_amount
        finally:
            ws.engine = original_engine
    
    def test_fund_wallet_multiple_currencies(self, test_db, mock_fx_rate_service):
        """Test funding wallet with different currencies."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db

            try:
                user_id = "multi_currency_user"

                # Fund USD
                result_usd = WalletService.fund_wallet(user_id, Currency.USD, Decimal("1000.00"))
                assert result_usd["currency"] == Currency.USD
                assert result_usd["new_balance"] == Decimal("1000.00")

                # Fund MXN
                result_mxn = WalletService.fund_wallet(user_id, Currency.MXN, Decimal("5000.00"))
                assert result_mxn["currency"] == Currency.MXN
                assert result_mxn["new_balance"] == Decimal("5000.00")

                # Verify both wallets exist
                wallets = session.exec(
                    select(Wallet).where(Wallet.user_id == user_id)
                ).all()
                assert len(wallets) == 2
            finally:
                ws.engine = original_engine


class TestWalletServiceConvert:
    """Tests for convert_currency method."""
    
    def test_convert_usd_to_mxn_success(self, test_db, mock_fx_rate_service):
        """Test successful USD to MXN conversion."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "convert_user"
                # Create USD wallet with balance
                usd_wallet = Wallet(user_id=user_id, currency=Currency.USD, balance=Decimal("1000.00"))
                session.add(usd_wallet)
                session.commit()

                result = WalletService.convert_currency(
                    user_id=user_id,
                    from_currency=Currency.USD,
                    to_currency=Currency.MXN,
                    amount=Decimal("100.00")
                )

                assert result["from_currency"] == Currency.USD
                assert result["to_currency"] == Currency.MXN
                assert result["from_amount"] == Decimal("100.00")
                assert result["to_amount"] == Decimal("1870.00")  # 100 * 18.70
                assert result["fx_rate"] == Decimal("18.70")
                
                # Verify balances
                session.refresh(usd_wallet)
                assert usd_wallet.balance == Decimal("900.00")  # 1000 - 100
                
                mxn_wallet = session.exec(
                    select(Wallet).where(
                        Wallet.user_id == user_id,
                        Wallet.currency == Currency.MXN
                    )
                ).first()
                assert mxn_wallet is not None
                assert mxn_wallet.balance == Decimal("1870.00")
            finally:
                ws.engine = original_engine
    
    def test_convert_mxn_to_usd_success(self, test_db, mock_fx_rate_service):
        """Test successful MXN to USD conversion."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "convert_user_mxn"
                # Create MXN wallet with balance
                mxn_wallet = Wallet(user_id=user_id, currency=Currency.MXN, balance=Decimal("1870.00"))
                session.add(mxn_wallet)
                session.commit()

                result = WalletService.convert_currency(
                    user_id=user_id,
                    from_currency=Currency.MXN,
                    to_currency=Currency.USD,
                    amount=Decimal("1870.00")
                )

                assert result["from_currency"] == Currency.MXN
                assert result["to_currency"] == Currency.USD
                assert result["from_amount"] == Decimal("1870.00")
                # 1870 * 0.053 = 99.11 (rounded)
                assert result["to_amount"] == Decimal("99.11")
                assert result["fx_rate"] == Decimal("0.053")
            finally:
                ws.engine = original_engine
    
    def test_convert_insufficient_balance(self, test_db, mock_fx_rate_service):
        """Test conversion fails with insufficient balance."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "insufficient_user"
                # Create USD wallet with low balance
                usd_wallet = Wallet(user_id=user_id, currency=Currency.USD, balance=Decimal("50.00"))
                session.add(usd_wallet)
                session.commit()

                with pytest.raises(ValueError, match="Insufficient balance"):
                    WalletService.convert_currency(
                        user_id=user_id,
                        from_currency=Currency.USD,
                        to_currency=Currency.MXN,
                        amount=Decimal("100.00")
                    )
            finally:
                ws.engine = original_engine
    
    def test_convert_same_currency_error(self, test_db, mock_fx_rate_service):
        """Test conversion fails when currencies are the same."""
        with pytest.raises(ValueError, match="Cannot convert currency to itself"):
            WalletService.convert_currency(
                user_id="test_user",
                from_currency=Currency.USD,
                to_currency=Currency.USD,
                amount=Decimal("100.00")
            )
    
    # Note: Test for unsupported currency pairs is handled by Pydantic validation at the API level
    # The service layer only accepts Currency enum which only has USD and MXN


class TestWalletServiceWithdraw:
    """Tests for withdraw_funds method."""
    
    def test_withdraw_success(self, test_db, sample_wallet, mock_fx_rate_service):
        """Test successful withdrawal."""
        import src.services.wallet_service as ws
        original_engine = ws.engine
        ws.engine = test_db

        try:
            initial_balance = sample_wallet.balance
            withdraw_amount = Decimal("300.00")

            result = WalletService.withdraw_funds(
                user_id=sample_wallet.user_id,
                currency=sample_wallet.currency,
                amount=withdraw_amount
            )

            assert result["currency"] == sample_wallet.currency
            assert result["amount"] == withdraw_amount
            assert result["new_balance"] == initial_balance - withdraw_amount

            # Verify wallet balance was updated
            with Session(test_db) as session:
                updated_wallet = session.get(Wallet, sample_wallet.id)
                assert updated_wallet.balance == initial_balance - withdraw_amount

                # Verify transaction was created
                transactions = session.exec(
                    select(Transaction).where(
                        Transaction.user_id == sample_wallet.user_id,
                        Transaction.transaction_type == TransactionType.WITHDRAW
                    )
                ).all()
                assert len(transactions) == 1
        finally:
            ws.engine = original_engine
    
    def test_withdraw_insufficient_balance(self, test_db, sample_wallet, mock_fx_rate_service):
        """Test withdrawal fails with insufficient balance."""
        import src.services.wallet_service as ws
        original_engine = ws.engine
        ws.engine = test_db

        try:
            withdraw_amount = Decimal("2000.00")  # More than balance

            with pytest.raises(ValueError, match="Insufficient balance"):
                WalletService.withdraw_funds(
                    user_id=sample_wallet.user_id,
                    currency=sample_wallet.currency,
                    amount=withdraw_amount
                )

            # Verify balance was not changed
            with Session(test_db) as session:
                updated_wallet = session.get(Wallet, sample_wallet.id)
                assert updated_wallet.balance == Decimal("1000.00")
        finally:
            ws.engine = original_engine
    
    def test_withdraw_exact_balance(self, test_db, sample_wallet, mock_fx_rate_service):
        """Test withdrawal of exact balance."""
        import src.services.wallet_service as ws
        original_engine = ws.engine
        ws.engine = test_db

        try:
            exact_amount = sample_wallet.balance

            result = WalletService.withdraw_funds(
                user_id=sample_wallet.user_id,
                currency=sample_wallet.currency,
                amount=exact_amount
            )

            assert result["new_balance"] == Decimal("0.00")

            with Session(test_db) as session:
                updated_wallet = session.get(Wallet, sample_wallet.id)
                assert updated_wallet.balance == Decimal("0.00")
        finally:
            ws.engine = original_engine


class TestWalletServiceGetBalances:
    """Tests for get_balances method."""
    
    def test_get_balances_multiple_currencies(self, test_db, sample_wallets, mock_fx_rate_service):
        """Test getting balances for user with multiple currencies."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                balances = WalletService.get_balances("test_user_001")
                
                assert "USD" in balances
                assert "MXN" in balances
                assert balances["USD"] == Decimal("1000.00")
                assert balances["MXN"] == Decimal("5000.00")
            finally:
                ws.engine = original_engine
    
    def test_get_balances_empty(self, test_db, mock_fx_rate_service):
        """Test getting balances for user with no wallets."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                balances = WalletService.get_balances("non_existent_user")
                assert balances == {}
            finally:
                ws.engine = original_engine


class TestWalletServiceGetTransactions:
    """Tests for get_transactions method."""
    
    def test_get_transactions_with_limit(self, test_db, mock_fx_rate_service):
        """Test getting transactions with limit."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                user_id = "transactions_user"
                
                # Create multiple transactions
                for i in range(5):
                    transaction = Transaction(
                        user_id=user_id,
                        transaction_type=TransactionType.FUND,
                        currency=Currency.USD,
                        amount=Decimal(f"{100 * (i + 1)}.00")
                    )
                    session.add(transaction)
                session.commit()
                
                transactions = WalletService.get_transactions(user_id, limit=3)
                assert len(transactions) == 3
            finally:
                ws.engine = original_engine
    
    def test_get_transactions_empty(self, test_db, mock_fx_rate_service):
        """Test getting transactions for user with no transactions."""
        with Session(test_db) as session:
            import src.services.wallet_service as ws
            original_engine = ws.engine
            ws.engine = test_db
            
            try:
                transactions = WalletService.get_transactions("no_transactions_user")
                assert transactions == []
            finally:
                ws.engine = original_engine

