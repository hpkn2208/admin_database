# Database lichen project

Standalone Streamlit app for browsing, downloading, and deleting rows in the
shared `feedback` table (Supabase Postgres) written by
[the AI Model Evaluation app](https://yolounetlichendetection-zkyucczccmlcsqkyewmu46.streamlit.app/)'s
(`Stage3/streamlit_app`) feedback widget — and their images/evidence on
Cloudflare R2. Username/password gated — it has permanent delete access to
production data, so keep the credentials in `.streamlit/secrets.toml` (or
Streamlit Cloud's Secrets UI) strong if this is ever exposed beyond a small
trusted group.

Deployed at: https://appdatabase-hqctzsnnzb6zfftya5mzfy.streamlit.app/
(repo: https://github.com/hpkn2208/admin_database) — kept awake by
`.github/workflows/keep-alive.yml`, same pattern as `streamlit_app` /
`streamlit_case_app`.

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
