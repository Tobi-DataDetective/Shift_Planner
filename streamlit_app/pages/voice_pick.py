import streamlit as st
import pandas as pd


def parse_voice_pick(raw_data: str) -> pd.DataFrame:
    COLUMNS = [
        "#", "login_name", "warehouse_id", "date",
        "utteringPromptCount", "CorrectCheckDigitCount",
        "scanBinCount", "checkDigitPullCount", "realUtilization",
        "userVoiceSpeed",
    ]
    HEADER_SET = set(COLUMNS)

    def is_serial(val):
        try:
            float(val)
            return True
        except ValueError:
            return False

    def is_date(val):
        return val.startswith(tuple([str(y) for y in range(2020, 2030)]))

    def is_login(val):
        return val.isalpha() and 6 <= len(val) <= 10

    lines = [l.strip() for l in raw_data.strip().split("\n") if l.strip()]

    # Skip header block
    i = 0
    while i < len(lines) and lines[i] in HEADER_SET:
        i += 1

    records = []
    while i < len(lines):
        if not is_serial(lines[i]):
            i += 1
            continue

        if i + 8 >= len(lines):
            break

        _, login, warehouse, date = lines[i], lines[i+1], lines[i+2], lines[i+3]
        uttering, correct, scan, check, util = (
            lines[i+4], lines[i+5], lines[i+6], lines[i+7], lines[i+8]
        )

        if not is_login(login) or not is_date(date):
            i += 1
            continue

        voice_speed = None
        consumed = 9
        next_line  = lines[i + 9]  if i + 9  < len(lines) else ""
        after_next = lines[i + 10] if i + 10 < len(lines) else ""

        if is_serial(next_line) and not is_login(after_next) and is_serial(after_next):
            voice_speed = next_line
            consumed = 10
        elif is_serial(next_line) and next_line.replace(".", "", 1).isdigit() and "." in next_line:
            voice_speed = next_line
            consumed = 10

        records.append({
            "#":                      len(records) + 1,
            "login_name":             login,
            "warehouse_id":           warehouse,
            "date":                   date.replace("T00:00:00.000Z", ""),
            "utteringPromptCount":    int(uttering),
            "CorrectCheckDigitCount": int(correct),
            "scanBinCount":           int(scan),
            "checkDigitPullCount":    int(check),
            "realUtilization":        float(util),
            "userVoiceSpeed":         float(voice_speed) if voice_speed else None,
        })

        i += consumed

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).drop(columns=["userVoiceSpeed"])
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] == df["date"].max()].copy()
    df["#"] = range(1, len(df) + 1)
    return df


# ── Page ─────────────────────────────────────────────────────────────────────
st.title("Voice Pick")
st.markdown("---")

raw_input = st.text_area(
    "Paste raw Voice Pick data below",
    height=300,
    placeholder="Paste the raw exported text here, then click Process.",
)

if st.button("Process", type="primary"):
    if not raw_input.strip():
        st.warning("Nothing to process — paste the raw data first.")
    else:
        df = parse_voice_pick(raw_input)
        if df.empty:
            st.error("No records could be parsed. Check that the pasted data is in the expected format.")
        else:
            st.session_state["vp_df"] = df

# ── Results ───────────────────────────────────────────────────────────────────
if "vp_df" in st.session_state:
    df = st.session_state["vp_df"]

    report_date = df["date"].iloc[0].date()
    st.caption(f"Data filtered to most recent date: **{report_date}**")

    # ── Summary metrics ───────────────────────────────────────────────────────
    above_75   = df[df["realUtilization"] >= 75]
    between    = df[(df["realUtilization"] >= 25) & (df["realUtilization"] < 75)]
    below_25   = df[df["realUtilization"] < 25]

    total_col, a75_col, mid_col, b25_col = st.columns(4)

    overall_avg = df["realUtilization"].mean()
    overall_color = "rgb(9,171,59)" if overall_avg >= 70 else "rgb(255,43,43)"
    total_col.markdown(f"""
        <div style="line-height:1.6;">
            <p style="margin:0; font-size:0.875rem; font-weight:700; color:white;">Total Associates</p>
            <p style="margin:0; font-size:2rem; font-weight:700; color:white;">{len(df)}</p>
            <p style="margin:0; font-size:0.875rem; color:{overall_color};">Avg {overall_avg:.1f}%</p>
        </div>
    """, unsafe_allow_html=True)

    def avg_metric(col, title, count, avg, avg_color):
        avg_str = f"Avg {avg:.1f}%" if avg is not None else "—"
        col.markdown(f"""
            <div style="line-height:1.6;">
                <p style="margin:0; font-size:0.875rem; font-weight:700; color:white;">{title}</p>
                <p style="margin:0; font-size:2rem; font-weight:700; color:white;">{count}</p>
                <p style="margin:0; font-size:0.875rem; color:{avg_color};">{avg_str}</p>
            </div>
        """, unsafe_allow_html=True)

    avg_metric(
        a75_col, "Above 75%", len(above_75),
        above_75["realUtilization"].mean() if len(above_75) else None,
        avg_color="rgb(9,171,59)",
    )
    avg_metric(
        mid_col, "25% – 74%", len(between),
        between["realUtilization"].mean() if len(between) else None,
        avg_color="rgb(255,43,43)",
    )
    avg_metric(
        b25_col, "Below 25%", len(below_25),
        below_25["realUtilization"].mean() if len(below_25) else None,
        avg_color="rgb(255,43,43)",
    )

    st.markdown("---")

    # ── Full results table ────────────────────────────────────────────────────
    st.subheader("All Associates")
    st.dataframe(df, use_container_width=True)

    # ── Below-70 table ────────────────────────────────────────────────────────
    below_70 = df[df["realUtilization"] < 70][["login_name", "realUtilization"]].reset_index(drop=True)
    st.subheader(f"Associates Below 70% Utilization  ({len(below_70)})")
    if below_70.empty:
        st.success("All associates are at or above 70% utilization.")
    else:
        st.dataframe(below_70, use_container_width=True)

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Full Report (CSV)",
        data=csv_bytes,
        file_name=f"voice_pick_{report_date}.csv",
        mime="text/csv",
    )
