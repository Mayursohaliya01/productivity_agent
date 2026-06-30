"""Shared API client for Streamlit frontend."""
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8001")

def api_get(path: str) -> requests.Response:
    token = st.session_state.get("token", "")
    return requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )


def api_post(path: str, data: dict) -> requests.Response:
    token = st.session_state.get("token", "")
    return requests.post(
        f"{API_BASE}{path}",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )


def api_delete(path: str) -> requests.Response:
    token = st.session_state.get("token", "")
    return requests.delete(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
