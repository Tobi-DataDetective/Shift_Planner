import streamlit as st
import pandas as pd
import io
import re

# ── Page ─────────────────────────────────────────────────────────────────────
st.title("Equipment Utilization")
st.markdown("---")
st.markdown(
    "Upload the Equipment Utilization report, then enter equipment numbers to see "
    "the **last operator** for each piece of equipment."
)

# ── File uploader ─────────────────────────────────────────────────────────────
eq_file = st.file_uploader(
    "Upload Equipment Utilization CSV",
    type=["csv"],
    help="Equipment Utilization by Login report CSV export.",
)

if not eq_file:
    st.info("Upload the Equipment Utilization report to get started.")
    st.stop()


# ── Load & process ────────────────────────────────────────────────────────────
@st.cache_data
def load_equipment_data(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    df.columns = df.columns.str.strip()

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

    # Combined logout datetime for accurate most-recent-sort
    df["_logout_dt"] = pd.to_datetime(
        df["Logout Date"] + " " + df["Logout Time"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce",
    )

    # Extract trailing digits as the lookup number (e.g. "RC1639" → "1639", "Rental PC2865" → "2865")
    df["_eq_num"] = df["Equipment Name"].str.extract(r"(\d+)$")
    return df


df = load_equipment_data(eq_file.getvalue())

total_records = len(df)
unique_equipment = df["_eq_num"].nunique()
col1, col2 = st.columns(2)
col1.metric("Total session records", f"{total_records:,}")
col2.metric("Unique equipment in file", unique_equipment)

st.markdown("---")

# ── Number input ──────────────────────────────────────────────────────────────
st.subheader("Look Up Equipment")
st.caption("Enter the number shown at the end of the Equipment Name (e.g. for RC**1639** enter 1639). "
           "Separate multiple numbers with commas, spaces, or new lines.")

input_text = st.text_area(
    "Equipment number(s)",
    placeholder="1639\n3275, 8989\n1472",
    height=110,
    label_visibility="collapsed",
)

# Parse, deduplicate, preserve order
raw_tokens = re.split(r"[,\s\n]+", input_text.strip()) if input_text.strip() else []
seen: set[str] = set()
numbers: list[str] = []
for t in raw_tokens:
    if t.isdigit() and t not in seen:
        seen.add(t)
        numbers.append(t)

if not numbers:
    st.info("Enter one or more equipment numbers above.")
    st.stop()

# ── Lookup ────────────────────────────────────────────────────────────────────
results: list[dict] = []
not_found: list[str] = []

for num in numbers:
    matches = df[df["_eq_num"] == num].dropna(subset=["_logout_dt"])
    if matches.empty:
        not_found.append(num)
        continue

    latest = matches.loc[matches["_logout_dt"].idxmax()]
    reason = latest.get("Logout Reason", "")
    reason = str(reason).strip() if str(reason).strip() not in ("", "nan") else "—"

    results.append({
        "Equipment Name": latest["Equipment Name"],
        "Equipment Number": num,
        "Last Operator": latest["Operator"],
        "Role": latest["Equipment Role"],
        "Logout Date": latest["Logout Date"],
        "Logout Time": latest["Logout Time"],
        "Logout Reason": reason,
        "System Logout": str(latest.get("System Logout", "")).strip(),
        "_logout_dt": latest["_logout_dt"],
    })

# ── Warnings for not-found numbers ───────────────────────────────────────────
for num in not_found:
    st.warning(f"No records found for equipment number **{num}**.")

if not results:
    st.stop()

st.markdown("---")

# ── View toggle ───────────────────────────────────────────────────────────────
view_col, _ = st.columns([2, 6])
with view_col:
    view_mode = st.radio("Display as", ["Cards", "Table"], horizontal=True)

results_df = pd.DataFrame(results)

# ─────────────────────────────────────────────────────────────────────────────
# CARD VIEW
# ─────────────────────────────────────────────────────────────────────────────
if view_mode == "Cards":
    COLS_PER_ROW = 3

    for row_start in range(0, len(results), COLS_PER_ROW):
        batch = results[row_start : row_start + COLS_PER_ROW]
        cols = st.columns(COLS_PER_ROW)

        for i, row in enumerate(batch):
            sys_logout = row["System Logout"].lower() == "yes"
            logout_type = "System Logout" if sys_logout else "Manual Logout"

            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"### {row['Equipment Name']}")
                    st.caption(f"#{row['Equipment Number']}  ·  {logout_type}")
                    st.divider()
                    st.markdown(f"**Last Operator:** {row['Last Operator']}")
                    st.markdown(f"**Role:** {row['Role']}")
                    st.markdown(f"**Logout Date:** {row['Logout Date']}")
                    st.markdown(f"**Logout Time:** {row['Logout Time']}")
                    st.markdown(f"**Logout Reason:** {row['Logout Reason']}")

# ─────────────────────────────────────────────────────────────────────────────
# TABLE VIEW
# ─────────────────────────────────────────────────────────────────────────────
else:
    display_df = results_df[[
        "Equipment Name",
        "Equipment Number",
        "Last Operator",
        "Role",
        "Logout Date",
        "Logout Time",
        "Logout Reason",
        "System Logout",
    ]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
