import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def generate_weekly_reviews():
    """Runs every Sunday at midnight and generates weekly reviews for all users."""
    from .database import SessionLocal
    from . import models
    from .agent import run_weekly_review

    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        today = str(date.today())
        monday = str(date.today() - timedelta(days=date.today().weekday()))

        for user in users:
            # don't create duplicates for the same week
            existing = db.query(models.WeeklyReview).filter(
                models.WeeklyReview.user_id == user.id,
                models.WeeklyReview.week_start == monday,
            ).first()

            if existing:
                continue

            logger.info(f"Generating weekly review for user {user.id}")
            review_text = run_weekly_review(user.id)

            review = models.WeeklyReview(
                user_id=user.id,
                week_start=monday,
                review_text=review_text,
            )
            db.add(review)

        db.commit()
        logger.info("Weekly reviews done.")
    except Exception as e:
        logger.error(f"Weekly review job failed: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    # every Sunday at 11:59 PM
    scheduler.add_job(
        generate_weekly_reviews,
        CronTrigger(day_of_week="sun", hour=23, minute=59),
        id="weekly_review",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — weekly reviews will run every Sunday.")
    return scheduler
