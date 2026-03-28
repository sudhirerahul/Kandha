# SQLAlchemy ORM models for cloud bill analysis sessions and spend reports
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AnalysisSession(Base):
    """Tracks a user's cloud bill upload and analysis lifecycle."""

    __tablename__ = "analysis_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_key: Mapped[str] = mapped_column(String, nullable=False)  # MinIO object key
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    spend_report: Mapped["SpendReport | None"] = relationship(
        "SpendReport", back_populates="session", uselist=False
    )


class SpendReport(Base):
    """Stores the structured output of a completed analysis: breakdown + AI recommendations."""

    __tablename__ = "spend_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), unique=True
    )
    raw_spend: Mapped[dict] = mapped_column(JSONB, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_monthly_usd: Mapped[float] = mapped_column(nullable=False)
    savings_report: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    hardware_recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="spend_report")
