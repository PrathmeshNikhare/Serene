from fastapi import APIRouter, HTTPException, Depends
from backend.api.ml.insights_agent import generate_insights
from pydantic import BaseModel
from typing import Dict, Optional
import uuid
from sqlalchemy.orm import Session
from backend.models.database import get_db, AIInsightsCache
from backend.api.ml.rlhf_nudge import get_global_system_prompt_rules

router = APIRouter()

class InsightsPayload(BaseModel):
    user_id: Optional[uuid.UUID] = None
    predicted_stress_score: float
    top_mathematical_drivers: Dict[str, float]

@router.post("/")
def get_insights(payload: InsightsPayload, db: Session = Depends(get_db)):
    """
    Get deep clinical insights from the LangGraph agent 
    using the real XGBoost predicted stress score and SHAP drivers,
    and save them to the DB insights cache.
    """
    try:
        ml_payload = {
            "raw_metrics": {
                "predicted_stress_score": payload.predicted_stress_score,
                "top_mathematical_drivers": payload.top_mathematical_drivers
            }
        }
        
        rlhf_rules = {}
        if payload.user_id:
            rlhf_rules = get_global_system_prompt_rules(db, str(payload.user_id))
            
        insights = generate_insights(ml_payload, rlhf_rules=rlhf_rules)
        
        # Save to database if user_id is provided
        if payload.user_id:
            db_insights = AIInsightsCache(
                user_id=payload.user_id,
                raw_json_payload=insights
            )
            db.add(db_insights)
            db.commit()
            
        return {"status": "success", "data": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
