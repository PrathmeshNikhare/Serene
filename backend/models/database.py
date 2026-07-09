from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime
from backend.core.config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    persona = Column(String)
    age = Column(Integer, default=20)
    gender = Column(String, default="Female")
    wellness_points = Column(Integer, default=0)
    
    mood_logs = relationship("MoodLog", back_populates="user")
    insights_cache = relationship("AIInsightsCache", back_populates="user")
    memories = relationship("AuraMemory", back_populates="user")
    nudge_feedbacks = relationship("UserNudgeFeedback", back_populates="user")

class MoodLog(Base):
    __tablename__ = "mood_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False) # Mood score (1-10)
    sleep_hours = Column(Float, default=0.0)
    screen_time_hours = Column(Float, default=0.0)
    work_study_hours = Column(Float, default=0.0)
    stressors = Column(JSONB, default=list) # List of checked checkbox stressors
    predicted_stress_score = Column(Float, default=0.0) # XGBoost stress score output
    top_drivers = Column(JSONB, default=dict) # SHAP drivers output
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="mood_logs")

class AIInsightsCache(Base):
    __tablename__ = "ai_insights_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    raw_json_payload = Column(JSONB)
    
    user = relationship("User", back_populates="insights_cache")

class AuraMemory(Base):
    __tablename__ = "aura_memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Vector(1024))
    metadata_json = Column(JSONB)
    
    user = relationship("User", back_populates="memories")

class UserNudgeFeedback(Base):
    __tablename__ = "user_nudge_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    nudge_type = Column(String)
    nudge_text = Column(String)
    feedback_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="nudge_feedbacks")
