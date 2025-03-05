from celery.schedules import crontab


from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

celery_app = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    # Настройка периодической задачи
    beat_schedule={
        'check-installment-payments-every-day': {
            'task': 'backend.database.finance_service.tasks.daily_installment_status_update',
            'schedule': crontab(hour="0", minute="0"),
        },
    }
)

