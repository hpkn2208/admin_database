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


@st.cache_data(ttl=10)
def load_feedback() -> pd.DataFrame:
    with _engine().connect() as conn:
        df = pd.read_sql(text("SELECT * FROM feedback ORDER BY created_at DESC"), conn)
    if df.empty:
        return df
    # SQL NULLs come back from pandas as NaN, which is truthy in Python (unlike
    # None) — normalize to None so `if row["overlay_path"]:`-style checks below
    # and in app.py behave correctly for the many optional/nullable columns.
    df = df.where(pd.notnull(df), None)
    df["created_at"] = pd.to_datetime(df["created_at"])
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
