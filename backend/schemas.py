from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime



class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class TaskOut(BaseModel):
    id: int
    title: str
    category: str
    urgency: str
    due_date: Optional[str]
    completed_at: Optional[datetime]
    skipped: bool
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MorningCheckin(BaseModel):
    tasks: List[str]
    morning_note: Optional[str] = ""


class MorningCheckinResponse(BaseModel):
    classified_tasks: List[dict]
    overdue_tasks: List[dict]
    saved_task_ids: List[int]


class EveningCheckin(BaseModel):
    completed_task_ids: List[int]
    skipped_task_ids: Optional[List[int]] = []
    evening_note: Optional[str] = ""


class EveningCheckinResponse(BaseModel):
    eod_summary: str
    tomorrow_plan: List[str]


class EODSummaryOut(BaseModel):
    id: int
    summary_date: str
    summary_text: str
    tomorrow_plan: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyReviewOut(BaseModel):
    id: int
    week_start: str
    review_text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WeekStatsResponse(BaseModel):
    week_start: str
    week_end: str
    total_tasks: int
    completed: int
    slipped: int
    skipped: int
    completion_rate: float
    by_category: dict
    daily_summaries: List[dict]


class DailyCompletion(BaseModel):
    date: str
    total: int
    completed: int
    completion_rate: float


class DashboardResponse(BaseModel):
    streak: int
    week_start: str
    week_end: str
    daily_completion: List[DailyCompletion]
    by_category: dict
    total_tasks: int
    completed: int
    skipped: int
    completion_rate: float


class CalendarDaySummary(BaseModel):
    date: str
    task_count: int
    completed_count: int
    has_eod: bool
    has_morning_checkin: bool


class CalendarMonthResponse(BaseModel):
    month: str
    days: List[CalendarDaySummary]


class CalendarDayDetail(BaseModel):
    date: str
    tasks: List[TaskOut]
    morning_note: Optional[str] = None
    evening_note: Optional[str] = None
    eod_summary: Optional[str] = None
    tomorrow_plan: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    reply: str


class TaskSuggestion(BaseModel):
    title: str
    reason: str
    priority: str


class SuggestionsResponse(BaseModel):
    suggestions: List[TaskSuggestion]


class PomodoroCreate(BaseModel):
    task_title: str
    duration_minutes: int = 25


class PomodoroOut(BaseModel):
    id: int
    task_title: str
    duration_minutes: int
    completed_at: datetime

    model_config = {"from_attributes": True}


class PomodoroTodayResponse(BaseModel):
    count: int
    total_minutes: int
    sessions: List[PomodoroOut]
