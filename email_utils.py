import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")


def send_weekly_report_email(to_email: str, report: dict):
    subject = "Your Weekly Finivo Spending Report"
    # Format the report dict into a plain-text body
    body = f"""
Hello,

Here is your weekly Finivo spending report:

User ID: {report.get('user_id')}
Week: {report.get('week')}
Total Spending Logs: {report.get('total_spending_logs')}
Regrets: {report.get('regrets')}
Top Items: {', '.join(report.get('top_items', []))}
Nudges Received: {report.get('nudges_received')}

Best regards,
Finivo AI
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        print(f"✅ Weekly report sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
