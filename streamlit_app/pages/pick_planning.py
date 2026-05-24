import streamlit as st
import pandas as pd
import datetime
import os

# ── Pick/Reach database ───────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_data_dir = os.environ.get("SHIFT_PLANNER_DATA")
PICK_REACH_PATH = (
    os.path.join(_data_dir, "HMW1_Master_Combined_Paths.csv") if _data_dir
    else os.path.join(BASE_DIR, "..", "..", "HMW1_Master_Combined_Paths.csv")
)


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    col_map = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c in col_map:
            return col_map[c]
    return None


@st.cache_data
def load_pick_reach(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    name_col = _find_col(df, ["names", "name", "full name", "employee name"])
    if name_col and name_col != "Names":
        df = df.rename(columns={name_col: "Names"})
    df["Names"] = df["Names"].str.strip()
    return df


ALIAS_CANDS = ["alias", "employee login", "login", "emp id", "employee id", "associate login"]
NAME_CANDS  = ["name", "names", "full name", "employee name", "associate name"]
SHIFT_CANDS = ["schedule start time", "schedule start", "shift start", "start time", "start", "shift begin", "scheduled start"]
VTO_CANDS   = ["employee login", "alias", "login", "emp id", "employee id", "associate login"]

# ── Sidebar — database status ─────────────────────────────────────────────────
st.sidebar.markdown("### Database")
try:
    pick_reach_df = load_pick_reach(PICK_REACH_PATH)
    st.sidebar.success(f"Pick/Reach DB: {len(pick_reach_df)} records")
    with st.sidebar.expander("Preview DB"):
        st.dataframe(pick_reach_df, use_container_width=True)
except FileNotFoundError:
    st.sidebar.error(
        "HMW1_Master_Combined_Paths.csv not found.  \n"
        "Expected: `Amazon_Pick_Planning/HMW1_Master_Combined_Paths.csv`"
    )
    st.stop()

# ── Page title ────────────────────────────────────────────────────────────────
st.title("Pick Planning")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Attendance
# ─────────────────────────────────────────────────────────────────────────────
st.header("Section 1 — Attendance")

upload_col, time_col = st.columns([1, 1])

with upload_col:
    attendance_file = st.file_uploader(
        "Upload Roster file (CSV)",
        type=["csv"],
        help="Roster export (e.g. HMW1_roster_…csv). Expected columns: Employee Login, Employee Name, Schedule Start Time. Column names are auto-detected.",
    )

with time_col:
    st.markdown("**Shift time window**")
    start_time = st.time_input("From", value=datetime.time(18, 30))
    end_time   = st.time_input("To",   value=datetime.time(23, 0))

attendance_cleaned = None

if attendance_file:
    raw_att = pd.read_csv(attendance_file)
    raw_att.columns = raw_att.columns.str.strip()

    alias_col = _find_col(raw_att, ALIAS_CANDS)
    name_col  = _find_col(raw_att, NAME_CANDS)
    shift_col = _find_col(raw_att, SHIFT_CANDS)

    missing = []
    if not alias_col: missing.append("Alias / Employee Login")
    if not name_col:  missing.append("Name")
    if not shift_col: missing.append("Shift Start")

    if missing:
        st.error(
            f"Could not auto-detect columns for: **{', '.join(missing)}**  \n"
            f"Columns found: `{list(raw_att.columns)}`"
        )
    else:
        att = raw_att[[alias_col, name_col, shift_col]].rename(columns={
            alias_col: "Alias",
            name_col:  "Names",
            shift_col: "Shift Start",
        })

        # Try roster format "May 17 18:30" first, fall back to generic ISO for older exports
        parsed_specific = pd.to_datetime(att["Shift Start"], format="%b %d %H:%M", errors="coerce")
        parsed_generic  = pd.to_datetime(att["Shift Start"], errors="coerce")
        att["Shift Start"] = parsed_specific.fillna(parsed_generic)
        att = att.dropna(subset=["Shift Start"])
        att["Shift Time"] = att["Shift Start"].dt.time

        att_filtered = att[
            (att["Shift Time"] >= start_time) &
            (att["Shift Time"] <= end_time)
        ].sort_values("Shift Time")

        attendance_cleaned = (
            att_filtered
            .drop_duplicates(subset="Names", keep="first")
            .reset_index(drop=True)
        )

        st.success(
            f"Attendance cleaned — **{len(attendance_cleaned)}** associates "
            f"in window {start_time.strftime('%H:%M')} – {end_time.strftime('%H:%M')}"
        )
        st.dataframe(
            attendance_cleaned[["Alias", "Names", "Shift Time"]],
            use_container_width=True,
        )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Merge with Pick/Reach DB
# ─────────────────────────────────────────────────────────────────────────────
st.header("Section 2 — Pick / Reach Assignment")

att_with_path = None

if attendance_cleaned is not None:
    # Merge on login/alias (case-insensitive) — more reliable than name matching
    # because name formatting differs between the DB and the attendance export.
    att_merge = attendance_cleaned.copy()
    att_merge["_key"] = att_merge["Alias"].astype(str).str.strip().str.lower()

    db_merge = pick_reach_df.copy()
    db_merge["_key"] = db_merge["Login"].astype(str).str.strip().str.lower()

    merged = pd.merge(
        att_merge,
        db_merge[["_key", "Path"]],
        on="_key",
        how="left",
    ).drop(columns=["_key"])

    keep_cols = [c for c in ["Alias", "Names", "Path"] if c in merged.columns]
    att_with_path = merged[keep_cols].drop_duplicates().reset_index(drop=True)

    unmatched = att_with_path["Path"].isna().sum() if "Path" in att_with_path.columns else 0
    if unmatched:
        st.warning(
            f"{unmatched} associate(s) not found in the database — Path will be blank for them."
        )
        with st.expander("Show unmatched associates"):
            st.dataframe(
                att_with_path[att_with_path["Path"].isna()],
                use_container_width=True,
            )

    st.success(f"Merged — **{len(att_with_path)}** records")
    st.dataframe(att_with_path, use_container_width=True)
else:
    st.info("Complete Section 1 first (upload Attendance and confirm the time window).")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Remove VTO
# ─────────────────────────────────────────────────────────────────────────────
st.header("Section 3 — Remove VTO")

vto_file = st.file_uploader(
    "Upload VTO file (CSV) — optional",
    type=["csv"],
    help="Daily VTO list. Leave empty to skip VTO removal and proceed with all associates.",
)

final_df = None

if att_with_path is None:
    st.info("Complete Sections 1 and 2 first.")

elif vto_file is not None:
    raw_vto = pd.read_csv(vto_file)
    raw_vto.columns = raw_vto.columns.str.strip()

    vto_login_col = _find_col(raw_vto, VTO_CANDS)

    if not vto_login_col:
        st.error(
            f"Could not find a login column in the VTO file.  \n"
            f"Columns found: `{list(raw_vto.columns)}`"
        )
    else:
        vto_logins = raw_vto[vto_login_col].astype(str).str.strip().str.lower()

        result = att_with_path.copy()
        result["Alias"] = result["Alias"].astype(str).str.strip().str.lower()
        result = result[~result["Alias"].isin(vto_logins)]
        result = result.sort_values(by="Path").reset_index(drop=True)

        final_df = result
        removed = len(att_with_path) - len(final_df)
        st.success(
            f"VTO removed — **{removed}** associate(s) excluded.  "
            f"Final list: **{len(final_df)}** associates."
        )

else:
    # No VTO file — pass through Section 2 data as-is
    final_df = att_with_path.sort_values(by="Path").reset_index(drop=True)
    st.info(f"No VTO file uploaded — proceeding with all **{len(final_df)}** associates.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL RESULTS + DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.header("Final Pick Plan")

if final_df is not None:
    st.dataframe(final_df, use_container_width=True)

    csv_bytes = final_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Final Pick Plan (CSV)",
        data=csv_bytes,
        file_name=f"pick_plan_{datetime.date.today()}.csv",
        mime="text/csv",
    )
else:
    st.info("Complete all three sections above to generate the final pick plan.")
