"""Postgres access for the feedback admin app — reads/deletes rows in the
SAME `feedback` table that Stage3/streamlit_app/feedback.py writes to.
Read + delete only; this app never inserts feedback rows.
"""

import json
from functools import lru_cache

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, create_engine, text

import storage


@lru_cache(maxsize=1)
def _engine():
    return create_engine(st.secrets["postgres_url"])


def ensure_schema() -> None:
    """Defensive ALTER TABLE ADD COLUMN IF NOT EXISTS for feedback_by — this
    app never creates the table, but if it's opened before streamlit_app has
    booted at least once since feedback_by was added there, the column
    might not exist yet. Idempotent, safe to call every session."""
    with _engine().begin() as conn:
        conn.execute(text("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS feedback_by TEXT"))


@st.cache_data(ttl=10)
def load_feedback() -> pd.DataFrame:
    with _engine().connect() as conn:
        df = pd.read_sql(text("SELECT * FROM feedback ORDER BY created_at DESC"), conn)
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"])
    # pandas' default "str" dtype boxes a SQL NULL as a *truthy* float NaN
    # when read as a Python scalar (not None, not pd.NA) — confirmed on both
    # pandas 3.0 locally and whatever's on Streamlit Cloud. Every place that
    # reads a nullable text column (here, and app.py's _present() helper)
    # must check isinstance(v, str), never a bare `if v:`.
    df["evidence_count"] = df["evidence_paths"].apply(
        lambda v: len(json.loads(v)) if isinstance(v, str) and v else 0
    )
    return df


def delete_feedback_rows(ids: list[str]) -> None:
    """Permanently deletes the given feedback rows AND their R2 images
    (original, overlay, evidence attachments). Cannot be undone."""
    if not ids:
        return

    select_stmt = text(
        "SELECT original_path, overlay_path, evidence_paths FROM feedback WHERE id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    delete_stmt = text("DELETE FROM feedback WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )

    with _engine().begin() as conn:
        rows = conn.execute(select_stmt, {"ids": ids}).mappings().all()
        conn.execute(delete_stmt, {"ids": ids})

    for row in rows:
        storage.delete_image(row["original_path"])
        if row["overlay_path"]:
            storage.delete_image(row["overlay_path"])
        if row["evidence_paths"]:
            for key in json.loads(row["evidence_paths"]):
                storage.delete_image(key)
