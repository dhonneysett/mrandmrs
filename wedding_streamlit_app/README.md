# Wedding Invite Streamlit App (Foundation)

This is a secure-ish foundation for:
- Guest-specific invite links (code-based)
- Cheeky RSVP flow (but still captures real RSVP)
- Wedding info page
- Honeymoon "Sponsor a Moment" page (no payments handled in-app)
- Admin dashboard (password protected)

## Important security note
The app **does not process payments**. It only generates a reference code and shows EFT instructions.

## Quick start (local)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub
2. On Streamlit Cloud, create an app from your repo
3. In Streamlit Cloud settings, add secrets from `secrets.example.toml` (admin password etc.)
4. Before sending invites, set up persistent storage (Google Sheets or Supabase).
   Local file writes on Streamlit Cloud are not reliable.

## Admin password (generated)
Set `ADMIN_PASSWORD` in secrets. Example generated password:
**WED-UPZWJHHI6Z**
(You can change it anytime.)

## Guests
Guest codes are in `guests.csv`. You can regenerate codes if needed.
