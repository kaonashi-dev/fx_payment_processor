"""Transaction model for tracking all wallet operations."""
from decimal import Decimal
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Column, DateTime
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from typing import Optional
from .currency import Currency


class TransactionType(str, Enum):
    FUND = "fund"
    CONVERT = "convert"
    WITHDRAW = "withdraw"


class Transaction(SQLModel, table=True):
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="User identifier")
    transaction_type: TransactionType = Field(
        index=True,
        description="Type of transaction: fund, convert, or withdraw"
    )

    # For fund and withdraw operations
    currency: Optional[Currency] = Field(default=None, max_length=3, description="Currency code")
    amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=2), nullable=True),
        description="Transaction amount"
    )

    # For convert operations
    from_currency: Optional[Currency] = Field(
        default=None,
        max_length=3,
        description="Source currency for conversion"
    )
    to_currency: Optional[Currency] = Field(
        default=None,
        max_length=3,
        description="Target currency for conversion"
    )
    from_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=2), nullable=True),
        description="Amount in source currency"
    )
    to_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=2), nullable=True),
        description="Amount in target currency"
    )
    fx_rate: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=20, scale=4), nullable=True),
        description="Exchange rate used for conversion"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now()),
        description="Transaction timestamp"
    )
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    
    def __repr__(self) -> str:
        if self.transaction_type == TransactionType.CONVERT:
            return (
                f"Transaction(type={self.transaction_type}, "
                f"user_id={self.user_id}, "
                f"{self.from_currency} {self.from_amount} -> "
                f"{self.to_currency} {self.to_amount}, "
                f"rate={self.fx_rate})"
            )
        return (
            f"Transaction(type={self.transaction_type}, "
            f"user_id={self.user_id}, "
            f"currency={self.currency}, "
            f"amount={self.amount})"
        )

