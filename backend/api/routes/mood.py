from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from backend.models.database import get_db, User, MoodLog
from backend.api.ml.stress_model import predict_stress, get_all_factors

router = APIRouter()

# Input schema
class MoodLogCreate(BaseModel):
    user_id: uuid.UUID
    score: int = Field(..., ge=1, le=10, description="Mood score on a scale of 1-10")
    sleep_hours: float = Field(..., ge=0.0, le=24.0)
    screen_time_hours: float = Field(..., ge=0.0, le=24.0)
    work_study_hours: float = Field(..., ge=0.0, le=24.0)
    stressors: List[str] = Field(default_list=[], description="Selected checkbox stressors/factors")

# Output schema
class MoodLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    score: int
    sleep_hours: float
    screen_time_hours: float
    work_study_hours: float
    stressors: List[str]
    predicted_stress_score: float
    top_drivers: Dict[str, float]
    logged_at: datetime

    class Config:
        from_attributes = True

@router.get("/factors", response_model=List[str])
def get_supported_factors():
    """Get all checkbox binarizer factors supported by the ML model."""
    try:
        return get_all_factors()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch factors: {str(e)}"
        )

@router.post("/", response_model=MoodLogResponse, status_code=status.HTTP_201_CREATED)
def log_mood(mood_in: MoodLogCreate, db: Session = Depends(get_db)):
    # 1. Fetch user from DB to get demographics
    user = db.query(User).filter(User.id == mood_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {mood_in.user_id} not found."
        )

    # Validate that selected stressors are valid model classes
    valid_factors = get_all_factors()
    invalid_factors = [f for f in mood_in.stressors if f not in valid_factors]
    if invalid_factors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stressors: {invalid_factors}. Supported options are: {valid_factors}"
        )

    # 2. Run XGBoost ML Prediction & SHAP Analysis
    try:
        predicted_score, top_drivers = predict_stress(
            age=user.age,
            gender=user.gender,
            persona=user.persona,
            sleep_avg_hours=mood_in.sleep_hours,
            screen_time_hours=mood_in.screen_time_hours,
            work_study_hours=mood_in.work_study_hours,
            wellness_points=user.wellness_points,
            factors=mood_in.stressors
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Machine Learning model prediction failed: {str(e)}"
        )

    # 3. Create mood log entry
    db_mood_log = MoodLog(
        user_id=mood_in.user_id,
        score=mood_in.score,
        sleep_hours=mood_in.sleep_hours,
        screen_time_hours=mood_in.screen_time_hours,
        work_study_hours=mood_in.work_study_hours,
        stressors=mood_in.stressors,
        predicted_stress_score=predicted_score,
        top_drivers=top_drivers
    )
    
    # 4. Increment user wellness points for checking in (+10 points)
    user.wellness_points += 10
    
    db.add(db_mood_log)
    db.commit()
    db.refresh(db_mood_log)
    
    return db_mood_log

@router.get("/{user_id}", response_model=List[MoodLogResponse])
def get_mood_logs(user_id: uuid.UUID, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
        
    logs = db.query(MoodLog).filter(MoodLog.user_id == user_id).order_by(MoodLog.logged_at.desc()).all()
    return logs
