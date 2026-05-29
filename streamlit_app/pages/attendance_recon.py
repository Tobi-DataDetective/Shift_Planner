import streamlit as st
import pandas as pd
import datetime
import os

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
_data_dir = os.environ.get("SHIFT_PLANNER_DATA")
DB_PATH   = (
    os.path.join(_data_dir, "HMW1_Master_Combined_Paths.csv") if _data_dir
    else os.path.join(BASE_DIR, "..", "..", "HMW1_Master_Combined_Paths.csv")
)


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    col_map = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c in col_map:
            return col_map[c]
    return None


def _norm_name(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().str.replace(r"\s*,\s*", ",", regex=True)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].fillna("").astype(str)
    return out


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

pick_plan_name_col  = _find_col(pick_plan_raw, ["names", "name", "employee name", "associate name", "full name"])
pick_plan_login_col = _find_col(pick_plan_raw, ["alias", "login", "employee login", "emp login"])

if not pick_plan_name_col:
    st.error(
        f"Could not find a Names column in the Pick Plan file.  \n"
        f"Columns found: `{list(pick_plan_raw.columns)}`"
    )
    st.stop()

st.success(f"Files loaded: **{in_house_file.name}** and **{pick_plan_file.name}**")

# ── Build name + login sets ───────────────────────────────────────────────────
in_house_names = (
    in_house_raw[[in_house_name_col]]
    .rename(columns={in_house_name_col: "Names"})
    .drop_duplicates()
    .copy()
)
in_house_names["_key"] = _norm_name(in_house_names["Names"])

pp_cols = [pick_plan_name_col]
if pick_plan_login_col:
    pp_cols.append(pick_plan_login_col)

attendance_names = pick_plan_raw[pp_cols].drop_duplicates().copy()
attendance_names.rename(columns={pick_plan_name_col: "Names"}, inplace=True)
if pick_plan_login_col:
    attendance_names.rename(columns={pick_plan_login_col: "Login"}, inplace=True)
attendance_names["_key"] = _norm_name(attendance_names["Names"])

# ── Combined login lookup: DB first, then pick plan ──────────────────────────
# timeofftask has no login column, so we pull from every available source.
login_map: dict[str, str] = {}

try:
    db_df = pd.read_csv(DB_PATH)
    db_df.columns = db_df.columns.str.strip()
    db_name_col  = _find_col(db_df, ["name", "names"])
    db_login_col = _find_col(db_df, ["login", "alias", "employee login"])
    if db_name_col and db_login_col:
        db_df["_key"] = _norm_name(db_df[db_name_col])
        login_map.update(db_df.set_index("_key")[db_login_col].astype(str).to_dict())
except FileNotFoundError:
    pass

# Layer the pick plan's Alias column on top for anyone not already in the DB
if "Login" in attendance_names.columns:
    pp_map = (
        attendance_names[["_key", "Login"]]
        .copy()
        .assign(Login=lambda d: d["Login"].fillna("").astype(str).str.strip())
        .query("Login != '' and Login.str.lower() != 'nan'")
        .drop_duplicates("_key")
        .set_index("_key")["Login"]
        .to_dict()
    )
    for k, v in pp_map.items():
        if k not in login_map:
            login_map[k] = v

# ── Build each group ──────────────────────────────────────────────────────────
_ib = in_house_names[~in_house_names["_key"].isin(attendance_names["_key"])].copy()
_ib["Login"]  = _ib["_key"].map(login_map).fillna("").astype(str)
_ib["Status"] = "Present – Not Scheduled"
in_building = _clean(_ib[["Names", "Login", "Status"]])

_ab = attendance_names[~attendance_names["_key"].isin(in_house_names["_key"])].copy()
_ab["Status"] = "Absent – Scheduled"
if "Login" not in _ab.columns:
    _ab["Login"] = ""
_ab["Login"] = _ab["Login"].fillna("").astype(str)
# Fill any blank aliases from the combined map
_empty = _ab["Login"].str.strip() == ""
_ab.loc[_empty, "Login"] = _ab.loc[_empty, "_key"].map(login_map).fillna("").astype(str)
absent = _clean(_ab[["Names", "Login", "Status"]])

all_df = pd.concat([in_building, absent], ignore_index=True)

# ── Metrics ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("In-House Headcount",      len(in_house_names))
col2.metric("Absent – Scheduled",      len(absent))
col3.metric("Present – Not Scheduled", len(in_building))

st.markdown("---")

# ── Filter ────────────────────────────────────────────────────────────────────
filter_options = ["All", "Present – Not Scheduled", "Absent – Scheduled"]
selected_filter = st.radio(
    "Filter by status",
    options=filter_options,
    horizontal=True,
)

if selected_filter == "All":
    display_df = all_df
elif selected_filter == "Present – Not Scheduled":
    display_df = in_building
else:
    display_df = absent

st.dataframe(display_df, use_container_width=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Report (CSV)",
    data=csv_bytes,
    file_name=f"attendance_reconciliation_{datetime.date.today()}.csv",
    mime="text/csv",
)
