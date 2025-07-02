from typing import List, Dict

def scan_impulse_triggers(data: Dict) -> Dict:
    triggered_flags = []
    # I - Item Type (not essential)
    essentials = ["groceries", "rent", "utilities", "medicine", "food", "transport"]
    if data.get("item_name", "").lower() not in essentials:
        triggered_flags.append("I")
    # M - Mood
    if data.get("mood", "").lower() in ["sad", "anxious", "bored", "excited"]:
        triggered_flags.append("M")
    # P - Pattern
    if data.get("pattern_match", False):
        triggered_flags.append("P")
    # U - Urgency
    if data.get("urgency", False):
        triggered_flags.append("U")
    # L - Last Purchase
    if isinstance(data.get("last_purchase_days_ago"), int) and data["last_purchase_days_ago"] < 3:
        triggered_flags.append("L")
    # S - Situation
    if data.get("situation", "").lower() in ["celebration", "peer pressure", "boredom", "stress"]:
        triggered_flags.append("S")
    # E - Explanation
    vague_explanations = ["just felt like it", "i don’t know", "i don't know", "because i wanted to"]
    if data.get("explanation", "").strip().lower() in vague_explanations:
        triggered_flags.append("E")
    total_triggers = len(triggered_flags)
    is_impulsive = total_triggers >= 4
    return {
        "total_triggers": total_triggers,
        "is_impulsive": is_impulsive,
        "triggered_flags": triggered_flags
    }
