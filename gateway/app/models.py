import enum

from sqlmodel import SQLModel, Field, Enum, Column
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy_json import mutable_json_type
from typing import Optional
from datetime import datetime


class Status(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class DeRequests(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    original_filename: str = Field(nullable=False)
    file_hash: str = Field(nullable=False)
    unique_filename: str = Field(unique=True, nullable=False)
    duplicate: bool = Field(default=False)
    file_url: str = Field(nullable=False)
    request_body: dict = Field(
        sa_column=Column(mutable_json_type(dbtype=JSONB, nested=True))
    )
    ocr_model: str = Field(default=None, nullable=True)
    raw_ocr: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    processed_ocr: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    llm_model: str = Field(default=None, nullable=True)
    de_prompt: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    raw_de: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    processed_de: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    ocr_status: Optional[Status] = Field(
        sa_column=Column(Enum(Status), nullable=False, default=Status.PENDING)
    )
    de_status: Optional[Status] = Field(
        sa_column=Column(Enum(Status), nullable=False, default=Status.PENDING)
    )
    num_or_retry: int = Field(default=0)
    status: Optional[Status] = Field(
        sa_column=Column(Enum(Status), nullable=False, default=Status.PENDING)
    )
    status_message: str = Field(sa_column=Column(TEXT, default=None, nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default=None, nullable=True)
