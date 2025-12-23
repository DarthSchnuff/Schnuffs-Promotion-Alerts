from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Streamer
from app.twitch import is_live
from app.discord import send_notification
from app.settings import settings

def check_streamers():
    db: Session = SessionLocal()
    try:
        for s in db.query(Streamer).all():
            stream = is_live(s.login)
            if stream and not s.is_live:
                send_notification(s.login, stream)
                s.is_live = True
            elif not stream:
                s.is_live = False
        db.commit()
    finally:
        db.close()

def start():
    sched = BackgroundScheduler()
    sched.add_job(check_streamers, "interval", seconds=settings.CHECK_INTERVAL)
    sched.start()
