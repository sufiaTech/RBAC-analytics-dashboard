from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="viewer")  # admin, manager, viewer
    department = Column(String, nullable=True)  # Applicable for manager/viewer

    audit_logs = relationship("AuditLog", back_populates="user")

class DataRecord(Base):
    __tablename__ = "data_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    department = Column(String, index=True)
    metric_name = Column(String, index=True)
    value = Column(Float)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # LOGIN, EXPORT_CSV, ROLE_CHANGE, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, nullable=True)

    user = relationship("User", back_populates="audit_logs")
