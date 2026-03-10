import base64
import pathlib
import secrets
import string
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st

# =========================
# Paths
# =========================
BASE_DIR = pathlib.Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
CSS_PATH = ASSETS_DIR / "css" / "style.css"
GUESTS_PATH = BASE_DIR / "guests.csv"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
RSVP_PATH = DATA_DIR / "rsvps.csv"
PLEDGE_PATH = DATA_DIR / "pledges.csv"

# =========================
# Wedding info
# =========================
COUPLE_NAMES = "Damian & Megan"
WEDDING_DATE = date(2026, 5, 30)
RSVP_DEADLINE = date(2026, 4, 15)

VENUE_NAME = "Sugar Baron Craft Distillery"
VENUE_MAP_LINK = "https://share.google/eDwOEY9LEIYKsZOR3"
START_TIME_TEXT = "Guests arrive from 14:30 for a 15:00 ceremony (till late)"
DRESS_CODE = "Garden Party 🌿"
ACCOMMODATION_NOTE = "The Oaks Hotel, Richmond — 033 212 2603"
RULES_NOTE = "No children • No plus ones unless your invite says so"

ROUTE_AREAS = [
    "Howick / KZN (Start)",
    "Clarens / Fouriesburg",
    "Kimberley (via)",
    "Upington / Augrabies",
    "West Coast",
    "Oudtshoorn / George",
    "Grahamstown",
    "Wildcard / Surprise us",
]

# =========================
# Bank details (displayed to guests)
# =========================
BANK_NAME = "Standard Bank"
BANK_ACCOUNT_TYPE = "Savings Account"
BANK_ACCOUNT_NUMBER_PRETTY = "10 10 225 247 3"
BANK_UNIVERSAL_CODE = "051001"
BANK_REFERENCE_NOTE = "Use the generated reference code"

# =========================
# Honeymoon token tiles (images stored in assets/tokens/)
# =========================
TOKENS = [
    {"key":"fuel", "label":"Fuel for the Long Haul ⛽", "default_amount":500, "max_amount":500, "img":"fuel_up.jpeg",
     "desc":"For the long stretches when the tank (and patience) runs low."},
    {"key":"nest", "label":"A Night’s Nest 🛏️", "default_amount":1300, "max_amount":1300, "img":"accommodation.jpeg",
     "desc":"A comfy stop along the route — we’ll pick the date that fits."},
    {"key":"datenight", "label":"Date Night 🍷", "default_amount":700, "max_amount":700, "img":"date_night.jpeg",
     "desc":"Dinner somewhere special (bonus points for views)."},
    {"key":"experience", "label":"Experience Token 🌄", "default_amount":1500, "max_amount":1500, "img":"activity.jpeg",
     "desc":"A tour, a tasting, a hike, a ‘wow’ moment."},
    {"key":"padkos", "label":"Padkos & Coffee ☕🥪", "default_amount":150, "max_amount":150, "img":"coffee_padkos.jpeg",
     "desc":"Roadtrip essentials: snacks and caffeine."},
    {"key":"detour", "label":"Detour Token 🗺️", "default_amount":0, "max_amount":2500, "img":"wild_card.jpeg",
     "desc":"Name the detour. Set the amount. Cause chaos (nicely)."},
]
TOKENS_DIR = ASSETS_DIR / "tokens"

# =========================
# Secrets (NOT visible to guests)
# =========================
def _get_secret(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default

APPS_SCRIPT_URL = _get_secret("APPS_SCRIPT_URL", "").strip()
APPS_SCRIPT_TOKEN = _get_secret("APPS_SCRIPT_TOKEN", "").strip()
ADMIN_PASSWORD = _get_secret("ADMIN_PASSWORD", "").strip()

STORAGE_MODE = "apps_script" if APPS_SCRIPT_URL and APPS_SCRIPT_TOKEN else "local"

# =========================
# Styling
# =========================
def load_css():
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def _pick_background() -> Optional[pathlib.Path]:
    # Upload your new border background here:
    # wedding_streamlit_app/assets/background.png  (recommended)
    candidates = [
        ASSETS_DIR / "background.png",
        ASSETS_DIR / "background.svg",
        ASSETS_DIR / "background.jpg",
        ASSETS_DIR / "background.jpeg",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def inject_background():
    bg = _pick_background()
    if not bg:
        return

    suffix = bg.suffix.lower()
    if suffix == ".svg":
        mime = "svg+xml"
        raw = bg.read_bytes()
    elif suffix == ".png":
        mime = "png"
        raw = bg.read_bytes()
    else:
        mime = "jpeg"
        raw = bg.read_bytes()

    b64 = base64.b64encode(raw).decode("utf-8")
    st.markdown(
        f"""
        <style>
          .stApp {{
            background-image: url("data:image/{mime};base64,{b64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def card(html: str):
    st.markdown(f"<div class='dm-card'>{html}</div>", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def make_ref(prefix: str = "DMHM") -> str:
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{prefix}-{token}"

def rsvp_open() -> bool:
    return date.today() <= RSVP_DEADLINE

# =========================
# Guests
# =========================
@dataclass
class Guest:
    invite_code: str
    party_label: str
    party_size_min: int
    party_size_max: int
    plus_one_allowed: bool
    notes: str

@st.cache_data(show_spinner=False)
def load_guests_df() -> pd.DataFrame:
    if not GUESTS_PATH.exists():
        raise FileNotFoundError(f"guests.csv not found at: {GUESTS_PATH}")
    return pd.read_csv(GUESTS_PATH, dtype={"invite_code": str})

def guest_by_code(code: str) -> Optional[Guest]:
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

# =========================
# Storage
# =========================
def _append_row_csv(path: pathlib.Path, row: Dict[str, Any]):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, mode="w", header=True, index=False)

def _apps_post(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        APPS_SCRIPT_URL,
        json={"token": APPS_SCRIPT_TOKEN, "action": action, "payload": payload},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()

def store_rsvp(row: Dict[str, Any]):
    if STORAGE_MODE == "apps_script":
        _apps_post("append_rsvp", row)
    else:
        _append_row_csv(RSVP_PATH, row)

def store_pledge(row: Dict[str, Any]):
    if STORAGE_MODE == "apps_script":
        _apps_post("append_pledge", row)
    else:
        _append_row_csv(PLEDGE_PATH, row)

@st.cache_data(show_spinner=False, ttl=30)
def read_rsvps() -> pd.DataFrame:
    if STORAGE_MODE == "apps_script":
        data = _apps_post("get_rsvps", {})
        return pd.DataFrame(data.get("rows", []))
    if RSVP_PATH.exists():
        return pd.read_csv(RSVP_PATH)
    return pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=30)
def read_pledges() -> pd.DataFrame:
    if STORAGE_MODE == "apps_script":
        data = _apps_post("get_pledges", {})
        return pd.DataFrame(data.get("rows", []))
    if PLEDGE_PATH.exists():
        return pd.read_csv(PLEDGE_PATH)
    return pd.DataFrame()

def storage_badge():
    if STORAGE_MODE == "apps_script":
        st.caption("Storage: Google Sheets ✅")
    else:
        st.caption("Storage: Local CSV (testing mode) ⚠️")

# =========================
# Pages
# =========================
def page_login():
    st.write("")
    card(f"""
      <div class="dm-muted">You’ve cracked an invite to the wedding of</div>
      <h2 style="margin:6px 0 4px 0">{COUPLE_NAMES}</h2>
      <div class="dm-muted">Enter your unique code to continue.</div>
    """)
    st.write("")

    prefill = (st.query_params.get("code", "") or "").strip().upper()
    code = st.text_input("Unique invite code", value=prefill, placeholder="e.g., Z6YY8JZG").strip().upper()

    st.markdown("<div class='dm-cta'>", unsafe_allow_html=True)
    enter = st.button("Dare to enter 💍", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if enter:
        g = guest_by_code(code)
        if not g:
            st.error("That code doesn’t look right 😅 Try again, or message us if you’re stuck.")
            return
        st.session_state["guest_code"] = g.invite_code
        st.query_params["code"] = g.invite_code
        st.rerun()

    st.caption("Tip: your code is in the WhatsApp message we sent you.")

def header_card(g: Guest):
    reserved = g.party_size_max if g.party_size_min == g.party_size_max else f"{g.party_size_min}–{g.party_size_max}"
    card(f"""
      <div class="dm-muted">Welcome</div>
      <h2 style="margin:6px 0 2px 0">{g.party_label} ✨</h2>
      <div class="dm-muted" style="margin-top:6px">
        <b>{WEDDING_DATE.strftime('%A, %d %B %Y')}</b> • {VENUE_NAME} • {START_TIME_TEXT}
      </div>
      <div class="dm-small" style="margin-top:6px">{RULES_NOTE}</div>
      <div class="dm-small" style="margin-top:6px">Seats reserved: <b>{reserved}</b></div>
    """)

def page_details():
    st.subheader("Wedding details")
    st.write(f"**Date:** {WEDDING_DATE.strftime('%A, %d %B %Y')}")
    st.write(f"**Time:** {START_TIME_TEXT}")
    st.write(f"**Venue:** {VENUE_NAME}")
    st.link_button("Open map 📍", VENUE_MAP_LINK, use_container_width=True)
    st.write(f"**Dress code:** {DRESS_CODE}")
    st.write(f"**Accommodation:** {ACCOMMODATION_NOTE}")
    st.write(f"**Rules:** {RULES_NOTE}")

def page_rsvp(g: Guest):
    st.subheader("RSVP")
    storage_badge()

    if not rsvp_open():
        st.warning(f"RSVPs closed on {RSVP_DEADLINE.strftime('%d %B %Y')}. If you’re late, please message us directly.")
        return

    st.session_state.setdefault("rsvp_step", 0)
    st.session_state.setdefault("journey", [])
    step = st.session_state["rsvp_step"]

    if step == 0:
        card(f"<h3 style='margin:0'>Are you available on {WEDDING_DATE.strftime('%d %B %Y')}?</h3><div class='dm-muted'>Be careful… your answers will be used against you 😌</div>")
        c1, c2, c3 = st.columns(3)
        if c1.button("Yes, of course ✅", use_container_width=True):
            st.session_state["journey"] = ["yes"]
            st.session_state["rsvp_step"] = 3
            st.rerun()
        if c2.button("Maybe… I want to see where this goes 👀", use_container_width=True):
            st.session_state["journey"] = ["maybe"]
            st.session_state["rsvp_step"] = 1
            st.rerun()
        if c3.button("No… but I know I’ll be missing out 😭", use_container_width=True):
            st.session_state["journey"] = ["no"]
            st.session_state["rsvp_step"] = 1
            st.rerun()
        return

    if step == 1:
        card("<h3 style='margin:0'>Quick question… do you like free food and drinks?</h3><div class='dm-muted'>Because we have some news for you.</div>")
        c1, c2 = st.columns(2)
        if c1.button("Yes 😌", use_container_width=True):
            st.session_state["journey"].append("free_food_yes")
            st.session_state["rsvp_step"] = 2
            st.rerun()
        if c2.button("No (liar) 😅", use_container_width=True):
            st.session_state["journey"].append("free_food_no")
            st.session_state["rsvp_step"] = 2
            st.rerun()
        return

    if step == 2:
        card("<h3 style='margin:0'>Are your plans REALLY that important?</h3><div class='dm-muted'>We can pretend they are… but let’s be honest.</div>")
        c1, c2, c3 = st.columns(3)
        if c1.button("Not really 😌", use_container_width=True):
            st.session_state["journey"].append("plans_not_really")
            st.session_state["rsvp_step"] = 3
            st.rerun()
        if c2.button("Kind of…", use_container_width=True):
            st.session_state["journey"].append("plans_kind_of")
            st.session_state["rsvp_step"] = 3
            st.rerun()
        if c3.button("Yes (but I’ll still come) 🤝", use_container_width=True):
            st.session_state["journey"].append("plans_yes_but")
            st.session_state["rsvp_step"] = 3
            st.rerun()
        return

    if step == 3:
        reserved = g.party_size_max if g.party_size_min == g.party_size_max else f"{g.party_size_min}–{g.party_size_max}"
        card(f"<h3 style='margin:0'>Alright, serious now…</h3><div class='dm-muted'>Seats reserved: <b>{reserved}</b> • {RULES_NOTE}</div>")
        attending = st.radio("Confirm your attendance:", ["Yes 🎉", "No 😢"], horizontal=True)

        if "Yes" in attending:
            if g.party_size_min == g.party_size_max:
                attendee_count = g.party_size_max
                st.caption(f"Seats reserved for you: **{attendee_count}**")
            else:
                attendee_count = st.selectbox("How many of you will attend?", list(range(g.party_size_min, g.party_size_max + 1)))

            dietary = st.text_area("Dietary requirements", height=80, placeholder="Vegetarian / halaal / etc.")
            allergies = st.text_area("Allergies", height=80, placeholder="Nuts / shellfish / etc.")
            song = st.text_input("Song request", placeholder="One song that will get you on the dance floor…")
            message = st.text_area("Message to the couple", height=110, placeholder="Anything you want to tell us 😊")

            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            submit = st.button("Submit RSVP ✅", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if submit:
                store_rsvp({
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
                st.success("Thank you ❤️ We’ve received your RSVP.")
                st.session_state["rsvp_step"] = 0
                return
        else:
            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            submit_no = st.button("Submit RSVP (No) ✅", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if submit_no:
                store_rsvp({
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
                st.session_state["rsvp_step"] = 0

def bank_details_card(reference_code: Optional[str] = None):
    ref_line = f"<b>Reference:</b> {reference_code}" if reference_code else f"<b>Reference:</b> {BANK_REFERENCE_NOTE}"
    card(f"""
      <h3 style="margin:0">EFT details</h3>
      <div style="margin-top:10px" class="dm-muted"><b>Bank:</b> {BANK_NAME}</div>
      <div class="dm-muted"><b>Account type:</b> {BANK_ACCOUNT_TYPE}</div>
      <div class="dm-muted"><b>Account number:</b> {BANK_ACCOUNT_NUMBER_PRETTY}</div>
      <div class="dm-muted"><b>Universal code:</b> {BANK_UNIVERSAL_CODE}</div>
      <div style="margin-top:10px" class="dm-muted">{ref_line}</div>
    """)

def page_registry(g: Guest):
    st.subheader("Honeymoon registry — sponsor a moment")
    storage_badge()

    st.write(
        "We don’t need traditional gifts (we already live together and have built a home). "
        "If you’d like to spoil us, you can sponsor a little moment on our road trip honeymoon — "
        "and leave a suggestion we’ll try to honour."
    )

    st.write("---")

    st.session_state.setdefault("token_key", None)
    cols = st.columns(3)

    for i, t in enumerate(TOKENS):
        with cols[i % 3]:
            img_path = TOKENS_DIR / t["img"]
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)
            st.markdown(f"**{t['label']}**")
            st.caption(t["desc"])
            if st.button("Choose", key=f"choose_{t['key']}", use_container_width=True):
                st.session_state["token_key"] = t["key"]

    token_key = st.session_state.get("token_key")
    if not token_key:
        st.info("Choose a tile above to continue.")
        bank_details_card()
        return

    token = next(x for x in TOKENS if x["key"] == token_key)
    st.success(f"Selected: {token['label']}")

    if token["key"] == "detour":
        amount = st.number_input("Amount (R0–R2500)", min_value=0, max_value=token["max_amount"], value=0, step=50)
    else:
        amount = st.number_input("Amount", min_value=0, max_value=token["max_amount"], value=token["default_amount"], step=50)

    area = st.selectbox("Which area should this apply to?", ROUTE_AREAS)
    suggestion = st.text_area("Suggestion (optional)", height=110, placeholder="A place to stay, restaurant, viewpoint, hidden gem…")
    want_update = st.checkbox("Send me a pic when you use my token 📸", value=True)

    st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
    generate = st.button("Generate reference code →", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if generate:
        ref = make_ref()
        store_pledge({
            "timestamp": now_iso(),
            "invite_code": g.invite_code,
            "party_label": g.party_label,
            "token": token["label"],
            "amount": int(amount),
            "area": area,
            "suggestion": suggestion.strip(),
            "wants_update": bool(want_update),
            "reference_code": ref,
            "paid": False,
        })

        st.success("Done! Here’s your reference code:")
        st.code(ref)
        bank_details_card(reference_code=ref)
    else:
        bank_details_card()

def page_admin():
    st.subheader("Admin")
    st.caption(f"Storage mode: {STORAGE_MODE}")

    if not ADMIN_PASSWORD:
        st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        st.stop()

    pw = st.text_input("Admin password", type="password")
    if pw != ADMIN_PASSWORD:
        st.stop()

    st.success("Welcome ✅")

    rsvps = read_rsvps()
    pledges = read_pledges()

    st.write("### RSVPs")
    if not rsvps.empty:
        st.dataframe(rsvps, use_container_width=True, hide_index=True)
        yes = rsvps[rsvps.get("attending", "").astype(str).str.contains("Yes", na=False)]
        headcount = int(pd.to_numeric(yes.get("attendee_count", 0), errors="coerce").fillna(0).sum()) if not yes.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Yes RSVPs", len(yes))
        c2.metric("Total RSVPs", len(rsvps))
        c3.metric("Headcount (Yes)", headcount)
        st.download_button("Download RSVPs CSV", rsvps.to_csv(index=False).encode("utf-8"), "rsvps.csv", "text/csv", use_container_width=True)
    else:
        st.info("No RSVPs yet.")

    st.write("---")
    st.write("### Pledges")
    if not pledges.empty:
        st.dataframe(pledges, use_container_width=True, hide_index=True)
        pledges["amount_num"] = pd.to_numeric(pledges.get("amount", 0), errors="coerce").fillna(0)
        totals = pledges.groupby("token")["amount_num"].sum().reset_index().sort_values("amount_num", ascending=False)
        st.write("**Totals by token**")
        st.dataframe(totals, use_container_width=True, hide_index=True)
        st.download_button("Download Pledges CSV", pledges.drop(columns=["amount_num"], errors="ignore").to_csv(index=False).encode("utf-8"), "pledges.csv", "text/csv", use_container_width=True)
    else:
        st.info("No pledges yet.")

# =========================
# App entry
# =========================
st.set_page_config(page_title=f"{COUPLE_NAMES} — Wedding Invite", page_icon="💍", layout="centered")
load_css()
inject_background()

code = st.session_state.get("guest_code")
guest = guest_by_code(code) if code else None

if not guest:
    page_login()
    st.stop()

st.sidebar.title("Menu")
st.sidebar.caption(guest.party_label)

if st.sidebar.button("Log out", use_container_width=True):
    for k in ["guest_code", "rsvp_step", "journey", "token_key"]:
        st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

page = st.sidebar.radio("Go to", ["RSVP", "Wedding details", "Honeymoon registry", "Admin"], index=0)

header_card(guest)
st.write("")

if page == "RSVP":
    page_rsvp(guest)
elif page == "Wedding details":
    page_details()
elif page == "Honeymoon registry":
    page_registry(guest)
else:
    page_admin()
