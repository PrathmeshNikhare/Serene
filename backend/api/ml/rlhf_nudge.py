import logging
import random
from datetime import datetime
from huggingface_hub import InferenceClient
from sqlalchemy.orm import Session
from backend.models.database import UserNudgeFeedback
from backend.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

client = InferenceClient(
    model="microsoft/phi-4",
    token=settings.HUGGINGFACEHUB_API_TOKEN,
    timeout=120.0
)

# The possible therapeutic interventions Serene can offer
NUDGE_CATEGORIES = [
    "breathing_exercise", 
    "physical_movement", 
    "cognitive_reframing", 
    "digital_detox"
]

# ==========================================
# 2. REINFORCEMENT LEARNING ALGORITHM
# ==========================================
def calculate_user_preferences(db: Session, user_id: str) -> dict:
    """
    Analyzes historical human feedback (+1/-1) to calculate a reward score 
    for each nudge category from the database.
    """
    # Start everyone at a baseline of 0 (Neutral)
    preferences = {category: 0 for category in NUDGE_CATEGORIES}
    
    # Calculate historical rewards from the DB
    feedbacks = db.query(UserNudgeFeedback).filter(UserNudgeFeedback.user_id == user_id).all()
    
    for record in feedbacks:
        if record.nudge_type in preferences:
            preferences[record.nudge_type] += record.feedback_score
            
    logger.info(f"Calculated RLHF Preference Weights for {user_id}: {preferences}")
    return preferences

def select_optimal_nudge_type(preferences: dict, exploration_rate: float = 0.2) -> str:
    """
    Uses an Epsilon-Greedy Bandit approach to pick the next nudge.
    80% of the time: Exploit (Pick the category the user likes most).
    20% of the time: Explore (Pick a random category to see if their taste changed).
    """
    # Exploration: Roll the dice to try something new
    if random.random() < exploration_rate:
        chosen = random.choice(list(preferences.keys()))
        logger.info(f"RLHF Strategy: EXPLORE -> Selected '{chosen}'")
        return chosen
        
    # Exploitation: Pick the highest scoring category
    # If multiple have the same high score, pick randomly among them
    max_score = max(preferences.values())
    best_categories = [cat for cat, score in preferences.items() if score == max_score]
    
    chosen = random.choice(best_categories)
    logger.info(f"RLHF Strategy: EXPLOIT -> Selected '{chosen}' (Score: {max_score})")
    return chosen

# ==========================================
# 2.5 GLOBAL SYSTEM EXPORT
# ==========================================
def get_global_system_prompt_rules(db: Session, user_id: str) -> dict:
    """
    Translates the mathematical RLHF weights into plain-English rules 
    that can be injected into Component 2 (LangGraph) and Component 3 (Aura).
    """
    preferences = calculate_user_preferences(db, user_id)
    
    # Sort categories by score
    sorted_prefs = sorted(preferences.items(), key=lambda item: item[1], reverse=True)
    
    # Top preference (> 0)
    loved = [cat for cat, score in sorted_prefs if score > 0]
    # Bottom preference (< 0)
    hated = [cat for cat, score in sorted_prefs if score < 0]
    
    return {
        "preferred_interventions": loved if loved else ["general_mindfulness"],
        "avoid_interventions": hated if hated else ["none"]
    }

# ==========================================
# 3. LLM NUDGE GENERATOR
# ==========================================
def generate_nudge_text(user_persona: str, current_stress_score: float, selected_category: str) -> str:
    """
    Passes the selected RLHF category and current ML stress score to the Hugging Face model
    to generate a highly personalized, contextual micro-therapy.
    """
    logger.info("Generating personalized nudge via Hugging Face Cloud...")
    
    # Adjust tone based on the ML stress score (from Component 1)
    urgency = "gentle and preventative" if current_stress_score < 0.6 else "immediate, calming, and grounding"
    
    system_prompt = f"""You are the proactive wellness engine for the Serene app.
Your job is to generate a 'Smart Nudge'—a short, actionable push notification.

[CONTEXT]
User Persona: {user_persona}
Current Stress Score: {current_stress_score} (Scale 0-1)
Required Tone: {urgency}
Intervention Category: {selected_category}

[INSTRUCTIONS]
1. Write EXACTLY ONE concise sentence.
2. It must be an actionable micro-step based on the Intervention Category.
3. Keep it under 20 words so it fits beautifully in a web dashboard modal or banner.
4. Do NOT use hashtags, emojis, or pleasantries.
"""

    try:
        response = client.chat_completion(
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': "Generate my nudge for right now."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate nudge via Cloud LLM: {e}")
        return "Take a deep breath and relax your shoulders." # Safe fallback

# ==========================================
# 4. CAPTURE HUMAN FEEDBACK
# ==========================================
def log_human_feedback(db: Session, user_id: str, nudge_type: str, nudge_text: str, accepted: bool):
    """
    Captures the user's action (clicking 'Start' vs 'Dismiss') 
    and writes it back to the database to train the system for tomorrow.
    """
    reward_score = 1 if accepted else -1
    
    new_record = UserNudgeFeedback(
        user_id=user_id,
        nudge_type=nudge_type,
        nudge_text=nudge_text,
        feedback_score=reward_score,
        created_at=datetime.utcnow()
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    action = "ACCEPTED (+1)" if accepted else "REJECTED (-1)"
    logger.info(f"Feedback Logged: User {action} the '{nudge_type}' nudge.")

# ==========================================
# 4.5 WEB-FIRST DELIVERY (LOGIN CHECK)
# ==========================================
def check_and_serve_nudge(db: Session, user_id: str, user_persona: str, current_stress_score: float) -> dict:
    """
    Checks the timestamp to ensure only one nudge is served per day.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check if user already interacted with a nudge today
    already_nudged_today = db.query(UserNudgeFeedback).filter(
        UserNudgeFeedback.user_id == user_id,
        UserNudgeFeedback.created_at >= today_start
    ).first()
    
    if already_nudged_today:
        logger.info("Login Check: User already received their daily nudge. Skipping.")
        return None
        
    logger.info("Login Check: No nudge found for today. Generating new modal content...")
    
    # Step 1: Read the user's historical preferences
    user_weights = calculate_user_preferences(db, user_id)
    
    # Step 2: Pick the best category
    best_category = select_optimal_nudge_type(user_weights, exploration_rate=0.2)
    
    # Step 3: Generate the actual notification text
    nudge_text = generate_nudge_text(
        user_persona=user_persona, 
        current_stress_score=current_stress_score, 
        selected_category=best_category
    )
    
    return {
        "category": best_category,
        "text": nudge_text,
        "timestamp": datetime.utcnow().isoformat()
    }
