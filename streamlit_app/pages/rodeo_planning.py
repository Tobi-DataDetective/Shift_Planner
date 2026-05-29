import streamlit as st
import pandas as pd
import datetime

PROCESS_PATH_KEYWORDS = ["FPP", "Frozen", "Chilled"]

WORK_POOL_OPTIONS = [
    "PickingNotYetPicked",
    "PickingNotYetPickedNotPrioritized",
    "PickingPicked",
    "Palletized",
]

# ── Page ─────────────────────────────────────────────────────────────────────
st.title("Rodeo Planning")
st.markdown("---")

# ── File upload ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload ExSD Report (CSV)",
    type=["csv"],
    help="ExSD report export. Expected columns: Process Path, Work Pool, ExSD, Quantity.",
)

if not uploaded_file:
    st.info("Upload an ExSD Report CSV to get started.")
    st.stop()

# ── Load & validate ───────────────────────────────────────────────────────────
df = pd.read_csv(uploaded_file)
df.columns = df.columns.str.strip()

required = ["Process Path", "Work Pool", "ExSD", "Quantity"]
missing_cols = [c for c in required if c not in df.columns]
if missing_cols:
    st.error(
        f"Could not find required column(s): **{', '.join(missing_cols)}**  \n"
        f"Columns found: `{list(df.columns)}`"
    )
    st.stop()

# Clean
df["Process Path"] = df["Process Path"].astype(str).str.strip()
df["Work Pool"]    = df["Work Pool"].astype(str).str.strip()
df["Quantity"]     = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)

st.success(f"File loaded: **{uploaded_file.name}** — {len(df):,} rows")
st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────────────
st.subheader("Filters")

left_col, right_col = st.columns(2)

with left_col:
    st.markdown("**Process Path**")
    path_mode = st.radio(
        "Mode",
        options=["Include", "Exclude"],
        horizontal=True,
        key="path_mode",
    )
    path_keywords = st.multiselect(
        "Path type(s)",
        options=PROCESS_PATH_KEYWORDS,
        default=PROCESS_PATH_KEYWORDS,
        key="path_keywords",
        help="Matches any Process Path containing the selected keyword(s).",
    )

with right_col:
    st.markdown("**Work Pool**")
    work_pool_selection = st.multiselect(
        "Work pool value(s)",
        options=WORK_POOL_OPTIONS,
        default=WORK_POOL_OPTIONS,
        key="work_pool_selection",
    )

st.markdown("---")

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()

# Process Path — substring match on selected keywords
if path_keywords:
    pattern = "|".join(path_keywords)
    matches = filtered["Process Path"].str.contains(pattern, case=False, na=False)
    filtered = filtered[matches] if path_mode == "Include" else filtered[~matches]
else:
    # Nothing selected → nothing passes
    filtered = filtered.iloc[0:0]

# Work Pool — exact match on selected values
if work_pool_selection:
    filtered = filtered[filtered["Work Pool"].isin(work_pool_selection)]
else:
    filtered = filtered.iloc[0:0]

filtered = filtered.reset_index(drop=True)

# ── Metrics ───────────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric("Rows (filtered)",       f"{len(filtered):,}")
m2.metric("Total Quantity",        f"{int(filtered['Quantity'].sum()):,}")
m3.metric("Unique Process Paths",  f"{filtered['Process Path'].nunique()}")

# ── Results table ─────────────────────────────────────────────────────────────
st.subheader(f"Results — {len(filtered):,} rows")
st.dataframe(filtered, use_container_width=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Report (CSV)",
    data=csv_bytes,
    file_name=f"rodeo_plan_{datetime.date.today()}.csv",
    mime="text/csv",
    disabled=filtered.empty,
)
