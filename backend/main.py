import json
import logging
from datetime import date, timedelta, datetime
from typing import List, Optional
# v1.0.1

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import settings
from .database import engine, get_db
from . import models, schemas, auth
from .agent import run_morning, run_evening
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create all tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Productivity Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler = None


@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()

    # DEMO — remove before production
    if settings.DEMO_SEED:
        from .seed_demo import seed_demo_data
        seed_demo_data()


@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown()


# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=schemas.TokenResponse, status_code=201)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username taken")

    user = models.User(
        email=body.email,
        username=body.username,
        hashed_password=auth.hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth.create_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(body: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == body.username).first()
    if not user or not auth.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong username or password")

    token = auth.create_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@app.get("/auth/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {"user_id": current_user.id, "username": current_user.username, "email": current_user.email}


# ─── MORNING CHECK-IN ────────────────────────────────────────────────────────

@app.post("/checkin/morning", response_model=schemas.MorningCheckinResponse)
def morning_checkin(
    body: schemas.MorningCheckin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not body.tasks:
        raise HTTPException(status_code=400, detail="Add at least one task to start your day")

    today = str(date.today())

    # run the agent to classify tasks and surface overdue
    agent_result = run_morning(current_user.id, body.tasks, body.morning_note or "")

    classified = agent_result.get("classified_tasks", [])
    overdue = agent_result.get("overdue_tasks", [])

    # save the classified tasks to DB
    saved_ids = []
    for item in classified:
        task = models.Task(
            user_id=current_user.id,
            title=item.get("title", "Untitled"),
            category=item.get("category", "other"),
            urgency=item.get("urgency", "medium"),
            due_date=today,
        )
        db.add(task)
        db.flush()  # get the ID before commit
        saved_ids.append(task.id)

    # save or update the daily log for today
    log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.id,
        models.DailyLog.log_date == today,
    ).first()

    if log:
        log.morning_note = body.morning_note
    else:
        log = models.DailyLog(
            user_id=current_user.id,
            log_date=today,
            morning_note=body.morning_note,
        )
        db.add(log)

    db.commit()

    return {
        "classified_tasks": classified,
        "overdue_tasks": overdue,
        "saved_task_ids": saved_ids,
    }


# ─── TASKS ───────────────────────────────────────────────────────────────────

@app.get("/tasks/today", response_model=List[schemas.TaskOut])
def get_todays_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today = str(date.today())
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == current_user.id, models.Task.due_date == today)
        .order_by(models.Task.created_at)
        .all()
    )
    return tasks


@app.post("/tasks/{task_id}/complete", response_model=schemas.TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.completed_at = datetime.utcnow()
    task.skipped = False
    db.commit()
    db.refresh(task)
    return task


@app.post("/tasks/{task_id}/skip", response_model=schemas.TaskOut)
def skip_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.skipped = True
    task.completed_at = None
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


# ─── EVENING CHECK-IN ────────────────────────────────────────────────────────

@app.post("/checkin/evening", response_model=schemas.EveningCheckinResponse)
def evening_checkin(
    body: schemas.EveningCheckin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today = str(date.today())

    # mark completed tasks in the DB first, then let the agent query
    for tid in body.completed_task_ids:
        task = db.query(models.Task).filter(
            models.Task.id == tid,
            models.Task.user_id == current_user.id,
        ).first()
        if task:
            task.completed_at = datetime.utcnow()
            task.skipped = False

    for tid in (body.skipped_task_ids or []):
        task = db.query(models.Task).filter(
            models.Task.id == tid,
            models.Task.user_id == current_user.id,
        ).first()
        if task:
            task.skipped = True
            task.completed_at = None

    # update evening log note
    log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.id,
        models.DailyLog.log_date == today,
    ).first()
    if log:
        log.evening_note = body.evening_note
    else:
        log = models.DailyLog(
            user_id=current_user.id,
            log_date=today,
            evening_note=body.evening_note,
        )
        db.add(log)

    db.commit()

    # now run the agent — it queries the DB which has updated data
    agent_result = run_evening(
        current_user.id,
        body.completed_task_ids,
        body.skipped_task_ids or [],
        body.evening_note or "",
    )

    eod_text = agent_result.get("eod_summary", "")
    plan = agent_result.get("tomorrow_plan", [])

    # save EOD to DB
    existing_eod = db.query(models.EODSummary).filter(
        models.EODSummary.user_id == current_user.id,
        models.EODSummary.summary_date == today,
    ).first()

    if existing_eod:
        existing_eod.summary_text = eod_text
        existing_eod.tomorrow_plan = json.dumps(plan)
    else:
        eod = models.EODSummary(
            user_id=current_user.id,
            summary_date=today,
            summary_text=eod_text,
            tomorrow_plan=json.dumps(plan),
        )
        db.add(eod)

    db.commit()

    return {"eod_summary": eod_text, "tomorrow_plan": plan}


# ─── EOD & HISTORY ───────────────────────────────────────────────────────────

@app.get("/eod/latest", response_model=schemas.EODSummaryOut)
def get_latest_eod(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    eod = (
        db.query(models.EODSummary)
        .filter(models.EODSummary.user_id == current_user.id)
        .order_by(models.EODSummary.created_at.desc())
        .first()
    )
    if not eod:
        raise HTTPException(status_code=404, detail="No EOD summary found yet")
    return eod


@app.get("/eod/history", response_model=List[schemas.EODSummaryOut])
def get_eod_history(
    limit: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    summaries = (
        db.query(models.EODSummary)
        .filter(models.EODSummary.user_id == current_user.id)
        .order_by(models.EODSummary.created_at.desc())
        .limit(limit)
        .all()
    )
    return summaries


# ─── WEEKLY STATS & REVIEW ───────────────────────────────────────────────────

@app.get("/tasks/week", response_model=schemas.WeekStatsResponse)
def get_week_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    week_start_str = str(week_start)
    week_end_str = str(week_end)

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == current_user.id,
            models.Task.due_date >= week_start_str,
            models.Task.due_date <= week_end_str,
        )
        .all()
    )

    completed = [t for t in tasks if t.completed_at is not None]
    slipped = [t for t in tasks if t.completed_at is None and not t.skipped]
    skipped = [t for t in tasks if t.skipped]

    from collections import Counter
    by_category = dict(Counter(t.category for t in tasks))

    # grab eod summaries for each day this week
    eod_summaries = (
        db.query(models.EODSummary)
        .filter(
            models.EODSummary.user_id == current_user.id,
            models.EODSummary.summary_date >= week_start_str,
            models.EODSummary.summary_date <= week_end_str,
        )
        .order_by(models.EODSummary.summary_date)
        .all()
    )

    daily = [
        {"date": e.summary_date, "summary": e.summary_text}
        for e in eod_summaries
    ]

    completion_rate = round(len(completed) / len(tasks) * 100, 1) if tasks else 0.0

    return {
        "week_start": week_start_str,
        "week_end": week_end_str,
        "total_tasks": len(tasks),
        "completed": len(completed),
        "slipped": len(slipped),
        "skipped": len(skipped),
        "completion_rate": completion_rate,
        "by_category": by_category,
        "daily_summaries": daily,
    }


@app.get("/review/latest", response_model=schemas.WeeklyReviewOut)
def get_latest_review(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    review = (
        db.query(models.WeeklyReview)
        .filter(models.WeeklyReview.user_id == current_user.id)
        .order_by(models.WeeklyReview.created_at.desc())
        .first()
    )
    if not review:
        raise HTTPException(status_code=404, detail="No weekly review yet. Check back on Sunday!")
    return review


@app.post("/review/generate", response_model=schemas.WeeklyReviewOut)
def generate_review_now(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Manual trigger for weekly review — useful for testing."""
    from .agent import run_weekly_review

    today = date.today()
    monday = str(today - timedelta(days=today.weekday()))

    review_text = run_weekly_review(current_user.id)

    existing = db.query(models.WeeklyReview).filter(
        models.WeeklyReview.user_id == current_user.id,
        models.WeeklyReview.week_start == monday,
    ).first()

    if existing:
        existing.review_text = review_text
        db.commit()
        db.refresh(existing)
        return existing

    review = models.WeeklyReview(
        user_id=current_user.id,
        week_start=monday,
        review_text=review_text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# ─── ANALYTICS (dashboard, calendar, export) ─────────────────────────────────

@app.get("/analytics/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from .analytics import dashboard_stats
    return dashboard_stats(db, current_user.id)


@app.get("/analytics/calendar", response_model=schemas.CalendarMonthResponse)
def get_calendar_month(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be 1–12")
    from .analytics import month_calendar_overview
    return month_calendar_overview(db, current_user.id, year, month)


@app.get("/analytics/calendar/{day}", response_model=schemas.CalendarDayDetail)
def get_calendar_day(
    day: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from .analytics import day_detail
    result = day_detail(db, current_user.id, day)
    return {
        "date": result["date"],
        "tasks": result["tasks"],
        "morning_note": result["morning_note"],
        "evening_note": result["evening_note"],
        "eod_summary": result["eod_summary"],
        "tomorrow_plan": result["tomorrow_plan"],
    }


@app.get("/analytics/export/week")
def export_week(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from .analytics import week_export_data
    data = week_export_data(db, current_user.id, current_user.username)
    return {
        "username": data["username"],
        "week_start": data["week_start"],
        "week_end": data["week_end"],
        "stats": data["stats"],
        "tasks": [
            {
                "title": t.title,
                "category": t.category,
                "urgency": t.urgency,
                "due_date": t.due_date,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "skipped": t.skipped,
            }
            for t in data["tasks"]
        ],
        "eod_summaries": [
            {
                "summary_date": e.summary_date,
                "summary_text": e.summary_text,
                "tomorrow_plan": e.tomorrow_plan,
            }
            for e in data["eod_summaries"]
        ],
        "weekly_review": (
            {"week_start": data["weekly_review"].week_start, "review_text": data["weekly_review"].review_text}
            if data["weekly_review"] else None
        ),
    }


# ─── PHASE 2: CHAT, SUGGESTIONS, POMODORO ────────────────────────────────────

@app.get("/suggestions/tasks", response_model=schemas.SuggestionsResponse)
def get_suggestions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from .suggestions import get_task_suggestions
    return {"suggestions": get_task_suggestions(db, current_user.id)}


@app.post("/chat", response_model=schemas.ChatResponse)
def chat_with_agent(
    body: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from .chat_service import run_chat
    history = [{"role": m.role, "content": m.content} for m in (body.history or [])]
    reply = run_chat(db, current_user.id, body.message, history)
    return {"reply": reply}


@app.post("/pomodoro/complete", response_model=schemas.PomodoroOut, status_code=201)
def log_pomodoro(
    body: schemas.PomodoroCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    entry = models.PomodoroLog(
        user_id=current_user.id,
        task_title=body.task_title,
        duration_minutes=body.duration_minutes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.get("/pomodoro/today", response_model=schemas.PomodoroTodayResponse)
def get_pomodoros_today(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today_str = str(date.today())
    sessions = (
        db.query(models.PomodoroLog)
        .filter(
            models.PomodoroLog.user_id == current_user.id,
            func.date(models.PomodoroLog.completed_at) == today_str,
        )
        .order_by(models.PomodoroLog.completed_at.desc())
        .all()
    )
    return {
        "count": len(sessions),
        "total_minutes": sum(s.duration_minutes for s in sessions),
        "sessions": sessions,
    }


# ═══ DEMO ONLY — remove before production ═══════════════════════════════════

@app.get("/demo/today-context")
def demo_today_context(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Read-only helper so the demo UI can show today's morning check-in."""
    today = str(date.today())
    log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.id,
        models.DailyLog.log_date == today,
    ).first()
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == current_user.id, models.Task.due_date == today)
        .order_by(models.Task.created_at)
        .all()
    )
    overdue = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == current_user.id,
            models.Task.due_date < today,
            models.Task.completed_at.is_(None),
            models.Task.skipped.is_(False),
        )
        .order_by(models.Task.due_date)
        .all()
    )
    return {
        "morning_note": log.morning_note if log else None,
        "tasks": [
            {
                "title": t.title,
                "category": t.category,
                "urgency": t.urgency,
                "completed_at": t.completed_at,
                "skipped": t.skipped,
            }
            for t in tasks
        ],
        "overdue_tasks": [
            {"title": t.title, "urgency": t.urgency, "due_date": t.due_date}
            for t in overdue
        ],
    }
