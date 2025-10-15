from typing import List, Dict
import re
import string

def _normalize(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(rf"[{re.escape(string.punctuation)}]", "", text)
    return text

def scan_impulse_triggers(data: Dict) -> Dict:
    triggered_flags = []
    debug = {}
    # Normalize all fields
    item = _normalize(data.get("item_name", ""))
    mood = _normalize(data.get("mood", ""))
    pattern = data.get("pattern", False)
    urgency = data.get("urgency", False)
    last_days = data.get("last_purchase_days", None)
    situation = _normalize(data.get("situation", ""))
    explanation = _normalize(data.get("explanation", ""))

    # I - Item Type
    essentials = ["groceries", "rent", "utilities", "medicine", "food", "transport", "bill", "gas", "water", "electric", "insurance"]
    luxury_keywords = ["sneaker", "designer", "gucci", "louis", "limited", "edition", "luxury", "bag", "watch", "jacket", "premium", "iphone", "macbook", "vacation", "trip", "sale", "exclusive", "collectible"]
    i_flag = False
    i_matches = [kw for kw in luxury_keywords if kw in item]
    if item and not any(e in item for e in essentials) and i_matches:
        i_flag = True
        triggered_flags.append("I")
    debug['I'] = f"[DEBUG] I: input = {item}, matched = {i_matches}, triggered = {i_flag}"

    # M - Mood
    mood_keywords = ["sad", "anxious", "bored", "excited", "stressed", "angry", "lonely", "depressed", "fomo", "fear", "impulsive", "restless", "overwhelmed", "tired", "burned out"]
    m_matches = [kw for kw in mood_keywords if kw in mood]
    m_flag = bool(m_matches)
    if m_flag:
        triggered_flags.append("M")
    debug['M'] = f"[DEBUG] M: input = {mood}, matched = {m_matches}, triggered = {m_flag}"

    # P - Pattern
    p_flag = bool(pattern)
    p_matches = ["pattern_true"] if p_flag else []
    if p_flag:
        triggered_flags.append("P")
    debug['P'] = f"[DEBUG] P: input = {pattern}, matched = {p_matches}, triggered = {p_flag}"

    # U - Urgency
    urgency_keywords = ["urgent", "now", "today", "immediately", "last chance", "act fast", "only one", "limited time", "flash", "ending soon", "sold out", "must buy", "almost sold out", "only 1 left", "ends soon"]
    u_matches = [kw for kw in urgency_keywords if kw in situation or kw in explanation]
    u_flag = bool(urgency) or bool(u_matches)
    if u_flag:
        triggered_flags.append("U")
    debug['U'] = f"[DEBUG] U: input = {situation} | {explanation}, matched = {u_matches}, triggered = {u_flag}"

    # L - Last Purchase
    l_flag = False
    l_matches = []
    if isinstance(last_days, int) and last_days <= 3:
        l_flag = True
        l_matches.append(f"days={last_days}")
        triggered_flags.append("L")
    debug['L'] = f"[DEBUG] L: input = {last_days}, matched = {l_matches}, triggered = {l_flag}"

    # S - Situation
    situation_keywords = ["celebration", "peer", "pressure", "boredom", "stress", "argument", "fight", "reward", "treat", "deserve", "special", "emotional", "trigger", "event", "occasion", "everyone around me", "everyone else is", "buying new stuff"]
    s_matches = [kw for kw in situation_keywords if kw in situation]
    s_flag = bool(s_matches)
    if s_flag:
        triggered_flags.append("S")
    debug['S'] = f"[DEBUG] S: input = {situation}, matched = {s_matches}, triggered = {s_flag}"

    # E - Explanation
    vague_explanations = ["just felt like it", "i dont know", "because i wanted to", "no reason", "just want", "cant explain", "idk", "impulse", "impulsively", "no solid reason", "felt like it", "just really want", "not sure why", "just want it", "feels right", "not sure", "just want", "probably dont need it", "probably dont need"]
    e_matches = [kw for kw in vague_explanations if kw in explanation]
    e_flag = bool(e_matches)
    if e_flag:
        triggered_flags.append("E")
    debug['E'] = f"[DEBUG] E: input = {explanation}, matched = {e_matches}, triggered = {e_flag}"

    # Fallback: if 4+ impulse-related keywords in any text, count as impulsive
    all_text = f"{item} {mood} {situation} {explanation}"
    impulse_keywords = luxury_keywords + mood_keywords + urgency_keywords + situation_keywords + vague_explanations + ["impulse", "impulsively", "regret", "splurge", "fomo", "treat", "sale", "exclusive", "scarcity", "limited", "must buy", "cant resist"]
    soft_trigger_count = sum(1 for k in impulse_keywords if k in all_text)
    total_triggers = len(set(triggered_flags))
    if total_triggers < 3 and soft_trigger_count >= 3:
        triggered_flags += ["soft"] * (3 - total_triggers)
        total_triggers = 3
    is_impulsive = total_triggers >= 3
    debug['soft_trigger_count'] = soft_trigger_count
    debug['total_triggers'] = total_triggers
    debug['is_impulsive'] = is_impulsive
    print("[IMPULSE DEBUG]", debug, "Triggered Flags:", triggered_flags)
    return {
        "total_triggers": total_triggers,
        "is_impulsive": is_impulsive,
        "triggered_flags": list(set(triggered_flags)),
        "debug": debug
    }
