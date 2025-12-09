from datetime import datetime
from sqlmodel import SQLModel, Field, Column, DateTime
from sqlalchemy.sql import func
from typing import Optional


class User(SQLModel, table=True):
    
    id: int = Field(primary_key=True, description="User identifier")
    email: str = Field(max_length=255, description="User email address")
    name: str = Field(max_length=255, description="User full name")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now()),
        description="User creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="User last update timestamp"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, name={self.name})"

