import streamlit as st
import pandas as pd
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "..", "..", "HMW1_Master_Combined_Paths.csv")

PATH_ORDER = ["CR", "Reach", "Forks", "Clamp", "EPJ", "GTDR"]

PATH_LABELS = [
    ("CR",    "Center Rider"),
    ("Reach", "Reach"),
    ("Forks", "Fork"),
    ("Clamp", "Clamp"),
    ("EPJ",   "EPJ"),
    ("GTDR",  "GTDR"),
]


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    col_map = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c in col_map:
            return col_map[c]
    return None


# ── Page ─────────────────────────────────────────────────────────────────────
st.title("Database Update")
st.markdown("---")
st.markdown(
    "Upload one or more trained-list CSV files to rebuild **HMW1_Master_Combined_Paths.csv**. "
    "Only upload the files you have — missing paths are simply skipped."
)

# ── File uploaders — 2 columns ────────────────────────────────────────────────
uploaded: dict[str, object] = {}
left, right = st.columns(2)
for i, (path_label, display_name) in enumerate(PATH_LABELS):
    col = left if i % 2 == 0 else right
    with col:
        f = st.file_uploader(
            f"{display_name}  —  `{path_label}`",
            type=["csv"],
            key=f"db_upload_{path_label}",
        )
        if f:
            uploaded[path_label] = f

st.markdown("---")

if not uploaded:
    st.info("Upload at least one trained-list file above to get started.")
    st.stop()

st.markdown(f"**{len(uploaded)} file(s) ready:** {', '.join(uploaded.keys())}")

# ── Process button ────────────────────────────────────────────────────────────
if st.button("Build Database", type="primary"):
    new_dfs = []
    load_errors = []

    # Step 1 — load each uploaded file into individual path rows
    for path_label, file in uploaded.items():
        try:
            df = pd.read_csv(file, encoding="latin-1")
            df.columns = df.columns.str.strip()

            name_col  = _find_col(df, ["name", "names", "full name", "employee name"])
            login_col = _find_col(df, ["login", "alias", "employee login", "emp login"])

            if not name_col or not login_col:
                missing = []
                if not name_col:  missing.append("Name")
                if not login_col: missing.append("Login")
                load_errors.append(
                    f"**{path_label}** — could not find column(s): {', '.join(missing)}. "
                    f"Found: `{list(df.columns)}`"
                )
                continue

            chunk = df[[name_col, login_col]].rename(
                columns={name_col: "Name", login_col: "Login"}
            )
            chunk["Name"]  = chunk["Name"].astype(str).str.strip()
            chunk["Login"] = chunk["Login"].astype(str).str.strip()
            chunk["Path"]  = path_label
            new_dfs.append(chunk)

        except Exception as e:
            load_errors.append(f"**{path_label}** — {e}")

    for err in load_errors:
        st.error(err)

    if not new_dfs:
        st.stop()

    # Step 2 — load existing DB and expand to one row per (Login, path),
    #           dropping any paths that are being replaced by the new uploads
    replaced_paths = set(uploaded.keys())
    existing_rows = []

    try:
        existing_df = pd.read_csv(DB_PATH)
        for _, row in existing_df.iterrows():
            for p in str(row["Path"]).split("_"):
                p = p.strip()
                if p and p not in replaced_paths:
                    existing_rows.append({"Name": row["Name"], "Login": row["Login"], "Path": p})
        retained = pd.DataFrame(existing_rows) if existing_rows else pd.DataFrame(columns=["Name", "Login", "Path"])
        st.info(
            f"Existing database loaded — retaining paths not in this upload: "
            f"{sorted(set(PATH_ORDER) - replaced_paths) or 'none'}"
        )
    except FileNotFoundError:
        retained = pd.DataFrame(columns=["Name", "Login", "Path"])
        st.info("No existing database found — building from uploads only.")

    # Step 3 — combine retained rows + new upload rows, then regroup
    def combine_paths(paths: pd.Series) -> str:
        unique_ordered = [p for p in PATH_ORDER if p in paths.values]
        return "_".join(unique_ordered)

    combined = pd.concat([retained] + new_dfs, ignore_index=True)

    result = (
        combined.groupby("Login", sort=False)
        .agg(Name=("Name", "first"), Path=("Path", combine_paths))
        .reset_index()
    )[["Name", "Login", "Path"]]

    st.session_state["db_result"] = result

# ── Results (persists across reruns once built) ───────────────────────────────
if "db_result" in st.session_state:
    result = st.session_state["db_result"]

    multi = result[result["Path"].str.contains("_")]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total employees", len(result))
    col2.metric("Multi-path employees", len(multi))
    col3.metric("Paths included", len(uploaded))

    tab1, tab2 = st.tabs(["All employees", "Multi-path employees"])
    with tab1:
        st.dataframe(result, use_container_width=True)
    with tab2:
        st.dataframe(multi, use_container_width=True)

    st.markdown("---")
    dl_col, save_col = st.columns([1, 1])

    with dl_col:
        csv_bytes = result.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV",
            data=csv_bytes,
            file_name=f"HMW1_Master_Combined_Paths_{datetime.date.today()}.csv",
            mime="text/csv",
        )

    with save_col:
        if st.button("Save & Activate as Database", type="primary"):
            result.to_csv(DB_PATH, index=False)
            # Clear cache so Pick Planning picks up the new DB immediately
            st.cache_data.clear()
            st.success(
                f"Database updated — {len(result)} employees saved to "
                f"`HMW1_Master_Combined_Paths.csv`. "
                "Pick Planning will use the new data on next run."
            )
