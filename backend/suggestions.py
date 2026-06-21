"""Smart task suggestions based on overdue items and weekly patterns."""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import models


def get_task_suggestions(db: Session, user_id: int) -> list[dict]:
    today = date.today()
    today_str = str(today)
    yesterday_str = str(today - timedelta(days=1))

    suggestions: list[dict] = []
    seen_titles: set[str] = set()

    def add(title: str, reason: str, priority: str = "medium"):
        key = title.strip().lower()
        if key and key not in seen_titles:
            seen_titles.add(key)
            suggestions.append({"title": title.strip(), "reason": reason, "priority": priority})

    overdue = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.completed_at.is_(None),
            models.Task.skipped.is_(False),
            models.Task.due_date.isnot(None),
            models.Task.due_date < today_str,
        )
        .order_by(models.Task.due_date)
        .all()
    )
    for t in overdue[:4]:
        add(t.title, f"Overdue since {t.due_date}", t.urgency)

    yesterday_slipped = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date == yesterday_str,
            models.Task.completed_at.is_(None),
            models.Task.skipped.is_(False),
        )
        .all()
    )
    for t in yesterday_slipped[:3]:
        add(t.title, "Incomplete yesterday — carry forward?", t.urgency)

    week_start = str(today - timedelta(days=today.weekday()))
    week_tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= week_start,
            models.Task.due_date <= today_str,
        )
        .all()
    )

    if week_tasks:
        skipped_health = [t for t in week_tasks if t.category == "health" and t.skipped]
        if skipped_health:
            add("30-min workout or walk", "Health tasks were skipped this week", "medium")

        skipped_learning = [t for t in week_tasks if t.category == "learning" and t.skipped]
        if skipped_learning:
            add(skipped_learning[0].title, "Learning task skipped earlier this week", "low")

        by_cat = Counter(t.category for t in week_tasks if t.completed_at)
        if by_cat.get("work", 0) >= 5 and by_cat.get("personal", 0) == 0:
            add("Personal errand or break", "Heavy work week — balance with something personal", "low")

    today_tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.due_date == today_str)
        .count()
    )
    if today_tasks == 0:
        add("Morning planning — list today's top 3 priorities", "No tasks logged for today yet", "high")

    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: priority_order.get(s["priority"], 1))
    return suggestions[:7]
