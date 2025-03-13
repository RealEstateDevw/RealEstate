import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from backend import get_db
from config import EMAIL_ADDRESS, SMTP_SERVER, SMTP_PORT, EMAIL_PASSWORD


def send_reminder_email(lead_id, callback_time, full_name, phone):
    subject = f"Напоминание о звонке: {full_name}"
    body = f"Уважаемый сотрудник,\n\nПора позвонить клиенту {full_name} (Телефон: {phone}).\nЗапланированное время: {callback_time.strftime('%Y-%m-%d %H:%M')}.\n\nС уважением,\nВаша система CRM"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = "salesperson_email@example.com"  # Replace with the salesperson's email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


def check_callbacks():
    db = next(get_db())
    try:
        from backend.database.models import Callback, Lead  # Import your models
        now = datetime.utcnow()
        pending_callbacks = db.query(Callback).filter(
            Callback.callback_time <= now,
            Callback.is_completed == False
        ).all()

        for callback in pending_callbacks:
            lead = db.query(Lead).filter(Lead.id == callback.lead_id).first()
            if lead:
                send_reminder_email(lead.id, callback.callback_time, lead.full_name, lead.phone)
                callback.is_completed = True  # Mark as completed after sending
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error in check_callbacks: {e}")
    finally:
        db.close()


# Schedule the callback checker to run every minute
scheduler = BackgroundScheduler()
scheduler.add_job(check_callbacks, 'interval', minutes=1)
scheduler.start()
