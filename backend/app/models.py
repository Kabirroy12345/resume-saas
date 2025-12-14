from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# ===============================
# USERS TABLE
# ===============================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)

    # Basic profile info
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)

    # Password (renamed from hashed_password)
    password = Column(String)

    # Profile Picture
    avatar_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    analyses = relationship("Analysis", back_populates="owner")


# ===============================
# ANALYSIS TABLE
# ===============================
class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_name = Column(String)
    job_title = Column(String)
    job_description = Column(Text)
    match_score = Column(Float)
    skill_score = Column(Float)
    semantic_score = Column(Float)
    missing_skills = Column(Text)
    bonus_skills = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="analyses")
