from decimal import Decimal
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Numeric, UniqueConstraint
from typing import Optional
from .currency import Currency


class Wallet(SQLModel, table=True):
    
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="unique_user_currency"),
    )
    
    id: int = Field(primary_key=True)
    user_id: int = Field(index=True, description="User identifier")
    currency: Currency = Field(index=True, max_length=3, description="Currency code (USD, MXN)")
    balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=20, scale=2)),
        description="Current balance in this currency"
    )
    
    class Config:
        json_encoders = {
            Decimal: str
        }
    
    def __repr__(self) -> str:
        return f"Wallet(user_id={self.user_id}, currency={self.currency}, balance={self.balance})"

