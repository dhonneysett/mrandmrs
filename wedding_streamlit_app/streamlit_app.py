import streamlit as st
import pandas as pd
import pathlib
import base64
from dataclasses import dataclass
from datetime import date, datetime
import secrets
import string

BASE_DIR = pathlib.Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
CSS_PATH = ASSETS_DIR / "css" / "style.css"
WELCOME_BG = ASSETS_DIR / "welcome_bg.png"
GUESTS_PATH = BASE_DIR / "guests.csv"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
RSVP_PATH = DATA_DIR / "rsvps.csv"

COUPLE_NAMES = "Damian & Megan"
WEDDING_DATE = date(2026, 5, 30)
RSVP_DEADLINE = date(2026, 4, 15)

def load_css():
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def set_bg_image(img_path: pathlib.Path | None):
    if img_path is None or not img_path.exists():
        return
    b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
          .stApp {{
            background-image: url("data:image/png;base64,{b64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def card(html: str):
    st.markdown(f"<div class='dm-card'>{html}</div>", unsafe_allow_html=True)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def append_row(path: pathlib.Path, row: dict):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, mode="w", header=True, index=False)

@dataclass
class Guest:
    invite_code: str
    party_label: str
    party_size_min: int
    party_size_max: int
    plus_one_allowed: bool
    notes: str

def load_guests_df() -> pd.DataFrame:
    if not GUESTS_PATH.exists():
        st.error("Setup issue: guests.csv not found in the app folder.")
        st.caption(f"Expected: {GUESTS_PATH}")
        st.stop()
    return pd.read_csv(GUESTS_PATH, dtype={"invite_code": str})

def guest_by_code(code: str) -> Guest | None:
    df = load_guests_df()
    row = df.loc[df["invite_code"] == code]
    if row.empty:
        return None
    r = row.iloc[0].to_dict()
    return Guest(
        invite_code=str(r["invite_code"]),
        party_label=str(r["party_label"]),
        party_size_min=int(r["party_size_min"]),
        party_size_max=int(r["party_size_max"]),
        plus_one_allowed=bool(r["plus_one_allowed"]),
        notes=str(r.get("notes", "")),
    )

def page_welcome():
    set_bg_image(WELCOME_BG)
    st.write("")
    card(f"""
      <div class='dm-muted'>You’ve cracked an invite to the wedding of</div>
      <h2 style='margin:6px 0 2px 0'>{COUPLE_NAMES}</h2>
      <div class='dm-muted'>Enter your unique code below to continue ✨</div>
    """)
    st.write("")
    code_prefill = (st.query_params.get("code", "") or "").strip().upper()
    code = st.text_input("Unique invite code", value=code_prefill, placeholder="e.g., CARLO").strip().upper()
    st.write("")
    st.markdown("<div class='dm-cta'>", unsafe_allow_html=True)
    if st.button("Dare to enter 💍", use_container_width=True):
        g = guest_by_code(code)
        if not g:
            st.error("That code doesn’t look right 😅 Try again, or message us.")
            st.stop()
        st.session_state["guest_code"] = g.invite_code
        st.query_params["code"] = g.invite_code
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def page_details():
    st.subheader("Wedding details")
    st.write(f"**Date:** {WEDDING_DATE.strftime('%A, %d %B %Y')}")
    st.write("**Time:** Guests arrive from 14:30 for a 15:00 ceremony (till late)")
    st.write("**Venue:** Sugar Baron Craft Distillery (Richmond)")
    st.link_button("Open map 📍", "https://share.google/eDwOEY9LEIYKsZOR3", use_container_width=True)
    st.write("**Dress code:** Garden Party 🌿")
    st.write("**Accommodation:** The Oaks Hotel (033 212 2603)")

def page_rsvp(g: Guest):
    card(f"<div class='dm-muted'>Welcome</div><h2 style='margin:6px 0 0 0'>{g.party_label} ✨</h2>")
    if date.today() > RSVP_DEADLINE:
        st.warning("RSVPs are closed. Message us directly if you're late — we'll try make a plan.")
        return

    st.write("")
    st.subheader("Are you available on 30 May 2026?")
    c1, c2, c3 = st.columns(3)
    if c1.button("Yes, of course ✅", use_container_width=True):
        st.session_state["journey"] = ["yes"]
        st.session_state["step"] = "confirm"
        st.rerun()
    if c2.button("Maybe… I want to see where this goes 👀", use_container_width=True):
        st.session_state["journey"] = ["maybe"]
        st.session_state["step"] = "fun1"
        st.rerun()
    if c3.button("No… but I know I’ll be missing out 😭", use_container_width=True):
        st.session_state["journey"] = ["no"]
        st.session_state["step"] = "fun1"
        st.rerun()

    step = st.session_state.get("step")
    if not step:
        return

    st.write("---")

    if step == "fun1":
        card("<h3 style='margin:0'>Quick question… do you like free food and drinks?</h3><div class='dm-muted'>Because we have some news for you.</div>")
        c1, c2 = st.columns(2)
        if c1.button("Yes 😌", use_container_width=True):
            st.session_state["journey"].append("free_food_yes")
            st.session_state["step"] = "confirm"
            st.rerun()
        if c2.button("No (liar) 😅", use_container_width=True):
            st.session_state["journey"].append("free_food_no")
            st.session_state["step"] = "confirm"
            st.rerun()

    if step == "confirm":
        reserved = g.party_size_max if g.party_size_min == g.party_size_max else f"{g.party_size_min}–{g.party_size_max}"
        card(f"<h3 style='margin:0'>Alright, serious now…</h3><div class='dm-muted'>Seats reserved for you: <b>{reserved}</b></div>")
        attending = st.radio("Confirm your attendance:", ["Yes 🎉", "No 😢"], horizontal=True)

        if "Yes" in attending:
            if g.party_size_min == g.party_size_max:
                attendee_count = g.party_size_max
                st.caption(f"Seats reserved: **{attendee_count}**")
            else:
                attendee_count = st.selectbox("How many of you will attend?", list(range(g.party_size_min, g.party_size_max + 1)))
            dietary = st.text_area("Dietary requirements (if any)", height=70)
            allergies = st.text_area("Allergies (if any)", height=70)
            song = st.text_input("Song request (optional)")
            message = st.text_area("Message to the couple (optional)", height=90)
            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            if st.button("Submit RSVP ✅", use_container_width=True):
                append_row(RSVP_PATH, {
                    "timestamp": now_iso(),
                    "invite_code": g.invite_code,
                    "party_label": g.party_label,
                    "attending": "Yes",
                    "attendee_count": int(attendee_count),
                    "dietary": dietary.strip(),
                    "allergies": allergies.strip(),
                    "song_request": song.strip(),
                    "message": message.strip(),
                    "journey": "|".join(st.session_state.get("journey", [])),
                })
                st.balloons()
                st.success("RSVP received ❤️")
                st.session_state.pop("step", None)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            if st.button("Submit RSVP (No) ✅", use_container_width=True):
                append_row(RSVP_PATH, {
                    "timestamp": now_iso(),
                    "invite_code": g.invite_code,
                    "party_label": g.party_label,
                    "attending": "No",
                    "attendee_count": 0,
                    "dietary": "",
                    "allergies": "",
                    "song_request": "",
                    "message": "",
                    "journey": "|".join(st.session_state.get("journey", [])),
                })
                st.success("Noted — we’ll miss you 😢")
                st.session_state.pop("step", None)
            st.markdown("</div>", unsafe_allow_html=True)

st.set_page_config(page_title="Damian & Megan — Invite", page_icon="💍", layout="centered")
load_css()

code = st.session_state.get("guest_code")
guest = guest_by_code(code) if code else None

if not guest:
    page_welcome()
    st.stop()

st.sidebar.title("Menu")
if st.sidebar.button("Log out", use_container_width=True):
    for k in ["guest_code", "step", "journey"]:
        st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

page = st.sidebar.radio("Go to", ["RSVP", "Wedding Details"], index=0)

if page == "RSVP":
    page_rsvp(guest)
else:
    page_details()
