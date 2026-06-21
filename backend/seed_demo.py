"""
=============================================================================
DEMO DATA SEED — REMOVE BEFORE PRODUCTION
=============================================================================
Populates the database with 7 days of realistic sample data for user "Mayur".
Toggle via DEMO_SEED=true in .env (auto-runs on backend startup).
Run manually:  python -m backend.seed_demo
Clear & reseed: python -m backend.seed_demo --force
=============================================================================
"""

import argparse
import json
import logging
from datetime import date, datetime, timedelta

from .database import SessionLocal
from . import models, auth

logger = logging.getLogger(__name__)

# --- DEMO CREDENTIALS (share with client for login) ---
DEMO_USERNAME = "Mayur"
DEMO_EMAIL = "mayur@demo.com"
DEMO_PASSWORD = "demo123"


def _dt(day: date, hour: int = 14, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute)


def _week_dates(today: date | None = None) -> list[date]:
    """Monday through today (up to 7 days) of the current week."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        if d > today:
            break
        days.append(d)
    return days


def _day_data(day: date, today: date) -> dict:
    """Return tasks, logs, and EOD content for a given day."""
    ds = str(day)
    is_today = day == today

    catalog = {
        0: {  # Monday
            "morning_note": "Fresh week — want to nail the client proposal before Wednesday.",
            "evening_note": "Solid start. Skipped gym but the proposal draft is in good shape.",
            "tasks": [
                ("Draft Q3 client proposal", "work", "high", "done"),
                ("Prep slides for team standup", "work", "medium", "done"),
                ("30-min gym session", "health", "medium", "skipped"),
                ("Read FastAPI middleware docs", "learning", "low", "done"),
            ],
            "eod": (
                "Started the week strong with meaningful progress on the client proposal "
                "and standup prep. Skipped the gym but stayed focused on high-priority work. "
                "Tomorrow I'll push the proposal to a shareable draft."
            ),
            "tomorrow_plan": [
                "Finish client proposal first draft",
                "Send proposal to internal review",
                "Make up the skipped gym session",
            ],
        },
        1: {  # Tuesday
            "morning_note": "Blocking 9–12 for deep work on the proposal. No meetings until afternoon.",
            "evening_note": "Proposal sent for review. Gym done. Feeling productive.",
            "tasks": [
                ("Finish client proposal first draft", "work", "high", "done"),
                ("Send proposal to internal review", "work", "high", "done"),
                ("45-min strength training", "health", "medium", "done"),
                ("Reply to vendor emails", "work", "low", "done"),
                ("Pick up dry cleaning", "personal", "low", "skipped"),
            ],
            "eod": (
                "A high-output Tuesday. The proposal went out for review and I cleared "
                "vendor backlog. Skipped dry cleaning — can do Wednesday. Energy was good "
                "after getting the gym in."
            ),
            "tomorrow_plan": [
                "Incorporate proposal feedback",
                "Schedule client follow-up call",
                "Review sprint board with team",
            ],
        },
        2: {  # Wednesday
            "morning_note": "Midweek check — proposal feedback expected by noon.",
            "evening_note": "Feedback came in heavier than expected. Adjusted plan for Thursday.",
            "tasks": [
                ("Incorporate proposal feedback", "work", "high", "done"),
                ("Sprint board review with team", "work", "medium", "done"),
                ("Schedule client follow-up call", "work", "medium", "done"),
                ("Meal prep for rest of week", "personal", "low", "done"),
                ("Online course: Module 3", "learning", "low", "skipped"),
            ],
            "eod": (
                "Handled heavier-than-expected proposal feedback and still moved the sprint "
                "forward. Client call is booked for Friday. Skipped the online course module — "
                "will catch up over the weekend."
            ),
            "tomorrow_plan": [
                "Revise proposal sections 2 and 4",
                "Prepare talking points for client call",
                "Block time for course Module 3",
            ],
        },
        3: {  # Thursday
            "morning_note": "Two meetings today but protecting 2–4pm for proposal revisions.",
            "evening_note": "Meetings ran long. Proposal revisions only half done.",
            "tasks": [
                ("Revise proposal sections 2 and 4", "work", "high", "done"),
                ("Prepare client call talking points", "work", "high", "done"),
                ("1:1 with manager", "work", "medium", "done"),
                ("Grocery run", "personal", "low", "done"),
                ("Online course: Module 3", "learning", "low", "skipped"),
            ],
            "eod": (
                "Meetings ate more time than planned, but proposal revisions and call prep "
                "are done. Still behind on the online course. Tomorrow is mostly heads-down "
                "before the client call."
            ),
            "tomorrow_plan": [
                "Final proposal polish",
                "Client follow-up call at 3pm",
                "Update project tracker",
            ],
        },
        4: {  # Friday
            "morning_note": "Client call at 3pm — everything else is prep for that.",
            "evening_note": "Call went well! Client wants a revised timeline by Monday.",
            "tasks": [
                ("Final proposal polish", "work", "high", "done"),
                ("Client follow-up call", "work", "high", "done"),
                ("Update project tracker", "work", "medium", "done"),
                ("Plan weekend errands", "personal", "low", "done"),
                ("Evening walk 30 min", "health", "low", "skipped"),
            ],
            "eod": (
                "Great client call — they're engaged and want a revised timeline Monday. "
                "Wrapped the week with the tracker updated. Skipped the evening walk but "
                "overall a strong Friday."
            ),
            "tomorrow_plan": [
                "Organize home office",
                "Backup project files",
                "Light weekend reading",
            ],
        },
        5: {  # Saturday
            "morning_note": "Keeping Saturday light — errands and recovery.",
            "evening_note": "Relaxed day. Didn't get to the home office or backup.",
            "tasks": [
                ("Organize home office", "personal", "medium", "pending"),
                ("Backup project files", "work", "medium", "pending"),
                ("Long walk in the park", "health", "low", "done"),
                ("Call parents", "personal", "low", "done"),
            ],
            "eod": (
                "A lighter Saturday focused on family and recovery. Got the walk in and "
                "caught up with parents. Home office and file backup slipped — carrying "
                "those to Sunday."
            ),
            "tomorrow_plan": [
                "Organize home office",
                "Backup project files",
                "Weekly planning for next week",
            ],
        },
        6: {  # Sunday
            "morning_note": "Sunday planning day — close out the week and set up Monday.",
            "evening_note": None,
            "tasks": [
                ("Weekly planning session", "work", "high", "pending"),
                ("Organize home office", "personal", "medium", "pending"),
                ("Backup project files", "work", "medium", "pending"),
                ("30-min yoga", "health", "low", "done"),
                ("Review client feedback email", "work", "high", "pending"),
                ("Family brunch prep", "personal", "medium", "done"),
            ],
            "eod": None,
            "tomorrow_plan": None,
        },
    }

    entry = catalog.get(day.weekday(), catalog[0])
    tasks = []
    for title, category, urgency, status in entry["tasks"]:
        task = {
            "title": title,
            "category": category,
            "urgency": urgency,
            "due_date": ds,
            "skipped": status == "skipped",
            "completed_at": _dt(day, 16, 30) if status == "done" else None,
            "created_at": _dt(day, 8, 15),
        }
        tasks.append(task)

    result = {
        "log_date": ds,
        "morning_note": entry["morning_note"],
        "evening_note": entry["evening_note"],
        "tasks": tasks,
    }

    if entry["eod"] and not is_today:
        result["eod"] = {
            "summary_text": entry["eod"],
            "tomorrow_plan": json.dumps(entry["tomorrow_plan"]),
            "created_at": _dt(day, 20, 0),
        }

    return result


WEEKLY_REVIEW_TEXT = (
    "**Week in review (demo data)**\n\n"
    "Mayur had a productive work week centred on the Q3 client proposal — from first draft "
    "through internal review, revisions, and a successful Friday client call. Work tasks "
    "dominated (~65% of logged items) with a healthy mix of personal and health activities.\n\n"
    "**Patterns noticed:**\n"
    "- High-priority work items were consistently completed Mon–Fri\n"
    "- Health tasks were attempted 4/7 days; gym/yoga slipped twice but walks compensated\n"
    "- Learning tasks (online course) were deprioritised mid-week — consider blocking a fixed slot\n"
    "- Weekend personal admin (home office, backups) carried over — typical Sunday catch-up\n\n"
    "**Suggested focus for next week:**\n"
    "1. Send revised timeline to client Monday morning\n"
    "2. Complete home office organisation and file backup early in the week\n"
    "3. Protect two 30-min learning blocks for the online course"
)


def _clear_user_data(db, user_id: int) -> None:
    db.query(models.Task).filter(models.Task.user_id == user_id).delete()
    db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id).delete()
    db.query(models.EODSummary).filter(models.EODSummary.user_id == user_id).delete()
    db.query(models.WeeklyReview).filter(models.WeeklyReview.user_id == user_id).delete()
    db.commit()


def seed_demo_data(force: bool = False) -> bool:
    """
    Seed demo data for user Mayur. Returns True if seeding ran, False if skipped.
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == DEMO_USERNAME).first()

        if user and not force:
            existing = db.query(models.EODSummary).filter(
                models.EODSummary.user_id == user.id
            ).count()
            if existing > 0:
                logger.info("DEMO SEED: data already present for '%s' — skipping (use --force to reset)", DEMO_USERNAME)
                return False

        if user and force:
            logger.info("DEMO SEED: clearing existing data for '%s'", DEMO_USERNAME)
            _clear_user_data(db, user.id)

        if not user:
            user = models.User(
                email=DEMO_EMAIL,
                username=DEMO_USERNAME,
                hashed_password=auth.hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("DEMO SEED: created user '%s' (password: %s)", DEMO_USERNAME, DEMO_PASSWORD)

        today = date.today()
        monday = today - timedelta(days=today.weekday())

        for day in _week_dates(today):
            payload = _day_data(day, today)

            db.add(models.DailyLog(
                user_id=user.id,
                log_date=payload["log_date"],
                morning_note=payload["morning_note"],
                evening_note=payload["evening_note"],
                created_at=_dt(day, 7, 45),
            ))

            for t in payload["tasks"]:
                db.add(models.Task(
                    user_id=user.id,
                    title=t["title"],
                    category=t["category"],
                    urgency=t["urgency"],
                    due_date=t["due_date"],
                    completed_at=t["completed_at"],
                    skipped=t["skipped"],
                    created_at=t["created_at"],
                ))

            if "eod" in payload:
                eod = payload["eod"]
                db.add(models.EODSummary(
                    user_id=user.id,
                    summary_date=payload["log_date"],
                    summary_text=eod["summary_text"],
                    tomorrow_plan=eod["tomorrow_plan"],
                    created_at=eod["created_at"],
                ))

        db.add(models.WeeklyReview(
            user_id=user.id,
            week_start=str(monday),
            review_text=WEEKLY_REVIEW_TEXT,
            created_at=_dt(today, 9, 0) if today.weekday() == 6 else _dt(monday + timedelta(days=6), 9, 0),
        ))

        db.commit()
        logger.info(
            "DEMO SEED: populated %d day(s) of data for '%s' (login: %s / %s)",
            len(_week_dates(today)), DEMO_USERNAME, DEMO_USERNAME, DEMO_PASSWORD,
        )
        return True
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Seed demo data for client presentations")
    parser.add_argument("--force", action="store_true", help="Clear existing Mayur data and reseed")
    args = parser.parse_args()
    seed_demo_data(force=args.force)
