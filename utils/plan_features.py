def get_plan_features(plan: str) -> dict:
    """
    Returns enabled features and limits for a given plan.
    Plan must be one of: "essential", "prestige", "elite".
    """
    features = {
        "essential": {
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
        },
        "prestige": {
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
        },
        "elite": {
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
        }
    }

    return features.get(plan.lower(), features["essential"])
