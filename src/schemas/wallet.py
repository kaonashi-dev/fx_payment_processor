from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from src.models.currency import Currency
from src.models.transaction import TransactionType


class FundRequest(BaseModel):
    currency: Currency = Field(..., description="Currency code (USD, MXN)")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Amount to fund")


class FundResponse(BaseModel):
    user_id: str
    currency: Currency
    amount: Decimal
    new_balance: Decimal
    message: str = "Wallet funded successfully"


class ConvertRequest(BaseModel):
    from_currency: Currency = Field(..., description="Source currency code")
    to_currency: Currency = Field(..., description="Target currency code")
    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Amount to convert"
    )


class ConvertResponse(BaseModel):
    user_id: str
    from_currency: Currency
    to_currency: Currency
    from_amount: Decimal
    to_amount: Decimal
    fx_rate: Decimal
    message: str = "Currency converted successfully"


class WithdrawRequest(BaseModel):
    currency: Currency = Field(..., description="Currency code")
    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Amount to withdraw"
    )


class WithdrawResponse(BaseModel):
    user_id: str
    currency: Currency
    amount: Decimal
    new_balance: Decimal
    message: str = "Funds withdrawn successfully"


class BalancesResponse(BaseModel):
    balances: dict[str, Decimal] = Field(..., description="Balances by currency")


class TransactionResponse(BaseModel):
    id: int
    user_id: str
    transaction_type: TransactionType
    currency: Optional[Currency] = None
    amount: Optional[Decimal] = None
    from_currency: Optional[Currency] = None
    to_currency: Optional[Currency] = None
    from_amount: Optional[Decimal] = None
    to_amount: Optional[Decimal] = None
    fx_rate: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class TransactionListResponse(BaseModel):
    user_id: str
    transactions: list[TransactionResponse]
    total: int
