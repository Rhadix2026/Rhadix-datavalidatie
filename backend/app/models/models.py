from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Text
from sqlalchemy.sql import func
from app.database import Base

class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id          = Column(Integer, primary_key=True, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    label       = Column(String(255), nullable=True)
    files       = Column(JSON)          # list of {name, schema_key, row_count}
    results     = Column(JSON)          # full results payload
    total_rows  = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warn_count  = Column(Integer, default=0)
    score       = Column(Float, default=100.0)
    status      = Column(String(32), default="completed")  # completed | failed
