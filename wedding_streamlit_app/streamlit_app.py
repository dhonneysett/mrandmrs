import base64
import io
import pathlib
import secrets
import string
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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
# Bank details (shown to guests)
# =========================
BANK_NAME = "Standard Bank"
BANK_ACCOUNT_TYPE = "Savings Account"
BANK_ACCOUNT_NUMBER_PRETTY = "10 10 225 247 3"
BANK_UNIVERSAL_CODE = "051001"
BANK_REFERENCE_NOTE = "Use the generated reference code"

# =========================
# Honeymoon tokens
# (Images optional – you said you aren’t using them now, so we keep emoji tiles)
# =========================
TOKENS = [
    {"key": "fuel", "label": "Fuel for the Long Haul ⛽", "default_amount": 500, "max_amount": 500,
     "desc": "For the long stretches when the tank (and patience) runs low."},
    {"key": "nest", "label": "A Night’s Nest 🛏️", "default_amount": 1300, "max_amount": 1300,
     "desc": "A comfy stop along the route — we’ll pick the date that fits."},
    {"key": "datenight", "label": "Date Night 🍷", "default_amount": 700, "max_amount": 700,
     "desc": "Dinner somewhere special (bonus points for views)."},
    {"key": "experience", "label": "Experience Token 🌄", "default_amount": 1500, "max_amount": 1500,
     "desc": "A tour, a tasting, a hike, a ‘wow’ moment."},
    {"key": "padkos", "label": "Padkos & Coffee ☕🥪", "default_amount": 150, "max_amount": 150,
     "desc": "Roadtrip essentials: snacks and caffeine."},
    {"key": "detour", "label": "Detour Token 🗺️", "default_amount": 0, "max_amount": 2500,
     "desc": "Name the detour. Set the amount. Cause chaos (nicely)."},
]

# =========================
# Secrets (not visible to guests)
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
# Styling / background
# =========================
def load_css():
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def _pick_background() -> Optional[pathlib.Path]:
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

def tile_box_start():
    st.markdown("<div class='dm-tile'>", unsafe_allow_html=True)

def tile_box_end():
    st.markdown("</div>", unsafe_allow_html=True)

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

def storage_badge():
    if STORAGE_MODE == "apps_script":
        st.caption("Storage: Google Sheets ✅")
    else:
        st.caption("Storage: Local CSV (testing mode) ⚠️")

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
# Storage: CSV + Apps Script
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
        headers={"Content-Type": "application/json"},
        json={"token": APPS_SCRIPT_TOKEN, "action": action, "payload": payload},
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) else {"ok": False, "error": "bad_response"}

def store_rsvp(row: Dict[str, Any]):
    if STORAGE_MODE == "apps_script":
        res = _apps_post("append_rsvp", row)
        if not res.get("ok"):
            raise RuntimeError(res.get("error", "unknown_error"))
    else:
        _append_row_csv(RSVP_PATH, row)

def store_pledge(row: Dict[str, Any]):
    if STORAGE_MODE == "apps_script":
        res = _apps_post("append_pledge", row)
        if not res.get("ok"):
            raise RuntimeError(res.get("error", "unknown_error"))
    else:
        _append_row_csv(PLEDGE_PATH, row)

@st.cache_data(show_spinner=False, ttl=20)
def read_rsvps() -> pd.DataFrame:
    if STORAGE_MODE == "apps_script":
        res = _apps_post("get_rsvps", {})
        return pd.DataFrame(res.get("rows", []))
    return pd.read_csv(RSVP_PATH) if RSVP_PATH.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=20)
def read_pledges() -> pd.DataFrame:
    if STORAGE_MODE == "apps_script":
        res = _apps_post("get_pledges", {})
        return pd.DataFrame(res.get("rows", []))
    return pd.read_csv(PLEDGE_PATH) if PLEDGE_PATH.exists() else pd.DataFrame()

# =========================
# PDF invoice
# =========================
def build_invoice_pdf(guest_label: str, reference: str, cart_items: List[Dict[str, Any]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setTitle("Honeymoon Sponsorship")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 60, "Honneymoon Sponsorship Invoice (Fun Edition)")

    c.setFont("Helvetica", 11)
    c.drawString(50, h - 85, f"For: {guest_label}")
    c.drawString(50, h - 102, f"Date: {datetime.now().strftime('%d %b %Y %H:%M')}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, h - 124, f"Reference: {reference}")

    y = h - 160
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Item")
    c.drawString(340, y, "Area")
    c.drawRightString(560, y, "Amount (ZAR)")
    y -= 10
    c.line(50, y, 560, y)
    y -= 18

    total = 0
    c.setFont("Helvetica", 10)
    for item in cart_items:
        label = str(item.get("token_label", ""))[:44]
        area = str(item.get("area", ""))[:18]
        amt = int(item.get("amount", 0))
        total += amt

        c.drawString(50, y, label)
        c.drawString(340, y, area)
        c.drawRightString(560, y, f"R {amt:,}".replace(",", " "))
        y -= 16
        if y < 140:
            c.showPage()
            y = h - 80
            c.setFont("Helvetica", 10)

    y -= 8
    c.line(50, y, 560, y)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(560, y, f"Total: R {total:,}".replace(",", " "))

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "EFT details")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Bank: {BANK_NAME}")
    y -= 14
    c.drawString(50, y, f"Account type: {BANK_ACCOUNT_TYPE}")
    y -= 14
    c.drawString(50, y, f"Account number: {BANK_ACCOUNT_NUMBER_PRETTY}")
    y -= 14
    c.drawString(50, y, f"Universal code: {BANK_UNIVERSAL_CODE}")
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, f"Reference: {reference}")
    y -= 24

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, "Thank you 🤍 We’ll send you a pic when we use your sponsored moment (if you asked for one).")

    c.showPage()
    c.save()
    return buf.getvalue()

# =========================
# Navigation helpers
# =========================
def set_page(p: str):
    st.session_state["page"] = p
    st.rerun()

def nav_row(show_admin: bool = True):
    cols = st.columns(4)
    if cols[0].button("RSVP", use_container_width=True):
        set_page("RSVP")
    if cols[1].button("Wedding details", use_container_width=True):
        set_page("Wedding details")
    if cols[2].button("Honneymoon", use_container_width=True):
        set_page("Honneymoon")
    if show_admin:
        if cols[3].button("Admin", use_container_width=True):
            set_page("Admin")

# =========================
# Pages
# =========================
def page_login():
    card(f"""
      <div class="dm-muted">You’ve cracked an invite to the wedding of</div>
      <h2 style="margin:6px 0 4px 0">{COUPLE_NAMES}</h2>
      <div class="dm-muted">Enter your unique code to continue.</div>
    """)
    st.write("")

    prefill = (st.query_params.get("code", "") or "").strip().upper()
    code = st.text_input("Unique invite code", value=prefill, placeholder="e.g., DAMIAN26").strip().upper()

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
        st.session_state["page"] = "RSVP"
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

    # After-submit screen
    if st.session_state.get("rsvp_done", False):
        st.success("RSVP received 🤍")
        st.snow()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='dm-cta'>", unsafe_allow_html=True)
            if st.button("Wedding details →", use_container_width=True):
                st.session_state["rsvp_done"] = False
                set_page("Wedding details")
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            if st.button("Honneymoon →", use_container_width=True):
                st.session_state["rsvp_done"] = False
                set_page("Honneymoon")
            st.markdown("</div>", unsafe_allow_html=True)
        return

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
        # Clear final buttons
        reserved = g.party_size_max if g.party_size_min == g.party_size_max else f"{g.party_size_min}–{g.party_size_max}"
        card(f"<h3 style='margin:0'>Final answer…</h3><div class='dm-muted'>Seats reserved: <b>{reserved}</b> • {RULES_NOTE}</div>")
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
            if st.button("Yes — we’ll be there 🎉", use_container_width=True):
                st.session_state["rsvp_step"] = 4
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='dm-danger'>", unsafe_allow_html=True)
            if st.button("No — sadly can’t make it 😢", use_container_width=True):
                try:
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
                    st.toast("RSVP saved ✅", icon="✅")
                    st.session_state["rsvp_step"] = 0
                    st.session_state["rsvp_done"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save RSVP: {e}")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    if step == 4:
        # Details form
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
        submit = st.button("Confirm RSVP ✅", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submit:
            try:
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
                st.toast("RSVP saved ✅", icon="✅")
                st.session_state["rsvp_step"] = 0
                st.session_state["rsvp_done"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Could not save RSVP: {e}")

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
    st.subheader("Honneymoon registry — sponsor a moment")
    storage_badge()

    st.write(
        "We don’t need traditional gifts (we already live together and have built a home). "
        "If you’d like to spoil us, you can sponsor a little moment on our road trip honeymoon — "
        "and leave a suggestion we’ll try to honour."
    )

    st.write("---")

    st.session_state.setdefault("cart", [])  # list of items
    st.session_state.setdefault("selected_token_key", None)

    # Token tiles
    cols = st.columns(3)
    for i, t in enumerate(TOKENS):
        with cols[i % 3]:
            tile_box_start()
            st.markdown(f"**{t['label']}**")
            st.caption(t["desc"])
            if st.button("Select", key=f"sel_{t['key']}", use_container_width=True):
                st.session_state["selected_token_key"] = t["key"]
                st.toast("Selected ✅", icon="✅")
            tile_box_end()

    token_key = st.session_state.get("selected_token_key")
    st.write("")

    if not token_key:
        st.info("Select a tile above, then add it to your cart.")
        bank_details_card()
        return

    token = next(x for x in TOKENS if x["key"] == token_key)
    st.success(f"Selected: {token['label']}")

    if token["key"] == "detour":
        amount = st.number_input("Amount (R0–R2500)", min_value=0, max_value=token["max_amount"], value=0, step=50)
    else:
        amount = st.number_input("Amount", min_value=0, max_value=token["max_amount"], value=token["default_amount"], step=50)

    area = st.selectbox("Area", ROUTE_AREAS)
    suggestion = st.text_area("Suggestion", height=110, placeholder="A place to stay, restaurant, viewpoint, hidden gem…")
    want_update = st.checkbox("Send me a pic when you use my token 📸", value=True)

    st.markdown("<div class='dm-cta'>", unsafe_allow_html=True)
    add = st.button("Add to cart ➕", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if add:
        st.session_state["cart"].append({
            "token_key": token["key"],
            "token_label": token["label"],
            "amount": int(amount),
            "area": area,
            "suggestion": suggestion.strip(),
            "wants_update": bool(want_update),
        })
        st.toast("Added to cart 🛒", icon="🛒")

    # Cart view
    st.write("---")
    st.subheader("Your cart")
    cart = st.session_state.get("cart", [])

    if not cart:
        st.info("Cart is empty — add a tile above.")
        bank_details_card()
        return

    total = sum(int(x.get("amount", 0)) for x in cart)
    st.caption(f"Total: **R {total:,}**".replace(",", " "))

    # Display cart items with remove buttons
    for idx, item in enumerate(cart):
        with st.container(border=True):
            st.write(f"**{item['token_label']}** — R {item['amount']}")
            st.caption(f"{item['area']}" + (f" • {item['suggestion']}" if item.get("suggestion") else ""))
            rm_cols = st.columns([1, 3])
            with rm_cols[0]:
                if st.button("Remove", key=f"rm_{idx}", use_container_width=True):
                    st.session_state["cart"].pop(idx)
                    st.toast("Removed 🗑️", icon="🗑️")
                    st.rerun()

    st.write("")
    st.markdown("<div class='dm-cta2'>", unsafe_allow_html=True)
    checkout = st.button("Generate reference code + invoice PDF →", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if checkout:
        ref = make_ref()
        # Save each cart line to storage with the SAME reference code
        try:
            for item in cart:
                store_pledge({
                    "timestamp": now_iso(),
                    "invite_code": g.invite_code,
                    "party_label": g.party_label,
                    "token": item["token_label"],
                    "amount": int(item["amount"]),
                    "area": item["area"],
                    "suggestion": item.get("suggestion", ""),
                    "wants_update": bool(item.get("wants_update", True)),
                    "reference_code": ref,
                    "paid": False,
                })
            st.balloons()
            st.snow()
            st.success("Done! Here’s your reference code:")
            st.code(ref)

            # Build invoice PDF
            pdf_bytes = build_invoice_pdf(g.party_label, ref, cart)
            st.download_button(
                "Download invoice PDF",
                data=pdf_bytes,
                file_name=f"honneymoon_invoice_{ref}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            bank_details_card(reference_code=ref)

            # Clear cart after checkout
            st.session_state["cart"] = []
            st.session_state["selected_token_key"] = None

        except Exception as e:
            st.error(f"Could not save to storage: {e}")
            st.info("If you see this, your Google Sheets connection likely needs fixing (Admin → Test connection).")
            bank_details_card()

    else:
        bank_details_card()

def page_admin():
    st.subheader("Admin")
    st.caption(f"Storage mode: **{STORAGE_MODE}**")

    if not ADMIN_PASSWORD:
        st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        st.stop()

    pw = st.text_input("Admin password", type="password")
    if pw != ADMIN_PASSWORD:
        st.stop()

    st.success("Welcome ✅")

    # Connection test
    st.write("### Google Sheets connection test")
    if STORAGE_MODE != "apps_script":
        st.warning("App is not in Google Sheets mode. Add APPS_SCRIPT_URL + APPS_SCRIPT_TOKEN in Streamlit Secrets.")
    else:
        if st.button("Test connection now", use_container_width=True):
            try:
                res = _apps_post("ping", {"ts": now_iso()})
                st.success(f"OK ✅ {res}")
            except Exception as e:
                st.error(f"Connection failed: {e}")
                st.info("Check: /exec URL, token match, access = Anyone, and redeploy Apps Script.")

    st.write("---")
    st.write("### RSVPs")
    rsvps = read_rsvps()
    if not rsvps.empty:
        st.dataframe(rsvps, use_container_width=True, hide_index=True)
    else:
        st.info("No RSVPs yet.")

    st.write("---")
    st.write("### Pledges")
    pledges = read_pledges()
    if not pledges.empty:
        st.dataframe(pledges, use_container_width=True, hide_index=True)
    else:
        st.info("No pledges yet.")

# =========================
# App entry
# =========================
st.set_page_config(page_title=f"{COUPLE_NAMES} — Wedding Invite", page_icon="💍", layout="centered")
load_css()
inject_background()

st.session_state.setdefault("page", "RSVP")

code = st.session_state.get("guest_code")
guest = guest_by_code(code) if code else None

if not guest:
    page_login()
    st.stop()

# Sidebar quick controls
st.sidebar.title("Menu")
st.sidebar.caption(guest.party_label)
st.sidebar.caption(f"RSVP deadline: {RSVP_DEADLINE.strftime('%d %b %Y')}")

if st.sidebar.button("Log out", use_container_width=True):
    for k in ["guest_code", "page", "rsvp_step", "journey", "rsvp_done", "cart", "selected_token_key"]:
        st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

# Header + nav
header_card(guest)
st.write("")
nav_row(show_admin=True)
st.write("")

# Route to page
p = st.session_state.get("page", "RSVP")
if p == "RSVP":
    page_rsvp(guest)
elif p == "Wedding details":
    page_details()
elif p == "Honneymoon":
    page_registry(guest)
else:
    page_admin()
