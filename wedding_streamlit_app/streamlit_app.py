import streamlit as st
import pandas as pd
from dataclasses import dataclass
from datetime import date, datetime
import secrets
import string
import pathlib

# ============================================================
# IMPORTANT PATH FIX (for Streamlit Cloud + subfolders)
# This makes file loading work even when the app is in a folder
# like /wedding_streamlit_app/ inside your GitHub repo.
# ============================================================
BASE_DIR = pathlib.Path(__file__).resolve().parent
GUESTS_PATH = BASE_DIR / "guests.csv"
ASSETS_DIR = BASE_DIR / "assets"

# Local CSV storage (OK for testing; not reliable long-term on Streamlit Cloud)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

RSVP_PATH = DATA_DIR / "rsvps.csv"
PLEDGE_PATH = DATA_DIR / "pledges.csv"

# ----------------------------
# CONFIG (edit these)
# ----------------------------
WEDDING_DATE = date(2026, 5, 30)
RSVP_DEADLINE = date(2026, 4, 15)

VENUE_NAME = "Sugar Baron Distillery"
VENUE_MAP_LINK = "https://share.google/eDwOEY9LEIYKsZOR3"
START_TIME_TEXT = "14:30 for 15:00 (till late)"
DRESS_CODE = "Garden party"
ACCOMMODATION_NOTE = "The Oaks Hotel is a recommended option for accommodation."

COUPLE_NAMES = "Damian & Megan"

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

TOKENS = [
    {"key": "fuel", "label": "Fuel for the Long Haul ⛽", "default_amount": 500, "min_amount": 0, "max_amount": 500, "help": "Help us survive the long stretches."},
    {"key": "nest", "label": "A Night’s Nest 🛏️", "default_amount": 1300, "min_amount": 0, "max_amount": 1300, "help": "A cosy stop somewhere on the route."},
    {"key": "datenight", "label": "Date Night 🍷", "default_amount": 700, "min_amount": 0, "max_amount": 700, "help": "Dinner somewhere special."},
    {"key": "experience", "label": "Experience Token 🌄", "default_amount": 1500, "min_amount": 0, "max_amount": 1500, "help": "An activity, a tour, a tasting, a view."},
    {"key": "padkos", "label": "Padkos & Coffee ☕🥪", "default_amount": 150, "min_amount": 0, "max_amount": 150, "help": "Roadtrip fuel (the snack kind)."},
    {"key": "detour", "label": "Detour Token 🗺️", "default_amount": 0, "min_amount": 0, "max_amount": 2500, "help": "Name the detour. Set the amount. Cause chaos (nicely)."},
]

# ----------------------------
# Storage helpers
# ----------------------------
def _append_row(path: pathlib.Path, row: dict):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, mode="w", header=True, index=False)

def load_guests() -> pd.DataFrame:
    if not GUESTS_PATH.exists():
        st.error("Setup issue: guests.csv not found.")
        st.info("Fix: ensure guests.csv is committed to GitHub in the SAME folder as streamlit_app.py.")
        st.caption(f"Expected path: {GUESTS_PATH}")
        st.stop()
    return pd.read_csv(GUESTS_PATH, dtype={"invite_code": str})

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def make_ref(prefix="DMHM") -> str:
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{prefix}-{token}"

# ----------------------------
# Helpers
# ----------------------------
@dataclass
class Guest:
    invite_code: str
    party_label: str
    party_size_min: int
    party_size_max: int
    plus_one_allowed: bool
    notes: str

def get_guest_by_code(code: str) -> Guest | None:
    guests = load_guests()
    row = guests.loc[guests["invite_code"] == code]
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

def rsvp_open() -> bool:
    return date.today() <= RSVP_DEADLINE

def page_header(guest: Guest | None):
    st.markdown(
        f"""
        <div style="padding: 14px 16px; border: 1px solid rgba(0,0,0,.08); border-radius: 14px;">
            <div style="font-size: 14px; opacity:.8;">You're invited to</div>
            <div style="font-size: 28px; font-weight: 700; margin-top: 2px;">{COUPLE_NAMES}</div>
            <div style="margin-top: 6px; font-size: 14px;">
                <b>{WEDDING_DATE.strftime('%d %B %Y')}</b> • {VENUE_NAME} • {START_TIME_TEXT}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if guest:
        st.write("")
        st.success(f"Hello **{guest.party_label}** ✨")

def require_code() -> str:
    qp = st.query_params
    code = (qp.get("code", "") or "").strip().upper()
    if code:
        return code

    st.info("Paste your invite code to continue 👇")
    code = st.text_input("Invite code", placeholder="e.g., AB12CD34").strip().upper()

    # If no code entered yet, stop here so we don't show an error prematurely.
    if not code:
        st.stop()

    return code

# ----------------------------
# Pages
# ----------------------------
def page_rsvp(guest: Guest):
    st.subheader("RSVP (the cheeky version)")

    with st.expander("See the vibe we’re going for (inspiration)"):
        img_path = ASSETS_DIR / "inspiration.png"
        if img_path.exists():
            st.image(str(img_path), caption="Flow-chart energy ✅", use_container_width=True)
        else:
            st.caption("Add an inspiration image at assets/inspiration.png")

    st.write("**Question:** Are you free on the day? 😌")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Yes, obviously 🥂", use_container_width=True):
            st.session_state["picked"] = True
    with col2:
        if st.button("No (but I’ll regret it) 😅", use_container_width=True):
            st.session_state["picked"] = True
    with col3:
        if st.button("Maybe (I love drama) 🙃", use_container_width=True):
            st.session_state["picked"] = True

    if st.session_state.get("picked", False):
        st.success("Correct answer. We accept. 😌")
        st.write("Now for the *actual* RSVP…")

    st.write("---")

    if not rsvp_open():
        st.warning(f"RSVPs closed on {RSVP_DEADLINE.strftime('%d %B %Y')}. If you’re late, message us directly — we’ll try our best.")
        st.info("You can still leave a message and/or sponsor a honeymoon moment in the sidebar.")
        return

    with st.form("rsvp_form", clear_on_submit=False):
        attending = st.radio("Will you be joining us?", ["Yes 🎉", "No 😢"], horizontal=True)

        if guest.party_size_min == guest.party_size_max:
            st.caption(f"Seats reserved for you: **{guest.party_size_max}**")
            attendee_count = guest.party_size_max
        else:
            attendee_count = st.selectbox(
                "How many of you will attend?",
                options=list(range(guest.party_size_min, guest.party_size_max + 1)),
                index=0,
                help="If you’re bringing a +1 (where allowed), choose 2.",
            )

        dietary = st.text_area("Dietary requirements (if any)", placeholder="e.g., vegetarian, halaal, kosher, etc.", height=90)
        allergies = st.text_area("Allergies (if any)", placeholder="e.g., nuts, shellfish, etc.", height=90)
        song = st.text_input("Song request (optional)", placeholder="One song that will get you on the dance floor…")
        message = st.text_area("Message to the couple (optional)", placeholder="Anything you want to tell us 😊", height=110)

        submitted = st.form_submit_button("Submit RSVP ✅", use_container_width=True)

    if submitted:
        row = {
            "timestamp": now_iso(),
            "invite_code": guest.invite_code,
            "party_label": guest.party_label,
            "attending": attending,
            "attendee_count": int(attendee_count),
            "dietary": dietary.strip(),
            "allergies": allergies.strip(),
            "song_request": song.strip(),
            "message": message.strip(),
        }
        _append_row(RSVP_PATH, row)
        st.balloons()
        st.success("RSVP received! Thank you ❤️")
        st.info("You can also sponsor a honeymoon moment from the sidebar (optional).")

def page_info():
    st.subheader("Wedding Details")
    st.write(f"**When:** {WEDDING_DATE.strftime('%A, %d %B %Y')}")
    st.write(f"**Time:** {START_TIME_TEXT}")
    st.write(f"**Where:** {VENUE_NAME}")
    st.link_button("Open map", VENUE_MAP_LINK)
    st.write(f"**Dress code:** {DRESS_CODE}")
    st.write("---")
    st.write("**Accommodation:**")
    st.write(ACCOMMODATION_NOTE)

def page_honeymoon(guest: Guest):
    st.subheader("Honeymoon — Sponsor a Moment")
    st.write(
        "We don’t need traditional gifts (we’ve already built a home together). "
        "If you’d like to spoil us, you can sponsor a little moment on our road trip — "
        "fuel, a stay, a date night, or a detour — and leave a suggestion along the way."
    )

    st.write("**Route (rough plan):** Howick → Clarens/Fouriesburg → Kimberley → Upington/Augrabies → West Coast → Oudtshoorn/George → Grahamstown → home-ish")
    st.write("---")

    token_label_to_obj = {t["label"]: t for t in TOKENS}
    token_choice = st.selectbox("Pick a token", options=[t["label"] for t in TOKENS])
    token = token_label_to_obj[token_choice]

    if token["key"] == "detour":
        amount = st.number_input("Choose an amount (R0–R2500)", min_value=token["min_amount"], max_value=token["max_amount"], value=0, step=50)
    else:
        amount = st.number_input("Amount (optional)", min_value=0, max_value=token["max_amount"], value=token["default_amount"], step=50, help="You can adjust this if you want.")

    area = st.selectbox("Which area should this apply to?", options=ROUTE_AREAS)

    suggestion = st.text_area(
        "Suggestion (optional)",
        placeholder="A place to stay, a restaurant, a viewpoint, a hidden gem…",
        height=120
    )

    want_update = st.checkbox("Send me a pic when you use my token 📸", value=True)

    if st.button("Generate my reference code →", use_container_width=True):
        ref = make_ref()
        st.session_state["last_ref"] = ref

        pledge_row = {
            "timestamp": now_iso(),
            "invite_code": guest.invite_code,
            "party_label": guest.party_label,
            "token": token["label"],
            "amount": int(amount),
            "area": area,
            "suggestion": suggestion.strip(),
            "wants_update": bool(want_update),
            "reference_code": ref,
            "paid": False,  # admin can mark later
        }
        _append_row(PLEDGE_PATH, pledge_row)

        st.success("Done! Here’s your EFT reference code:")
        st.code(ref)

        st.info(
            "EFT details will be shown here once added. For now, please use the EFT details from your invite message and paste the reference code above."
        )

def page_admin():
    st.subheader("Admin Dashboard")
    st.caption("Password required.")

    try:
        admin_pw = st.secrets.get("ADMIN_PASSWORD", None)
    except Exception:
        admin_pw = None

    if not admin_pw:
        st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        st.caption("Add ADMIN_PASSWORD in Streamlit Cloud → App settings → Secrets.")
        st.stop()

    pw = st.text_input("Admin password", type="password")
    if pw != admin_pw:
        st.stop()

    st.success("Welcome, admin ✅")

    st.write("### RSVPs")
    if RSVP_PATH.exists():
        rsvps = pd.read_csv(RSVP_PATH)
        st.dataframe(rsvps, use_container_width=True, hide_index=True)

        yes = rsvps[rsvps["attending"].str.contains("Yes", na=False)]
        no = rsvps[rsvps["attending"].str.contains("No", na=False)]
        headcount = int(yes["attendee_count"].sum()) if not yes.empty else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Yes RSVPs", len(yes))
        c2.metric("No RSVPs", len(no))
        c3.metric("Headcount (Yes)", headcount)

        st.download_button(
            "Download RSVPs CSV",
            data=rsvps.to_csv(index=False).encode("utf-8"),
            file_name="rsvps.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No RSVPs yet.")

    st.write("---")

    st.write("### Honeymoon Tokens / Pledges")
    if PLEDGE_PATH.exists():
        pledges = pd.read_csv(PLEDGE_PATH)
        st.dataframe(pledges, use_container_width=True, hide_index=True)

        totals = pledges.groupby("token")["amount"].sum().reset_index().sort_values("amount", ascending=False)
        st.write("**Totals by token**")
        st.dataframe(totals, use_container_width=True, hide_index=True)

        st.download_button(
            "Download Pledges CSV",
            data=pledges.to_csv(index=False).encode("utf-8"),
            file_name="pledges.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No pledges yet.")

# ----------------------------
# Main
# ----------------------------
st.set_page_config(page_title="Damian & Megan — Wedding Invite", page_icon="💍", layout="centered")

code = require_code()
guest = get_guest_by_code(code)

if not guest:
    st.error("That invite code doesn’t look right 😅")
    st.caption("Tip: codes are 8 characters (letters/numbers).")
    st.stop()

page_header(guest)

st.sidebar.title("Menu")
page = st.sidebar.radio("Go to", ["RSVP", "Wedding Details", "Honeymoon", "Admin"], index=0)

if page == "RSVP":
    page_rsvp(guest)
elif page == "Wedding Details":
    page_info()
elif page == "Honeymoon":
    page_honeymoon(guest)
elif page == "Admin":
    page_admin()
