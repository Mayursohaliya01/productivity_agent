"""Read-only analytics helpers for dashboard, calendar, and export."""

from collections import Counter
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from . import models


def _has_checkin(db: Session, user_id: int, day: str) -> bool:
    log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == user_id,
        models.DailyLog.log_date == day,
    ).first()
    if log and (log.morning_note or log.evening_note):
        return True
    task_count = db.query(models.Task).filter(
        models.Task.user_id == user_id,
        models.Task.due_date == day,
    ).count()
    return task_count > 0


def compute_streak(db: Session, user_id: int, today: Optional[date] = None) -> int:
    """Consecutive days with a morning check-in (log entry or tasks), ending today or yesterday."""
    today = today or date.today()
    streak = 0
    current = today

    if not _has_checkin(db, user_id, str(current)):
        current = current - timedelta(days=1)

    while _has_checkin(db, user_id, str(current)):
        streak += 1
        current = current - timedelta(days=1)

    return streak


def week_bounds(today: Optional[date] = None) -> tuple[date, date]:
    today = today or date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def daily_completion_for_range(
    db: Session,
    user_id: int,
    start: date,
    end: date,
) -> list[dict]:
    start_str = str(start)
    end_str = str(end)

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= start_str,
            models.Task.due_date <= end_str,
        )
        .all()
    )

    by_date: dict[str, list] = {}
    for t in tasks:
        by_date.setdefault(t.due_date, []).append(t)

    results = []
    current = start
    while current <= end:
        ds = str(current)
        day_tasks = by_date.get(ds, [])
        total = len(day_tasks)
        completed = sum(1 for t in day_tasks if t.completed_at is not None)
        rate = round(completed / total * 100, 1) if total else 0.0
        results.append({
            "date": ds,
            "total": total,
            "completed": completed,
            "completion_rate": rate,
        })
        current += timedelta(days=1)

    return results


def dashboard_stats(db: Session, user_id: int) -> dict:
    week_start, week_end = week_bounds()
    start_str = str(week_start)
    end_str = str(week_end)

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= start_str,
            models.Task.due_date <= end_str,
        )
        .all()
    )

    completed = [t for t in tasks if t.completed_at is not None]
    by_category = dict(Counter(t.category for t in tasks))
    completion_rate = round(len(completed) / len(tasks) * 100, 1) if tasks else 0.0

    return {
        "streak": compute_streak(db, user_id),
        "week_start": start_str,
        "week_end": end_str,
        "daily_completion": daily_completion_for_range(db, user_id, week_start, week_end),
        "by_category": by_category,
        "total_tasks": len(tasks),
        "completed": len(completed),
        "skipped": sum(1 for t in tasks if t.skipped),
        "completion_rate": completion_rate,
    }


def month_calendar_overview(db: Session, user_id: int, year: int, month: int) -> dict:
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)

    start_str = str(first)
    end_str = str(last)

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= start_str,
            models.Task.due_date <= end_str,
        )
        .all()
    )
    tasks_by_date: dict[str, list] = {}
    for t in tasks:
        tasks_by_date.setdefault(t.due_date, []).append(t)

    logs = (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.user_id == user_id,
            models.DailyLog.log_date >= start_str,
            models.DailyLog.log_date <= end_str,
        )
        .all()
    )
    logs_by_date = {log.log_date: log for log in logs}

    eods = (
        db.query(models.EODSummary)
        .filter(
            models.EODSummary.user_id == user_id,
            models.EODSummary.summary_date >= start_str,
            models.EODSummary.summary_date <= end_str,
        )
        .all()
    )
    eod_dates = {e.summary_date for e in eods}

    days = []
    current = first
    while current <= last:
        ds = str(current)
        day_tasks = tasks_by_date.get(ds, [])
        log = logs_by_date.get(ds)
        days.append({
            "date": ds,
            "task_count": len(day_tasks),
            "completed_count": sum(1 for t in day_tasks if t.completed_at is not None),
            "has_eod": ds in eod_dates,
            "has_morning_checkin": bool(log and log.morning_note) or len(day_tasks) > 0,
        })
        current += timedelta(days=1)

    return {"month": f"{year:04d}-{month:02d}", "days": days}


def day_detail(db: Session, user_id: int, day: str) -> dict:
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.due_date == day)
        .order_by(models.Task.created_at)
        .all()
    )
    log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == user_id,
        models.DailyLog.log_date == day,
    ).first()
    eod = db.query(models.EODSummary).filter(
        models.EODSummary.user_id == user_id,
        models.EODSummary.summary_date == day,
    ).first()

    return {
        "date": day,
        "tasks": tasks,
        "morning_note": log.morning_note if log else None,
        "evening_note": log.evening_note if log else None,
        "eod_summary": eod.summary_text if eod else None,
        "tomorrow_plan": eod.tomorrow_plan if eod else None,
    }


def week_export_data(db: Session, user_id: int, username: str) -> dict:
    stats = dashboard_stats(db, user_id)
    week_start = stats["week_start"]
    week_end = stats["week_end"]

    eod_summaries = (
        db.query(models.EODSummary)
        .filter(
            models.EODSummary.user_id == user_id,
            models.EODSummary.summary_date >= week_start,
            models.EODSummary.summary_date <= week_end,
        )
        .order_by(models.EODSummary.summary_date)
        .all()
    )

    review = (
        db.query(models.WeeklyReview)
        .filter(
            models.WeeklyReview.user_id == user_id,
            models.WeeklyReview.week_start == week_start,
        )
        .first()
    )
    if not review:
        review = (
            db.query(models.WeeklyReview)
            .filter(models.WeeklyReview.user_id == user_id)
            .order_by(models.WeeklyReview.created_at.desc())
            .first()
        )

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= week_start,
            models.Task.due_date <= week_end,
        )
        .order_by(models.Task.due_date, models.Task.created_at)
        .all()
    )

    return {
        "username": username,
        "week_start": week_start,
        "week_end": week_end,
        "stats": stats,
        "tasks": tasks,
        "eod_summaries": eod_summaries,
        "weekly_review": review,
    }
