import streamlit as st
import pandas as pd
import datetime
import os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, "..", "..", "HMW1_Master_Combined_Paths.csv")


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    col_map = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c in col_map:
            return col_map[c]
    return None


def _norm_name(series: pd.Series) -> pd.Series:
    """Uppercase, strip spaces, and normalise spaces around commas for matching."""
    return series.astype(str).str.strip().str.upper().str.replace(r"\s*,\s*", ",", regex=True)


# ── Page ─────────────────────────────────────────────────────────────────────
st.title("Attendance Reconciliation")
st.markdown("---")
st.markdown(
    "Upload the **In-House** report and the **Pick Plan** output from the Pick Planning page "
    "to identify who is in the building but not on shift, and who is scheduled but not present."
)

# ── File uploaders ────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    in_house_file = st.file_uploader(
        "In-House report (CSV)",
        type=["csv"],
        help="The in-house activity report. Must contain an Employee Name column.",
    )

with right:
    pick_plan_file = st.file_uploader(
        "Pick Plan output (CSV)",
        type=["csv"],
        help="The final pick plan downloaded from the Pick Planning page.",
    )

st.markdown("---")

# ── Guard ─────────────────────────────────────────────────────────────────────
if not in_house_file or not pick_plan_file:
    missing = []
    if not in_house_file:  missing.append("In-House report")
    if not pick_plan_file: missing.append("Pick Plan output")
    st.info(f"Waiting for: {' and '.join(missing)}.")
    st.stop()

# ── In-House file ─────────────────────────────────────────────────────────────
in_house_raw = pd.read_csv(in_house_file)
in_house_raw.columns = in_house_raw.columns.str.strip()

with st.expander("In-House columns detected"):
    st.write(list(in_house_raw.columns))

in_house_name_col = _find_col(
    in_house_raw,
    ["employee name", "name", "names", "associate name", "full name"],
)

if not in_house_name_col:
    st.error(
        f"Could not find a Name column in the In-House file.  \n"
        f"Columns found: `{list(in_house_raw.columns)}`"
    )
    st.stop()

# ── Pick Plan file ────────────────────────────────────────────────────────────
pick_plan_raw = pd.read_csv(pick_plan_file)
pick_plan_raw.columns = pick_plan_raw.columns.str.strip()

with st.expander("Pick Plan columns detected"):
    st.write(list(pick_plan_raw.columns))

pick_plan_name_col  = _find_col(pick_plan_raw, ["names", "name", "employee name", "associate name", "full name"])
pick_plan_login_col = _find_col(pick_plan_raw, ["alias", "login", "employee login", "emp login"])

if not pick_plan_name_col:
    st.error(
        f"Could not find a Names column in the Pick Plan file.  \n"
        f"Columns found: `{list(pick_plan_raw.columns)}`"
    )
    st.stop()

# ── Build name + login sets ───────────────────────────────────────────────────
in_house_names = (
    in_house_raw[[in_house_name_col]]
    .rename(columns={in_house_name_col: "Names"})
    .drop_duplicates()
    .copy()
)
in_house_names["_key"] = _norm_name(in_house_names["Names"])

# Pick plan: keep Names and Alias (login) if available
pp_cols = [pick_plan_name_col]
if pick_plan_login_col:
    pp_cols.append(pick_plan_login_col)

attendance_names = pick_plan_raw[pp_cols].drop_duplicates().copy()
attendance_names.rename(columns={pick_plan_name_col: "Names"}, inplace=True)
if pick_plan_login_col:
    attendance_names.rename(columns={pick_plan_login_col: "Login"}, inplace=True)
attendance_names["_key"] = _norm_name(attendance_names["Names"])

# ── Login lookup table from database (for In-Building group) ─────────────────
db_login_map: dict[str, str] = {}
try:
    db_df = pd.read_csv(DB_PATH)
    db_df.columns = db_df.columns.str.strip()
    db_name_col  = _find_col(db_df, ["name", "names"])
    db_login_col = _find_col(db_df, ["login", "alias", "employee login"])
    if db_name_col and db_login_col:
        db_df["_key"] = _norm_name(db_df[db_name_col])
        db_login_map = db_df.set_index("_key")[db_login_col].to_dict()
except FileNotFoundError:
    pass  # login lookup simply won't populate for in-building group

# ── Reconciliation ────────────────────────────────────────────────────────────
in_building = in_house_names[
    ~in_house_names["_key"].isin(attendance_names["_key"])
].copy()
in_building["Login"]  = in_building["_key"].map(db_login_map)
in_building["Status"] = "In Building – Not on Shift"
in_building = in_building[["Names", "Login", "Status"]]

absent = attendance_names[
    ~attendance_names["_key"].isin(in_house_names["_key"])
].copy()
absent["Status"] = "Absent – On Shift Schedule"
if "Login" not in absent.columns:
    absent["Login"] = None
absent = absent[["Names", "Login", "Status"]]

reconciliation_df = pd.concat([in_building, absent]).reset_index(drop=True)

# ── Results ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("In-House headcount",  len(in_house_names))
col2.metric("On-shift headcount",  len(attendance_names))
col3.metric("Discrepancies found", len(reconciliation_df))

tab1, tab2, tab3 = st.tabs([
    f"All discrepancies ({len(reconciliation_df)})",
    f"In Building – Not on Shift ({len(in_building)})",
    f"Absent – On Shift Schedule ({len(absent)})",
])

with tab1:
    st.dataframe(reconciliation_df, use_container_width=True)

with tab2:
    st.markdown("These associates are in the building but are **not on the shift schedule**.")
    st.dataframe(in_building, use_container_width=True)

with tab3:
    st.markdown("These associates are on the shift schedule but are **not showing as in the building**.")
    st.dataframe(absent, use_container_width=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
csv_bytes = reconciliation_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Reconciliation Report (CSV)",
    data=csv_bytes,
    file_name=f"attendance_reconciliation_{datetime.date.today()}.csv",
    mime="text/csv",
)
