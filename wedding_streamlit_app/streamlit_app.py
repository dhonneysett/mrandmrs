import streamlit as st
import pandas as pd
from dataclasses import dataclass
from datetime import date, datetime
import secrets
import string
import pathlib
import time
import math

# ============================================================
# PATHS (robust for Streamlit Cloud + subfolder deployment)
# ============================================================
BASE_DIR = pathlib.Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
TOKENS_DIR = ASSETS_DIR / "tokens"
GUESTS_PATH = BASE_DIR / "guests.csv"

# Local CSV storage (OK for testing; not reliable long-term on Streamlit Cloud)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
RSVP_PATH = DATA_DIR / "rsvps.csv"
PLEDGE_PATH = DATA_DIR / "pledges.csv"

# ============================================================
# WEDDING CONFIG
# ============================================================
COUPLE_NAMES = "Damian & Megan"
WEDDING_DATE = date(2026, 5, 30)
RSVP_DEADLINE = date(2026, 4, 15)

VENUE_NAME = "Sugar Baron Craft Distillery"
VENUE_MAP_LINK = "https://share.google/eDwOEY9LEIYKsZOR3"
START_TIME_TEXT = "Guests arrive from 14:30 for a 15:00 ceremony (till late)"
DRESS_CODE = "Garden Party 🌿"
ACCOMMODATION_NOTE = "For guests travelling, we recommend The Oaks Hotel in Richmond (033 212 2603)."

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

# ============================================================
# HONEYMOON TOKENS (with your custom images)
# Put these images in: wedding_streamlit_app/assets/tokens/
# Expected filenames (recommended):
# - fuel_up.jpeg
# - accommodation.jpeg
# - date_night.jpeg
# - activity.jpeg
# - coffee_padkos.jpeg
# - wild_card.jpeg
# (or change the img field below)
# ============================================================
TOKENS = [
    {"key":"fuel", "label":"Fuel for the Long Haul ⛽", "default_amount":500, "max_amount":500, "img":"fuel_up.jpeg",
     "help":"For the long stretches when the tank (and patience) runs low."},

    {"key":"nest", "label":"A Night’s Nest 🛏️", "default_amount":1300, "max_amount":1300, "img":"accommodation.jpeg",
     "help":"A comfy stop along the route — we’ll pick the date that fits."},

    {"key":"datenight", "label":"Date Night 🍷", "default_amount":700, "max_amount":700, "img":"date_night.jpeg",
     "help":"Dinner somewhere special (bonus points for views)."},

    {"key":"experience", "label":"Experience Token 🌄", "default_amount":1500, "max_amount":1500, "img":"activity.jpeg",
     "help":"A tour, a tasting, a hike, a ‘wow’ moment."},

    {"key":"padkos", "label":"Padkos & Coffee ☕🥪", "default_amount":150, "max_amount":150, "img":"coffee_padkos.jpeg",
     "help":"Roadtrip essentials: snacks and caffeine."},

    {"key":"detour", "label":"Detour Token 🗺️", "default_amount":0, "max_amount":2500, "img":"wild_card.jpeg",
     "help":"Name the detour. Set the amount. Cause chaos (nicely)."},
]

# ============================================================
# UI helpers
# ============================================================
def inject_css():
    st.markdown("""
    <style>
      /* soften page */
      .stApp { background: linear-gradient(180deg, rgba(250,249,247,1) 0%, rgba(255,255,255,1) 45%, rgba(250,249,247,1) 100%); }
      /* make headers nicer */
      h1, h2, h3 { letter-spacing: .3px; }
      /* tighten sidebar */
      [data-testid="stSidebar"] { border-right: 1px solid rgba(0,0,0,.06); }
      /* nicer buttons */
      .stButton>button { border-radius: 14px; padding: .6rem .9rem; }
      /* subtle card */
      .dm-card {
        border: 1px solid rgba(0,0,0,.08);
        border-radius: 18px;
        padding: 14px 16px;
        background: rgba(255,255,255,.9);
        box-shadow: 0 6px 18px rgba(0,0,0,.04);
      }
      .dm-muted { opacity:.75; font-size: 0.95rem; }
      .dm-small { opacity:.75; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def make_ref(prefix="DMHM") -> str:
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{prefix}-{token}"

def safe_image(path: pathlib.Path, caption: str | None = None):
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)

def find_asset(*relative_parts: str) -> pathlib.Path:
    return BASE_DIR.joinpath(*relative_parts)

def rsvp_open() -> bool:
    return date.today() <= RSVP_DEADLINE

# ============================================================
# Data
# ============================================================
def _append_row(path: pathlib.Path, row: dict):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, mode="w", header=True, index=False)

def load_guests() -> pd.DataFrame:
    if not GUESTS_PATH.exists():
        st.error("Setup issue: guests.csv not found.")
        st.caption(f"Expected path: {GUESTS_PATH}")
        st.stop()
    return pd.read_csv(GUESTS_PATH, dtype={"invite_code": str})

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

# ============================================================
# Auth gate / Landing
# ============================================================
def landing_page():
    st.markdown(f"<div class='dm-card'><div class='dm-muted'>You’ve cracked an invite to the wedding of</div><h2 style='margin:6px 0 2px 0'>{COUPLE_NAMES}</h2><div class='dm-muted'>Enter your unique code below to access your invite ✨</div></div>", unsafe_allow_html=True)
    st.write("")

    # Optional: show the floral invite as a hero image if present
    # Recommended filename: assets/invite.png
    safe_image(ASSETS_DIR / "invite.png")

    qp = st.query_params
    prefill = (qp.get("code", "") or "").strip().upper()

    code = st.text_input("Unique invite code", value=prefill, placeholder="e.g., AB12CD34").strip().upper()
    st.caption("Tip: If someone sent you a link, your code might already be filled in.")

    col1, col2 = st.columns([1,1])
    with col1:
        enter = st.button("Dare to enter 💍", use_container_width=True)
    with col2:
        st.button("I’m scared (but I’ll do it anyway) 😅", use_container_width=True, disabled=True)

    if not enter:
        st.stop()

    guest = get_guest_by_code(code)
    if not guest:
        st.error("That code doesn’t look right 😅 Try again, or message us if you’re stuck.")
        st.stop()

    st.session_state["authed_code"] = guest.invite_code
    st.session_state["guest_label"] = guest.party_label
    st.query_params["code"] = guest.invite_code  # keep it in URL for convenience
    st.rerun()

def get_authed_guest() -> Guest:
    code = st.session_state.get("authed_code", "")
    guest = get_guest_by_code(code)
    if not guest:
        # if session expired or guests.csv changed
        st.session_state.pop("authed_code", None)
        st.session_state.pop("guest_label", None)
        st.rerun()
    return guest

# ============================================================
# Pages
# ============================================================
def header_card(guest: Guest):
    st.markdown(
        f"""
        <div class="dm-card">
          <div class="dm-muted">Welcome</div>
          <h2 style="margin:6px 0 0 0;">{guest.party_label} ✨</h2>
          <div class="dm-muted" style="margin-top:6px;">
            <b>{WEDDING_DATE.strftime('%A, %d %B %Y')}</b> • {VENUE_NAME} • {START_TIME_TEXT}
          </div>
          <div class="dm-small" style="margin-top:6px;">{RULES_NOTE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def page_home(guest: Guest):
    header_card(guest)
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Open map 📍", VENUE_MAP_LINK, use_container_width=True)
    with col2:
        st.button("Share this invite", use_container_width=True, disabled=True)
        st.caption("Tip: copy the URL from your browser and send it. It will include your code.")

    st.write("---")
    st.subheader("Quick links")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("RSVP →", use_container_width=True):
            st.session_state["nav_page"] = "RSVP"
            st.rerun()
    with c2:
        if st.button("Honeymoon registry →", use_container_width=True):
            st.session_state["nav_page"] = "Honeymoon"
            st.rerun()

    st.write("---")
    st.subheader("What Megan sent (copy/paste message)")
    st.code(
f"""Well… it’s happening. ✨🤍

After five years together, we are officially getting married — and we would love for you to celebrate with us.

📅 Saturday, 30 May 2026
⏰ Guests arrive from 2:30pm for a 3:00pm ceremony
📍 {VENUE_NAME}
Seafield Farm, R56, Richmond

Please RSVP using the link below before the 15th of April.
(LINK)

If clicking links isn’t really your thing, you’re very welcome to simply reply to this message and let us know if you’ll be joining us — we promise not to make you wrestle with the internet😉

Dress code: Garden Party 🌿
If you match the invitation, you’re probably on the right track.

For guests travelling and looking for accommodation, we can recommend The Oaks Hotel in Richmond.
📞 033 212 2603

We can’t wait to celebrate with you 🤍

Love,
Damian & Megan💕

P.S. Sarge & Ranger have their bow ties sorted and look forward to seeing everyone there. 🐾""",
        language="text"
    )

def page_details():
    st.subheader("Wedding details")
    safe_image(ASSETS_DIR / "invite.png")
    st.write(f"**When:** {WEDDING_DATE.strftime('%A, %d %B %Y')}")
    st.write(f"**Time:** {START_TIME_TEXT}")
    st.write(f"**Where:** {VENUE_NAME}")
    st.link_button("Open map 📍", VENUE_MAP_LINK)
    st.write(f"**Dress code:** {DRESS_CODE}")
    st.write(f"**Rules:** {RULES_NOTE}")
    st.write("---")
    st.write("**Accommodation**")
    st.write(ACCOMMODATION_NOTE)

    # Optional schedule/facts image
    with st.expander("Extra: Fun facts / schedule (optional)"):
        safe_image(ASSETS_DIR / "schedule.png")

def rsvp_wizard(guest: Guest):
    st.subheader("RSVP (the fun version)")

    if not rsvp_open():
        st.warning(f"RSVPs closed on {RSVP_DEADLINE.strftime('%d %B %Y')}. If you’re late, message us directly — we’ll try our best.")
        st.info("You can still view details and the honeymoon registry.")
        return

    # init
    st.session_state.setdefault("rsvp_step", 0)
    st.session_state.setdefault("rsvp_path", None)
    st.session_state.setdefault("rsvp_fun", {})

    step = st.session_state["rsvp_step"]

    # Step 0 — main question
    if step == 0:
        st.markdown(f"<div class='dm-card'><h3 style='margin:0'>Are you available on <b>{WEDDING_DATE.strftime('%d %B %Y')}</b> to attend the wedding of {COUPLE_NAMES}?</h3><div class='dm-muted' style='margin-top:6px'>Be careful… your answers will be used against you 😌</div></div>", unsafe_allow_html=True)
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Yes, of course ✅", use_container_width=True):
                st.session_state["rsvp_path"] = "yes"
                st.session_state["rsvp_step"] = 3
                st.rerun()
        with c2:
            if st.button("Maybe… I want to see where this goes 👀", use_container_width=True):
                st.session_state["rsvp_path"] = "maybe"
                st.session_state["rsvp_step"] = 1
                st.rerun()
        with c3:
            if st.button("No… but I know I’ll be missing out 😭", use_container_width=True):
                st.session_state["rsvp_path"] = "no"
                st.session_state["rsvp_step"] = 1
                st.rerun()
        return

    # Steps 1–2 — fun questions (only for maybe/no path)
    if step == 1:
        st.markdown("<div class='dm-card'><h3 style='margin:0'>Quick question… do you like free food and drinks?</h3><div class='dm-muted' style='margin-top:6px'>Because we have some news for you.</div></div>", unsafe_allow_html=True)
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes 😌", use_container_width=True):
                st.session_state["rsvp_fun"]["free_food"] = "yes"
                st.session_state["rsvp_step"] = 2
                st.rerun()
        with c2:
            if st.button("No (liar) 😅", use_container_width=True):
                st.session_state["rsvp_fun"]["free_food"] = "no"
                st.session_state["rsvp_step"] = 2
                st.rerun()
        return

    if step == 2:
        st.markdown("<div class='dm-card'><h3 style='margin:0'>Are your plans really that important?</h3><div class='dm-muted' style='margin-top:6px'>We can pretend they are… but let’s be honest.</div></div>", unsafe_allow_html=True)
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Not really 😌", use_container_width=True):
                st.session_state["rsvp_fun"]["plans_important"] = "not_really"
                st.session_state["rsvp_step"] = 3
                st.rerun()
        with c2:
            if st.button("Kind of…", use_container_width=True):
                st.session_state["rsvp_fun"]["plans_important"] = "kind_of"
                st.session_state["rsvp_step"] = 3
                st.rerun()
        with c3:
            if st.button("Yes (but I’ll still come) 🤝", use_container_width=True):
                st.session_state["rsvp_fun"]["plans_important"] = "yes_but"
                st.session_state["rsvp_step"] = 3
                st.rerun()
        return

    # Step 3 — real confirmation
    if step == 3:
        reserved = guest.party_size_max if guest.party_size_min == guest.party_size_max else f"{guest.party_size_min}–{guest.party_size_max}"
        st.markdown(
            f"<div class='dm-card'><h3 style='margin:0'>Alright, final answer…</h3>"
            f"<div class='dm-muted' style='margin-top:6px'>Seats reserved for you: <b>{reserved}</b> • {RULES_NOTE}</div></div>",
            unsafe_allow_html=True
        )
        st.write("")
        attending = st.radio("Confirm your attendance:", ["Yes 🎉", "No 😢"], horizontal=True)

        st.caption("If you can’t make it, we totally understand — but we will be dramatic about it for at least 3 business days.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Continue →", use_container_width=True):
                st.session_state["rsvp_confirmed_attending"] = attending
                st.session_state["rsvp_step"] = 4
                st.rerun()
        with c2:
            if st.button("Start over ↩️", use_container_width=True):
                for k in ["rsvp_step","rsvp_path","rsvp_fun","rsvp_confirmed_attending"]:
                    st.session_state.pop(k, None)
                st.rerun()
        return

    # Step 4 — final RSVP details + submit
    if step == 4:
        attending = st.session_state.get("rsvp_confirmed_attending", "Yes 🎉")
        if "Yes" not in attending:
            st.info("We’ll miss you! 😢 If anything changes, message us — we’ll try make a plan.")
            if st.button("Submit RSVP (No) ✅", use_container_width=True):
                row = {
                    "timestamp": now_iso(),
                    "invite_code": guest.invite_code,
                    "party_label": guest.party_label,
                    "attending": "No",
                    "attendee_count": 0,
                    "dietary": "",
                    "allergies": "",
                    "song_request": "",
                    "message": "",
                    "journey_path": st.session_state.get("rsvp_path"),
                    "journey_fun": str(st.session_state.get("rsvp_fun", {})),
                }
                _append_row(RSVP_PATH, row)
                st.session_state["rsvp_step"] = 5
                st.rerun()
            return

        with st.form("rsvp_details_form"):
            # attendee count
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
                "attending": "Yes",
                "attendee_count": int(attendee_count),
                "dietary": dietary.strip(),
                "allergies": allergies.strip(),
                "song_request": song.strip(),
                "message": message.strip(),
                "journey_path": st.session_state.get("rsvp_path"),
                "journey_fun": str(st.session_state.get("rsvp_fun", {})),
            }
            _append_row(RSVP_PATH, row)
            st.session_state["rsvp_step"] = 5
            st.rerun()
        return

    # Step 5 — thank you + registry button
    if step == 5:
        st.balloons()
        st.success("Thank you! Your RSVP has been received ❤️")
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Wedding details →", use_container_width=True):
                st.session_state["nav_page"] = "Details"
                st.rerun()
        with c2:
            if st.button("Honeymoon registry →", use_container_width=True):
                st.session_state["nav_page"] = "Honeymoon"
                st.rerun()

        st.write("---")
        st.markdown("<div class='dm-card'><b>Quick note on gifts</b><br><span class='dm-muted'>We’re lucky — we already live together and have built a home, so we don’t need traditional gifts. If you’d like to spoil us, you can sponsor a small moment on our road trip honeymoon instead.</span></div>", unsafe_allow_html=True)

def honeymoon_tiles(guest: Guest):
    st.subheader("Honeymoon registry — sponsor a moment")
    st.write(
        "We don’t need traditional gifts (we’ve already built a home together). "
        "If you’d like to spoil us, you can sponsor a little moment on our road trip — "
        "fuel, a stay, a date night, or a detour — and leave a suggestion along the way."
    )

    st.write("**Route (rough plan):** Howick → Clarens/Fouriesburg → Kimberley → Upington/Augrabies → West Coast → Oudtshoorn/George → Grahamstown → home-ish")
    st.write("---")

    # Animated tile reveal (once per session)
    st.session_state.setdefault("tiles_shown", False)
    if st.button("Replay tile animation ✨", use_container_width=True):
        st.session_state["tiles_shown"] = False

    selected_key = st.session_state.get("selected_token_key", None)

    ncols = 3
    nrows = math.ceil(len(TOKENS) / ncols)

    placeholders = []
    for r in range(nrows):
        cols = st.columns(ncols)
        for c in range(ncols):
            idx = r * ncols + c
            if idx < len(TOKENS):
                placeholders.append(cols[c].empty())

    def render_tile(t):
        img_path = TOKENS_DIR / t["img"]
        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        st.markdown(f"**{t['label']}**")
        if t.get("help"):
            st.caption(t["help"])
        if st.button("Choose", key=f"choose_{t['key']}", use_container_width=True):
            st.session_state["selected_token_key"] = t["key"]

    if not st.session_state["tiles_shown"]:
        for i, ph in enumerate(placeholders):
            with ph.container():
                with st.container(border=True):
                    render_tile(TOKENS[i])
            time.sleep(0.10)
        st.session_state["tiles_shown"] = True
    else:
        for i, ph in enumerate(placeholders):
            with ph.container():
                with st.container(border=True):
                    render_tile(TOKENS[i])

    selected_key = st.session_state.get("selected_token_key", None)
    if not selected_key:
        st.info("Choose a token to continue.")
        st.stop()

    token = next(x for x in TOKENS if x["key"] == selected_key)
    st.success(f"Selected: {token['label']}")
    st.write("")

    # Amount
    if token["key"] == "detour":
        amount = st.number_input("Choose an amount (R0–R2500)", min_value=0, max_value=token["max_amount"], value=0, step=50)
    else:
        amount = st.number_input("Amount (optional)", min_value=0, max_value=token["max_amount"], value=token["default_amount"], step=50)

    area = st.selectbox("Which area should this apply to?", options=ROUTE_AREAS)
    suggestion = st.text_area("Suggestion (optional)", placeholder="A place to stay, a restaurant, a viewpoint, a hidden gem…", height=120)
    want_update = st.checkbox("Send me a pic when you use my token 📸", value=True)

    if st.button("Generate my reference code →", use_container_width=True):
        ref = make_ref()
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
            "paid": False,
        }
        _append_row(PLEDGE_PATH, pledge_row)

        st.success("Done! Here’s your EFT reference code:")
        st.code(ref)
        st.info("EFT details will be shown here once added. For now, please use the EFT details from your invite message and paste the reference code above.")

def page_admin():
    st.subheader("Admin dashboard")
    st.caption("Password required.")

    admin_pw = None
    try:
        admin_pw = st.secrets.get("ADMIN_PASSWORD", None)
    except Exception:
        admin_pw = None

    if not admin_pw:
        st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        st.stop()

    pw = st.text_input("Admin password", type="password")
    if pw != admin_pw:
        st.stop()

    st.success("Welcome, admin ✅")

    st.write("### RSVPs")
    if RSVP_PATH.exists():
        rsvps = pd.read_csv(RSVP_PATH)
        st.dataframe(rsvps, use_container_width=True, hide_index=True)

        yes = rsvps[rsvps["attending"].astype(str).str.contains("Yes", na=False)]
        no = rsvps[rsvps["attending"].astype(str).str.contains("No", na=False)]
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
    st.write("### Honeymoon tokens / pledges")
    if PLEDGE_PATH.exists():
        pledges = pd.read_csv(PLEDGE_PATH)
        st.dataframe(pledges, use_container_width=True, hide_index=True)

        totals = pledges.groupby("token")["amount"].sum().reset_index().sort_values("amount", ascending=False)
        st.write("**Totals by token**")
        st.dataframe(totals, use_container_width=True, hide_index=True)

        st.download_button(
            "Download pledges CSV",
            data=pledges.to_csv(index=False).encode("utf-8"),
            file_name="pledges.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No pledges yet.")

# ============================================================
# Main
# ============================================================
st.set_page_config(page_title="Damian & Megan — Wedding Invite", page_icon="💍", layout="centered")
inject_css()

# If not authed, show landing page
if not st.session_state.get("authed_code"):
    landing_page()

guest = get_authed_guest()

# Sidebar nav (after auth)
st.sidebar.title("Menu")
if st.sidebar.button("Log out", use_container_width=True):
    for k in ["authed_code","guest_label","rsvp_step","rsvp_path","rsvp_fun","rsvp_confirmed_attending","tiles_shown","selected_token_key","nav_page"]:
        st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

default_page = st.session_state.get("nav_page", "Home")
page = st.sidebar.radio("Go to", ["Home", "RSVP", "Details", "Honeymoon", "Admin"], index=["Home","RSVP","Details","Honeymoon","Admin"].index(default_page))

# reset the nav hint after used
st.session_state["nav_page"] = page

if page == "Home":
    page_home(guest)
elif page == "RSVP":
    header_card(guest)
    st.write("")
    rsvp_wizard(guest)
elif page == "Details":
    page_details()
elif page == "Honeymoon":
    honeymoon_tiles(guest)
elif page == "Admin":
    page_admin()
