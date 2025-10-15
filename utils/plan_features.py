from sqlalchemy.orm import Session
from models import User

def sanitize_plan(plan: str) -> str:
    valid_plans = {"essential", "prestige", "elite"}
    if not isinstance(plan, str):
        return "essential"
    plan_lc = plan.lower()
    if plan_lc not in valid_plans:
        return "essential"
    return plan_lc

def get_user_plan(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.plan:
        return sanitize_plan(user.plan)
    return "essential"

def get_plan_features(plan: str) -> dict:
    """
    Returns enabled features and limits for a given plan.
    Plan must be one of: "essential", "prestige", "elite".
    Pricing: Essential $79/mo, Prestige $149/mo, Elite $299/mo.
    """
    features = {
        "essential": {
            "price": 79,
            "nudge_limit": 20,
            "report_frequency": "monthly",
            "deep_insights": False,
            "plaid_enabled": True,
            "budget_enforcement": False,
            "ai_tone": "basic",
            "custom_rules": True,
            "goal_based_nudging": False,
            "luxury_profiling": False,
            "human_fallback": False,
            "nudge_history": False,
            "voice_access": False,
            "elite_club": False,
            "fallback_responses": [
                "No impulse detected. All clear!",
                "You’re thinking things through — that’s smart.",
                "No red flags here. Carry on!"
            ]
        },
        "prestige": {
            "price": 149,
            "nudge_limit": 60,
            "report_frequency": "weekly",
            "deep_insights": False,
            "plaid_enabled": True,
            "budget_enforcement": True,
            "ai_tone": "smart",
            "custom_rules": True,
            "goal_based_nudging": True,
            "luxury_profiling": False,
            "human_fallback": False,
            "nudge_history": True,
            "voice_access": False,
            "elite_club": False,
            "fallback_responses": [
                "No impulse detected. All clear!",
                "You’re thinking things through — that’s smart.",
                "No red flags here. Carry on!",
                "Not sure? Add it to your wishlist and revisit later.",
                "If you’re unsure, consider saving this item to your wishlist for now."
            ]
        },
        "elite": {
            "price": 299,
            "nudge_limit": None,  # Unlimited
            "report_frequency": "weekly",
            "deep_insights": True,
            "plaid_enabled": True,
            "budget_enforcement": True,
            "ai_tone": "luxury",
            "custom_rules": True,
            "goal_based_nudging": True,
            "luxury_profiling": True,
            "human_fallback": True,
            "nudge_history": True,
            "voice_access": True,
            "elite_club": True,
            "fallback_responses": [
                "No impulse detected. All clear!",
                "You’re thinking things through — that’s smart.",
                "No red flags here. Carry on!",
                "Not sure? Add it to your wishlist and revisit later.",
                "If you’re unsure, consider saving this item to your wishlist for now."
            ]
        }
    }

    return features.get(plan.lower(), features["essential"])
