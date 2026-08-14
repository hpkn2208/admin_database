"""Feedback admin — standalone Streamlit app for browsing, downloading, and
deleting rows in the shared `feedback` table (Supabase Postgres) + their
images/evidence (Cloudflare R2). Username/password gated: this has permanent
delete access to the same production data streamlit_app writes to.

Read-only against streamlit_app / streamlit_case_app themselves — this app
only touches the shared `feedback` table and `research-app/` R2 objects that
Web 1's feedback widget already writes to. See db.py / storage.py.
"""

import io
import json
import zipfile
from pathlib import Path

import streamlit as st

import db
import storage

st.set_page_config(page_title="Feedback admin", layout="wide")


def _present(v) -> bool:
    """True only for a real, non-empty string. Pandas can surface SQL NULLs
    as NaN — a *truthy* float, unlike None — for nullable text columns
    (version-dependent), so a bare `if v:` check is not safe here."""
    return isinstance(v, str) and bool(v)


def _arcname(key: str) -> str:
    """R2 keys look like "research-app/{category}/{filename}" — drop the
    app-prefix segment so the ZIP mirrors Web 1's own feedback export
    (feedback.py::create_feedback_zip), which groups files under
    "{category}/{filename}" instead of dumping everything flat."""
    parts = key.split("/", 1)
    return parts[1] if len(parts) > 1 else parts[0]

# ── Login gate ────────────────────────────────────────────────────────────
if not st.session_state.get("authed"):
    st.title("Feedback admin")
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        if user == st.secrets.get("admin_username") and pwd == st.secrets.get("admin_password"):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Wrong username or password.")
    st.stop()

st.title("Feedback admin")
st.caption("Browse, download, and delete rows in the shared `feedback` table (Supabase + R2).")

df = db.load_feedback()

if df.empty:
    st.info("No feedback rows yet.")
    st.stop()

st.write(f"{len(df)} row(s)")

event = st.dataframe(
    df,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "id": None,
        "original_path": None,
        "overlay_path": None,
        "predictions": None,
        "models_used": None,
        "evidence_paths": None,
        "created_at": st.column_config.DatetimeColumn("Created", format="MMM DD, YYYY, hh:mm a"),
        "evidence_count": st.column_config.NumberColumn("Evidence files"),
    },
)

selected = df.iloc[event.selection.rows] if event.selection.rows else df.iloc[0:0]

if selected.empty:
    st.info("Select one or more rows above to view images, download, or delete.")
    st.stop()

st.divider()
st.subheader(f"{len(selected)} row(s) selected")

if st.button("Prepare ZIP of all selected images"):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for _, row in selected.iterrows():
            for col in ("original_path", "overlay_path"):
                key = row[col]
                if _present(key):
                    zf.writestr(_arcname(key), storage.download_bytes(key))
            if _present(row["evidence_paths"]):
                for key in json.loads(row["evidence_paths"]):
                    zf.writestr(_arcname(key), storage.download_bytes(key))
    st.session_state["zip_bytes"] = zip_buf.getvalue()

if "zip_bytes" in st.session_state:
    st.download_button(
        "Download ZIP", st.session_state["zip_bytes"],
        file_name="feedback_selected.zip", key="dl_zip",
    )

st.divider()

for _, row in selected.iterrows():
    with st.container(border=True):
        header = f"**{row['created_at']}** — {row['category']} — {row['feedback_type']}"
        if _present(row["reason"]):
            header += f" ({row['reason']})"
        st.markdown(header)

        c1, c2 = st.columns(2)
        if _present(row["original_path"]):
            with c1:
                st.image(storage.get_image_url(row["original_path"]), caption="Original")
                st.download_button(
                    "Download original", storage.download_bytes(row["original_path"]),
                    file_name=Path(row["original_path"]).name, key=f"dl_orig_{row['id']}",
                )
        if _present(row["overlay_path"]):
            with c2:
                st.image(storage.get_image_url(row["overlay_path"]), caption="Overlay")
                st.download_button(
                    "Download overlay", storage.download_bytes(row["overlay_path"]),
                    file_name=Path(row["overlay_path"]).name, key=f"dl_ov_{row['id']}",
                )

        if _present(row["comment"]):
            st.markdown(f"**Comment:** {row['comment']}")

        if _present(row["evidence_paths"]):
            st.markdown("**Evidence attachments:**")
            for key in json.loads(row["evidence_paths"]):
                st.download_button(
                    f":material/download: {Path(key).name}", storage.download_bytes(key),
                    file_name=Path(key).name, key=f"dl_ev_{row['id']}_{key}",
                )

st.divider()
st.warning(f"Deleting is permanent — {len(selected)} row(s) and all their images/evidence "
           "will be removed from Supabase + R2, no undo.")
confirm = st.checkbox("I understand, delete the selected row(s).")
if st.button(":material/delete: Delete selected", disabled=not confirm, type="primary"):
    db.delete_feedback_rows(selected["id"].tolist())
    db.load_feedback.clear()
    st.session_state.pop("zip_bytes", None)
    st.success(f"Deleted {len(selected)} row(s).")
    st.rerun()
