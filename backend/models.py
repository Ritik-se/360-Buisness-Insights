from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    session_token = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    category = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    status = Column(String, default="uploaded")
    stored_path = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    profile_json = Column(Text, nullable=True)
    mapping_json = Column(Text, nullable=True)
    kpi_json = Column(Text, nullable=True)
    source_dataset_id = Column(Integer, nullable=True)  # set when this row is a cleaned copy of another dataset
