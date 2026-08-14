# Feedback admin

Standalone Streamlit app for browsing, downloading, and deleting rows in the
shared `feedback` table (Supabase Postgres) written by
`Stage3/streamlit_app`'s feedback widget — and their images/evidence on
Cloudflare R2. **Local-only, password-gated** — do not deploy this publicly,
it has permanent delete access to production data.

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Fill in `.streamlit/secrets.toml`:
- `postgres_url` and `[r2]` — copy from `streamlit_app/.streamlit/secrets.toml` (same Supabase project + R2 bucket).
- `admin_username` / `admin_password` — pick your own; they only gate this app's login screen.

## Run

```bash
streamlit run app.py
```

## What it does

- Lists every row of the `feedback` table (created date, category, correct/incorrect,
  reason, comment, evidence-file count).
- Select one or more rows (click the checkboxes in the table) to:
  - View the original + overlay images inline.
  - Download the original/overlay/evidence files individually, or bundle the
    whole selection into one ZIP.
  - Permanently delete the selected rows — this also removes their images
    and evidence attachments from R2. Requires an explicit confirmation
    checkbox before the delete button is enabled. Cannot be undone.
