import os
from memory import embedder, collection
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def smart_nudge(user_id: int, spending_intent: str, plan: str = "free") -> str:
    """
    Analyze user's past vector memories and return a smart nudge message based on similarity/context and plan.
    Uses OpenAI for plan-based tone and decision logic.
    """
    # Embed the spending intent
    embedding = embedder.encode([spending_intent]).tolist()
    # Search for similar memories for this user
    results = collection.query(
        query_embeddings=embedding,
        n_results=3,
        where={"user_id": user_id}
    )
    # Prepare context for OpenAI prompt
    similar_regret = None
    if results.get("distances") and results["distances"][0]:
        for idx, dist in enumerate(results["distances"][0]):
            if dist < (1 - 0.75):  # Similarity > 0.75
                similar_regret = results["documents"][0][idx]
                break
    # Dynamic prompt based on plan
    from utils.plan_features import sanitize_plan
    plan = sanitize_plan(plan)
    if plan == "ultra":
        tone = "Be highly protective, assertive, and act like a strong financial guardian."
    elif plan == "premium":
        tone = "Be firm but empathetic, and personalize the advice."
    else:
        tone = "Be friendly, soft, and suggestive."
    if similar_regret:
        user_context = f"The user previously regretted: '{similar_regret}'"
    else:
        user_context = "No strong regretful memory found."
    prompt = (
        f"User's spending intent: {spending_intent}\n"
        f"{user_context}\n"
        f"Plan: {plan}\n"
        f"Tone: {tone}\n"
        "Generate a short, actionable nudge for the user."
    )
    # Call OpenAI (fallback to static if key not set)
    try:
        if openai.api_key:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Fallback by plan
        if plan == "ultra":
            return "[ULTRA] Our system couldn't evaluate this, but your risk level might be high."
        elif plan == "premium":
            return "[PREMIUM] AI is temporarily unavailable. Use your financial instincts."
        else:
            return "[FREE] Unable to generate full nudge. Proceed carefully."
    # Fallback static message if OpenAI not called
    if similar_regret:
        if plan == "ultra":
            return f"[ULTRA] Think again, last time you spent on this you had regrets: '{similar_regret}'"
        elif plan == "premium":
            return f"[PREMIUM] You previously regretted a similar purchase: '{similar_regret}'"
        else:
            return f"Think again, last time you spent on this you had regrets: '{similar_regret}'"
    if plan == "ultra":
        return "[ULTRA] You usually avoid spending on this category during weekdays."
    elif plan == "premium":
        return "[PREMIUM] Consider your past habits before making this purchase."
    return "You usually avoid spending on this category during weekdays."
