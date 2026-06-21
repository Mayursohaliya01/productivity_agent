"""Premium glassmorphism styles for the login / register screen."""

import streamlit as st

LOGIN_ORBS_HTML = """
<div class="pa-login-scene" aria-hidden="true">
    <div class="pa-orb pa-orb--lg"></div>
    <div class="pa-orb pa-orb--md"></div>
    <div class="pa-orb pa-orb--sm"></div>
</div>
"""

LOGIN_CSS = """
<style>
/* ── Charcoal / slate page background ── */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(160deg, #2c2f33 0%, #23262a 45%, #1e2124 100%) !important;
}

.main .block-container {
    max-width: 420px;
    padding-top: 3rem;
    position: relative;
    z-index: 2;
}

/* ── Decorative golden orbs (fixed behind card) ── */
.pa-login-scene {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    overflow: hidden;
}

.pa-orb {
    position: absolute;
    border-radius: 50%;
    background: radial-gradient(
        circle at 32% 28%,
        #ffe9a0 0%,
        #ffb830 28%,
        #e8871a 55%,
        #b85c10 100%
    );
    box-shadow:
        0 0 50px rgba(255, 175, 50, 0.55),
        0 0 100px rgba(255, 140, 30, 0.25);
    filter: blur(0.5px);
}

.pa-orb--lg {
    width: 200px;
    height: 200px;
    top: calc(50% - 220px);
    right: calc(50% - 240px);
    opacity: 0.92;
}

.pa-orb--md {
    width: 130px;
    height: 130px;
    bottom: calc(50% - 200px);
    left: calc(50% - 260px);
    opacity: 0.85;
}

.pa-orb--sm {
    width: 72px;
    height: 72px;
    top: calc(50% - 280px);
    left: calc(50% - 180px);
    opacity: 0.78;
}

/* ── Title: clean white uppercase ── */
.main h1 {
    color: #ffffff !important;
    text-align: center !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.25rem !important;
    -webkit-text-fill-color: #ffffff !important;
    background: none !important;
    position: relative !important;
    z-index: 2 !important;
}

.main .stCaption,
.main p[data-testid="stCaptionContainer"] {
    color: rgba(255, 255, 255, 0.5) !important;
    text-align: center !important;
}

/* ── Glass card: tabs wrapper ── */
[data-testid="stTabs"] {
    position: relative;
    z-index: 2;
    margin-top: 1.25rem;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-bottom: none !important;
    border-radius: 18px 18px 0 0 !important;
    display: flex !important;
    justify-content: center !important;
    align-items: stretch !important;
    gap: 1rem !important;
    padding: 0.65rem 1.5rem 0 !important;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    max-width: calc(50% - 0.5rem) !important;
    color: rgba(255, 255, 255, 0.5) !important;
    background: transparent !important;
    border-radius: 10px 10px 0 0 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    text-align: center !important;
    padding: 0.7rem 1rem !important;
    margin: 0 !important;
    white-space: nowrap !important;
    justify-content: center !important;
}

[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #ffffff !important;
    background: rgba(255, 255, 255, 0.12) !important;
    box-shadow: inset 0 -2px 0 rgba(255, 185, 80, 0.85) !important;
}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
}

[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    background: rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(15px) !important;
    -webkit-backdrop-filter: blur(15px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-top: none !important;
    border-radius: 0 0 20px 20px !important;
    padding: 1.75rem 1.75rem 2rem !important;
    box-shadow:
        0 20px 55px rgba(0, 0, 0, 0.38),
        inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
}

/* Form inside glass panel — no double card */
[data-testid="stTabs"] [data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    padding: 0 !important;
    border-radius: 0 !important;
}

/* ── Minimal underline inputs ── */
[data-testid="stForm"] [data-testid="stTextInput"] > div > div,
[data-testid="stForm"] [data-testid="stPasswordInput"] > div > div,
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"],
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.42) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input,
[data-testid="stForm"] [data-testid="stPasswordInput"] input {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    color: rgba(255, 255, 255, 0.92) !important;
    padding: 0.55rem 0 !important;
    box-shadow: none !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input::placeholder,
[data-testid="stForm"] [data-testid="stPasswordInput"] input::placeholder {
    color: rgba(255, 255, 255, 0.38) !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input:focus,
[data-testid="stForm"] [data-testid="stPasswordInput"] input:focus {
    outline: none !important;
    box-shadow: none !important;
}

[data-testid="stForm"] [data-testid="stTextInput"]:focus-within > div > div,
[data-testid="stForm"] [data-testid="stPasswordInput"]:focus-within > div > div,
[data-testid="stForm"] [data-testid="stPasswordInput"]:focus-within [data-baseweb="input"],
[data-testid="stForm"] [data-testid="stPasswordInput"]:focus-within [data-baseweb="input"] > div {
    border-bottom-color: rgba(255, 190, 90, 0.85) !important;
}

/* Hide only the form hint — NOT labels */
[data-testid="stForm"] [data-testid="InputInstructions"] {
    display: none !important;
}

/* Field labels — must stay visible */
[data-testid="stForm"] [data-testid="stTextInput"] label,
[data-testid="stForm"] [data-testid="stPasswordInput"] label,
[data-testid="stForm"] [data-testid="stTextInput"] [data-testid="stWidgetLabel"],
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-testid="stWidgetLabel"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    color: rgba(255, 255, 255, 0.7) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    margin-bottom: 0.35rem !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] [data-testid="stWidgetLabel"] p,
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-testid="stWidgetLabel"] p {
    display: block !important;
    visibility: visible !important;
    color: rgba(255, 255, 255, 0.7) !important;
    margin: 0 !important;
}

/* ── Password eye icon (flex-aligned, no dark box) ── */
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] > div {
    display: flex !important;
    align-items: center !important;
    gap: 0.25rem !important;
    min-height: 2.4rem !important;
    padding: 0 !important;
}

[data-testid="stForm"] [data-testid="stPasswordInput"] input {
    flex: 1 1 auto !important;
    padding-right: 0.25rem !important;
    min-width: 0 !important;
}

[data-testid="stForm"] [data-testid="stPasswordInput"] button,
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] button,
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-testid="stPasswordInputToggle"] {
    position: static !important;
    transform: none !important;
    flex-shrink: 0 !important;
    align-self: center !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 0.2rem !important;
    margin: 0 0 0 0.25rem !important;
    min-height: 0 !important;
    height: 1.75rem !important;
    width: 1.75rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: rgba(255, 200, 120, 0.85) !important;
    cursor: pointer !important;
}

[data-testid="stForm"] [data-testid="stPasswordInput"] button:hover,
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] button:hover {
    color: #ffbf66 !important;
    background: rgba(255, 160, 60, 0.12) !important;
    border-radius: 6px !important;
}

/* Remove dark wrapper around toggle icon only */
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] > div > div:has(button),
[data-testid="stForm"] [data-testid="stPasswordInput"] [data-baseweb="input"] button span {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── Sign-in button: dark minimal block ── */
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
    background: #2a2d32 !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-size: 0.82rem !important;
    padding: 0.7rem 1rem !important;
    margin-top: 0.75rem !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
    transition: background 0.2s, box-shadow 0.2s !important;
}

[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
    background: #35393f !important;
    border-color: rgba(255, 190, 90, 0.35) !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.38) !important;
}

/* ── Demo banner ── */
[data-testid="stAlert"] {
    background: rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255, 200, 100, 0.3) !important;
    border-radius: 12px !important;
    color: rgba(255, 220, 170, 0.9) !important;
    position: relative;
    z-index: 2;
}
</style>
"""


def inject_login_styles():
    st.markdown(LOGIN_ORBS_HTML, unsafe_allow_html=True)
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
