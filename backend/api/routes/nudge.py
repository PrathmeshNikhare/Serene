from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from backend.models.database import get_db, User, MoodLog
from backend.api.ml.rlhf_nudge import check_and_serve_nudge, log_human_feedback

router = APIRouter()

class NudgeFeedbackRequest(BaseModel):
    nudge_type: str
    nudge_text: str
    accepted: bool

@router.get("/{user_id}")
def get_daily_nudge(user_id: uuid.UUID, db: Session = Depends(get_db)):
    # 1. Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    # 2. Get latest mood log for current stress score
    latest_mood = db.query(MoodLog).filter(MoodLog.user_id == user_id).order_by(MoodLog.logged_at.desc()).first()
    current_stress_score = latest_mood.predicted_stress_score if latest_mood else 0.5

    # 3. Check and serve nudge
    try:
        nudge_payload = check_and_serve_nudge(
            db=db,
            user_id=str(user_id),
            user_persona=user.persona or "General user",
            current_stress_score=current_stress_score
        )
        return {"status": "success", "data": nudge_payload}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate nudge: {str(e)}"
        )

@router.post("/{user_id}/feedback")
def submit_nudge_feedback(user_id: uuid.UUID, feedback: NudgeFeedbackRequest, db: Session = Depends(get_db)):
    # 1. Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
        
    # 2. Log human feedback
    try:
        log_human_feedback(
            db=db,
            user_id=str(user_id),
            nudge_type=feedback.nudge_type,
            nudge_text=feedback.nudge_text,
            accepted=feedback.accepted
        )
        return {"status": "success", "message": "Feedback logged successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log feedback: {str(e)}"
        )
