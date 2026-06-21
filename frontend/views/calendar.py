"""Calendar view — tasks and EOD summaries by date."""

import calendar
import json
from datetime import date

import streamlit as st

from api_client import api_get
from constants import URGENCY_LABELS


def _parse_month(month_str: str) -> tuple[int, int]:
    year, month = month_str.split("-")
    return int(year), int(month)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def _day_cell_label(day_info: dict) -> str:
    parts = []
    if day_info["task_count"]:
        parts.append(f"{day_info['completed_count']}/{day_info['task_count']} tasks")
    if day_info["has_eod"]:
        parts.append("EOD")
    if day_info["has_morning_checkin"] and not day_info["task_count"]:
        parts.append("check-in")
    return " · ".join(parts) if parts else "—"


def show_calendar():
    st.header("Calendar")
    st.caption("Browse tasks and end-of-day summaries by date.")

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = date.today().year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = date.today().month
    if "cal_selected" not in st.session_state:
        st.session_state.cal_selected = str(date.today())

    year = st.session_state.cal_year
    month = st.session_state.cal_month

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    if nav1.button("◀ Prev", use_container_width=True):
        year, month = _shift_month(year, month, -1)
        st.session_state.cal_year = year
        st.session_state.cal_month = month
        st.rerun()
    nav2.markdown(f"### {calendar.month_name[month]} {year}")
    if nav3.button("Next ▶", use_container_width=True):
        year, month = _shift_month(year, month, 1)
        st.session_state.cal_year = year
        st.session_state.cal_month = month
        st.rerun()

    resp = api_get(f"/analytics/calendar?year={year}&month={month}")
    if resp.status_code != 200:
        st.warning("Couldn't load calendar.")
        return

    month_data = resp.json()
    days_by_date = {d["date"]: d for d in month_data.get("days", [])}

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    header_cols = st.columns(7)
    for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        header_cols[i].markdown(f"**{name}**")

    for week in weeks:
        cols = st.columns(7)
        for i, day_num in enumerate(week):
            with cols[i]:
                if day_num == 0:
                    st.write("")
                    continue

                ds = f"{year:04d}-{month:02d}-{day_num:02d}"
                info = days_by_date.get(ds, {
                    "task_count": 0,
                    "completed_count": 0,
                    "has_eod": False,
                    "has_morning_checkin": False,
                })
                is_today = ds == str(date.today())
                is_selected = ds == st.session_state.cal_selected
                label = _day_cell_label(info)

                btn_type = "primary" if is_selected else "secondary"
                prefix = "● " if is_today else ""
                if st.button(
                    f"{prefix}{day_num}\n{label}",
                    key=f"cal_{ds}",
                    use_container_width=True,
                    type=btn_type,
                ):
                    st.session_state.cal_selected = ds
                    st.rerun()

    st.divider()
    _show_day_detail(st.session_state.cal_selected)


def _show_day_detail(day: str):
    st.subheader(f"Details — {day}")

    resp = api_get(f"/analytics/calendar/{day}")
    if resp.status_code != 200:
        st.info("No data for this date.")
        return

    detail = resp.json()
    has_content = False

    if detail.get("morning_note"):
        has_content = True
        st.markdown(f"**Morning note:** _{detail['morning_note']}_")

    tasks = detail.get("tasks", [])
    if tasks:
        has_content = True
        st.markdown("**Tasks**")
        for t in tasks:
            urg = URGENCY_LABELS.get(t.get("urgency", "medium"), "")
            cat = t.get("category", "other")
            if t.get("completed_at"):
                st.write(f"~~{t['title']}~~ `{urg}` — _{cat}_ (done)")
            elif t.get("skipped"):
                st.write(f"{t['title']} `{urg}` — _{cat}_ (skipped)")
            else:
                st.write(f"**{t['title']}** `{urg}` — _{cat}_")

    if detail.get("evening_note"):
        has_content = True
        st.markdown(f"**Evening note:** _{detail['evening_note']}_")

    if detail.get("eod_summary"):
        has_content = True
        st.markdown("**EOD summary**")
        st.info(detail["eod_summary"])

    if detail.get("tomorrow_plan"):
        try:
            plan = json.loads(detail["tomorrow_plan"])
            if plan:
                has_content = True
                st.markdown("**Tomorrow's plan was:**")
                for item in plan:
                    st.write(f"- {item}")
        except (json.JSONDecodeError, TypeError):
            pass

    if not has_content:
        st.info("Nothing logged on this date.")
