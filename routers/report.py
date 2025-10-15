from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import SessionLocal
from model import SpendingLog, NudgeLog, User
from email_utils import send_weekly_report_email
from utils.plan_features import get_plan_features

router = APIRouter(prefix="/report", tags=["Report"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/weekly/{user_id}")
def get_weekly_report(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from utils.plan_features import sanitize_plan
    features = get_plan_features(sanitize_plan(user.plan))
    # Check report frequency permission
    if features["report_frequency"] != "weekly":
        raise HTTPException(status_code=403, detail="Weekly reports are not available for your current plan.")
    # Calculate current week's Monday and Sunday
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    # Format week as 'June 16–22, 2025' (en dash, not ASCII dash)
    week_str = f"{start_of_week.strftime('%B %d')} - {end_of_week.strftime('%d, %Y')}"
    # Query spending logs for this week
    logs = db.query(SpendingLog).filter(
        SpendingLog.user_id == user_id,
        SpendingLog.timestamp >= datetime.combine(start_of_week, datetime.min.time()),
        SpendingLog.timestamp <= datetime.combine(end_of_week, datetime.max.time())
    ).all()
    total_spending_logs = len(logs)
    regrets = sum(1 for log in logs if log.decision and 'regret' in log.decision.lower())
    # Top 3 most frequent item_names
    from collections import Counter
    # Use category if available, else item_name
    top_items = [item for item, _ in Counter([
        log.category if log.category else log.item_name for log in logs
    ]).most_common(3)]
    total_amount_spent = sum(log.amount for log in logs)
    # Deep insights if enabled
    if features["deep_insights"]:
        insights = {"message": "[Sample] Deep insights would be generated here."}
    else:
        insights = {"message": "Upgrade to Elite to access deep spending insights."}
    report_data = {
        "user_id": user_id,
        "week": week_str,
        "total_logs": total_spending_logs,
        "total_spent": total_amount_spent,
        "regrets": regrets,
        "top_items": top_items,
        "insights": insights
    }
    # Nudge logs for this week
    nudge_count = db.query(NudgeLog).filter(
        NudgeLog.user_id == user_id,
        NudgeLog.timestamp >= datetime.combine(start_of_week, datetime.min.time()),
        NudgeLog.timestamp <= datetime.combine(end_of_week, datetime.max.time())
    ).count()
    email_status = ""
    if user.email:
        try:
            send_weekly_report_email(user.email, report_data)
            email_status = f"✅ Report emailed to {user.email}"
        except Exception as e:
            email_status = f"⚠️ Report generated but email failed: {e}"
    else:
        email_status = "⚠️ Report generated but user email not found."
    return {
        "status": "success",
        "email_sent": email_status,
        "report": report_data
    }
