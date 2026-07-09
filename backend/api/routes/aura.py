from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from backend.models.database import get_db, User
from backend.api.ml.aura_agent import get_aura_response

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: uuid.UUID
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
def chat_with_aura(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Verify user exists
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {payload.user_id} not found."
        )
    
    # 1.5 Fetch latest Phase 2 Insights for the user
    from backend.models.database import AIInsightsCache
    latest_insights = db.query(AIInsightsCache).filter(AIInsightsCache.user_id == payload.user_id).order_by(AIInsightsCache.date.desc()).first()
    phase_2_insights = latest_insights.raw_json_payload if latest_insights else {}

    # 2. Get Aura response (and queue memory saving in the background)
    try:
        response_text = get_aura_response(
            user_id=str(payload.user_id),
            user_persona=user.persona or "Teenager",
            user_age=user.age or 20,
            user_gender=user.gender or "Female",
            message=payload.message,
            background_tasks=background_tasks,
            phase_2_insights=phase_2_insights
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aura agent failed to generate a response: {str(e)}")

