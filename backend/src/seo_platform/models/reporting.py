from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Boolean,
    ForeignKey, Enum as SQLEnum, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum


class ReportType(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class CitationReport:
    """Stored report record."""

    __tablename__ = "citation_reports"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class CitationSnapshot:
    """Daily snapshot of citation counts for growth tracking."""

    __tablename__ = "citation_snapshots"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
