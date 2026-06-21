"""Chat agent — answers questions using the user's productivity data."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import models
from .agent import SMART_MODEL, _call_groq
from .analytics import compute_streak, week_bounds


def _gather_context(db: Session, user_id: int) -> str:
    today = date.today()
    today_str = str(today)
    week_start, week_end = week_bounds(today)

    today_tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.due_date == today_str)
        .all()
    )
    pending = [t for t in today_tasks if not t.completed_at and not t.skipped]
    done = [t for t in today_tasks if t.completed_at]

    overdue = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.completed_at.is_(None),
            models.Task.skipped.is_(False),
            models.Task.due_date.isnot(None),
            models.Task.due_date < today_str,
        )
        .limit(8)
        .all()
    )

    week_tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user_id,
            models.Task.due_date >= str(week_start),
            models.Task.due_date <= str(week_end),
        )
        .all()
    )
    week_done = sum(1 for t in week_tasks if t.completed_at)

    latest_eod = (
        db.query(models.EODSummary)
        .filter(models.EODSummary.user_id == user_id)
        .order_by(models.EODSummary.summary_date.desc())
        .first()
    )

    streak = compute_streak(db, user_id, today)

    lines = [
        f"Today: {today_str}",
        f"Check-in streak: {streak} day(s)",
        f"This week ({week_start} to {week_end}): {len(week_tasks)} tasks, {week_done} completed",
        f"Today — pending: {', '.join(t.title for t in pending) or 'none'}",
        f"Today — done: {', '.join(t.title for t in done) or 'none'}",
        f"Overdue: {', '.join(t.title for t in overdue) or 'none'}",
    ]
    if latest_eod:
        lines.append(f"Latest EOD ({latest_eod.summary_date}): {latest_eod.summary_text[:300]}")

    return "\n".join(lines)


def run_chat(db: Session, user_id: int, message: str, history: list[dict] | None = None) -> str:
    context = _gather_context(db, user_id)
    history = history or []

    history_text = ""
    for msg in history[-8:]:
        role = msg.get("role", "user").capitalize()
        history_text += f"{role}: {msg.get('content', '')}\n"

    prompt = f"""You are a friendly personal productivity coach. Answer based ONLY on the user's data below.
Be concise (2-5 sentences). If you don't have enough data, say so honestly.

USER DATA:
{context}

RECENT CHAT:
{history_text or '(none)'}

User: {message}
Coach:"""

    try:
        return _call_groq(SMART_MODEL, prompt, max_tokens=400)
    except Exception:
        return _fallback_reply(message, context)


def _fallback_reply(message: str, context: str) -> str:
    lower = message.lower()
    if "priority" in lower or "today" in lower or "focus" in lower:
        for line in context.splitlines():
            if line.startswith("Today — pending:"):
                pending = line.replace("Today — pending:", "").strip()
                if pending and pending != "none":
                    return f"Based on your data, focus on: {pending}. Tackle high-urgency items first."
                return "You have no pending tasks for today. Do a morning check-in to add some!"
    if "overdue" in lower:
        for line in context.splitlines():
            if line.startswith("Overdue:"):
                return f"Your overdue items: {line.replace('Overdue:', '').strip()}"
    if "streak" in lower:
        for line in context.splitlines():
            if "streak" in line.lower():
                return line
    return (
        "I can help with priorities, overdue tasks, and weekly patterns. "
        "Try asking: 'What should I focus on today?' or 'How is my week going?'"
    )
