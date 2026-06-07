from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Session(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    emulator_serial: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    current_app: Optional[str] = None
    status: str = Field(default="ready", index=True)  # ready | busy | error

