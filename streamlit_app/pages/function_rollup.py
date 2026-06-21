import re
import io
import streamlit as st
import pandas as pd

st.title("Function Rollup")
st.markdown("---")

# ── Session state init ────────────────────────────────────────────────────────
if "fr_zones" not in st.session_state:
    st.session_state["fr_zones"] = []
if "fr_input_key" not in st.session_state:
    st.session_state["fr_input_key"] = 0
if "fr_overall" not in st.session_state:
    st.session_state["fr_overall"] = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sort_key(level_str):
    m = re.search(r"\d+", str(level_str))
    return int(m.group()) if m else 0


def highlight_total(row):
    if row["Level"] == "TOTAL":
        return ["font-weight: bold; background-color: #1e3a5f"] * len(row)
    return [""] * len(row)


def build_summary(df):
    """df must have columns: login, level, jobs, jph, hours"""
    total_assoc = df["login"].nunique()
    total_jobs  = df["jobs"].sum()
    total_hours = df["hours"].sum()
    overall_avg = df["jph"].mean()

    grouped = (
        df.groupby("level")
        .agg(
            Associates=("login",  "nunique"),
            Total_Jobs =("jobs",   "sum"),
            Total_Hours=("hours",  "sum"),
            Avg_JPH    =("jph",    "mean"),
        )
        .reset_index()
    )
    grouped.columns = ["Level", "Associates", "Total Jobs", "Total Hours", "Avg JPH"]
    grouped["% of Workforce"] = (grouped["Associates"] / total_assoc * 100).round(1)
    grouped["Avg JPH"]        = grouped["Avg JPH"].round(2)
    grouped["Total Jobs"]     = grouped["Total Jobs"].astype(int)
    grouped["Total Hours"]    = grouped["Total Hours"].round(2)

    level_nums = grouped["Level"].str.extract(r"(\d+)")
    if level_nums[0].notna().all():
        grouped["_sort"] = level_nums[0].astype(int)
        grouped = grouped.sort_values("_sort").drop(columns="_sort")
    grouped = grouped.reset_index(drop=True)

    totals = pd.DataFrame([{
        "Level":          "TOTAL",
        "Associates":     total_assoc,
        "Total Jobs":     int(total_jobs),
        "Total Hours":    round(float(total_hours), 2),
        "Avg JPH":        round(float(overall_avg), 2),
        "% of Workforce": 100.0,
    }])

    summary = pd.concat([grouped, totals], ignore_index=True)
    return summary[["Level", "Associates", "% of Workforce", "Total Jobs", "Total Hours", "Avg JPH"]]


def render_summary_table(summary):
    styled = (
        summary.style
        .apply(highlight_total, axis=1)
        .format({
            "% of Workforce": "{:.1f}%",
            "Total Jobs":      "{:,}",
            "Total Hours":     "{:,.2f}",
            "Avg JPH":         "{:.2f}",
        })
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_zone(lbl, summary, total_assoc, total_jobs, total_hours, overall_avg):
    st.subheader(lbl)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Associates", total_assoc)
    m2.metric("Total Jobs",       f"{total_jobs:,}")
    m3.metric("Total Hours",      f"{total_hours:,.2f}")
    m4.metric("Overall Avg JPH",  f"{overall_avg:.2f}")
    render_summary_table(summary)


# ── Step 1: Paste + label + Process ──────────────────────────────────────────
key = st.session_state["fr_input_key"]

st.markdown("### Add Temp Zone")
raw_input = st.text_area(
    "Paste raw data (tab-separated, no header row required)",
    height=220,
    placeholder="Copy your dataset and paste it here…",
    key=f"fr_raw_input_{key}",
)
zone_label = st.text_input(
    "Temp Zone label",
    placeholder="e.g. Ambient, Chiller, Frozen",
    key=f"fr_zone_label_{key}",
)

if st.button("Process", type="primary", key=f"fr_process_{key}"):
    if not raw_input.strip():
        st.warning("Nothing to process — paste the raw data first.")
        st.stop()
    if not zone_label.strip():
        st.warning("Enter a Temp Zone label before processing.")
        st.stop()
    try:
        df_raw = pd.read_csv(
            io.StringIO(raw_input.strip()),
            sep="\t",
            header=None,
            engine="python",
            on_bad_lines="skip",
            dtype=str,
        )
    except Exception as e:
        st.error(f"Could not parse pasted data: {e}")
        st.stop()
    df_raw.columns = [f"col{i + 1}" for i in range(df_raw.shape[1])]
    st.session_state["fr_pending_raw"]   = df_raw
    st.session_state["fr_pending_label"] = zone_label.strip()

# ── Step 2: Column preview + mapping ─────────────────────────────────────────
if "fr_pending_raw" in st.session_state:
    df_raw      = st.session_state["fr_pending_raw"]
    pending_lbl = st.session_state["fr_pending_label"]
    n_cols      = df_raw.shape[1]
    col_options = list(df_raw.columns)

    st.markdown("---")
    st.subheader(f"Column Preview — {pending_lbl}")
    st.caption(
        f"Detected **{n_cols} columns** and **{df_raw.shape[0]} rows**. "
        "Use this preview to identify which column is which, then map them below."
    )
    st.dataframe(df_raw.head(5), use_container_width=True)

    st.subheader("Map Columns")
    c1, c2, c3, c4, c5 = st.columns(5)
    login_col = c1.selectbox("Login column",      col_options, index=min(8,  n_cols - 1), help="Unique associate login ID")
    level_col = c2.selectbox("Level column",      col_options, index=min(6,  n_cols - 1), help="e.g. 'Level 5', 'Level 1'")
    jobs_col  = c3.selectbox("Jobs column",       col_options, index=min(14, n_cols - 1), help="Total jobs / units processed")
    jph_col   = c4.selectbox("JPH column",        col_options, index=min(15, n_cols - 1), help="Jobs per hour rate")
    hours_col = c5.selectbox("Hours/Time column", col_options, index=min(13, n_cols - 1), help="Total hours worked in the period")

    if st.button("Run Analysis", type="primary"):
        df = df_raw[[login_col, level_col, jobs_col, jph_col, hours_col]].copy()
        df[jobs_col]  = pd.to_numeric(df[jobs_col],  errors="coerce")
        df[jph_col]   = pd.to_numeric(df[jph_col],   errors="coerce")
        df[hours_col] = pd.to_numeric(df[hours_col], errors="coerce")
        df = df.dropna(subset=[level_col, jobs_col, jph_col, hours_col])
        df[level_col] = df[level_col].str.strip()
        df[login_col] = df[login_col].str.strip()

        if df.empty:
            st.error("No valid rows found. Check your column selections.")
            st.stop()

        df_std = df.rename(columns={
            login_col: "login",
            level_col: "level",
            jobs_col:  "jobs",
            jph_col:   "jph",
            hours_col: "hours",
        })

        summary = build_summary(df_std)

        st.session_state["fr_zones"].append({
            "label":       pending_lbl,
            "summary":     summary,
            "total_assoc": len(df_std),
            "total_jobs":  int(df_std["jobs"].sum()),
            "total_hours": round(float(df_std["hours"].sum()), 2),
            "overall_avg": round(float(df_std["jph"].mean()), 2),
            "raw":         df_std,
        })
        st.session_state["fr_overall"] = None
        del st.session_state["fr_pending_raw"]
        del st.session_state["fr_pending_label"]
        st.session_state["fr_input_key"] += 1
        st.rerun()

# ── Step 4: Display individual zones ─────────────────────────────────────────
if st.session_state["fr_zones"]:
    st.markdown("---")
    st.markdown("## Results")

    all_csvs = []
    for zone in st.session_state["fr_zones"]:
        render_zone(
            zone["label"], zone["summary"],
            zone["total_assoc"], zone["total_jobs"],
            zone["total_hours"], zone["overall_avg"],
        )
        lcsv = zone["summary"].copy()
        lcsv.insert(0, "Temp Zone", zone["label"])
        all_csvs.append(lcsv)
        st.markdown("")

    st.markdown("---")
    st.download_button(
        label="Download All Zones (CSV)",
        data=pd.concat(all_csvs, ignore_index=True).to_csv(index=False).encode("utf-8"),
        file_name="function_rollup_all.csv",
        mime="text/csv",
        key="dl_all_zones",
    )

    # ── Overall Analysis ──────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("View Overall", type="primary", key="btn_view_overall"):
        parts = []
        for z in st.session_state["fr_zones"]:
            p = z["raw"].copy()
            p["zone"] = z["label"]
            parts.append(p)
        all_raw = pd.concat(parts, ignore_index=True)

        deduped = (
            all_raw.groupby("login")
            .agg(level=("level", lambda x: x.mode().iloc[0]),
                 jobs =("jobs",  "sum"),
                 hours=("hours", "sum"))
            .reset_index()
        )
        deduped = deduped[deduped["hours"] > 0].copy()
        deduped["jph"] = deduped["jobs"] / deduped["hours"]
        st.session_state["fr_overall"] = deduped

    if st.session_state["fr_overall"] is not None:
        deduped = st.session_state["fr_overall"]

        # Rebuild all_raw with zone labels for Scenario 4
        parts = []
        for z in st.session_state["fr_zones"]:
            p = z["raw"].copy()
            p["zone"] = z["label"]
            parts.append(p)
        all_raw = pd.concat(parts, ignore_index=True)

        oa_summary = build_summary(deduped)
        oa_assoc   = deduped["login"].nunique()
        oa_jobs    = int(deduped["jobs"].sum())
        oa_hours   = round(float(deduped["hours"].sum()), 2)
        oa_avg     = deduped["jph"].mean()

        st.markdown("### Overall Analysis")
        st.caption(
            f"Combined and deduplicated across all temp zones — **{oa_assoc}** unique associates. "
            "JPH computed as total jobs ÷ total hours per associate."
        )
        render_zone("Overall", oa_summary, oa_assoc, oa_jobs, oa_hours, oa_avg)
        st.download_button(
            label="Download Overall Analysis (CSV)",
            data=oa_summary.to_csv(index=False).encode("utf-8"),
            file_name="function_rollup_overall.csv",
            mime="text/csv",
            key="dl_overall",
        )

        available_levels = sorted(deduped["level"].str.strip().unique().tolist(), key=_sort_key)

        # ── Scenario 1: Remove Level ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### What If Scenario 1: Remove Level")
        st.caption("Shows what the overall numbers would look like if the selected level were excluded.")

        wi1_level = st.selectbox("Select a level to remove", options=available_levels, key="wi1_level")
        s1_df     = deduped[deduped["level"].str.strip() != wi1_level].copy()

        if s1_df.empty:
            st.info(f"No associates remain after removing {wi1_level}.")
        else:
            s1_assoc = s1_df["login"].nunique()
            s1_jobs  = int(s1_df["jobs"].sum())
            s1_hours = round(float(s1_df["hours"].sum()), 2)
            s1_avg   = s1_df["jph"].mean()

            w1, w2, w3, w4 = st.columns(4)
            w1.metric(f"Associates (ex. {wi1_level})", s1_assoc,
                      delta=f"-{oa_assoc - s1_assoc} removed", delta_color="off")
            w2.metric(f"Total Jobs (ex. {wi1_level})", f"{s1_jobs:,}",
                      delta=f"-{oa_jobs - s1_jobs:,}", delta_color="off")
            w3.metric(f"Total Hours (ex. {wi1_level})", f"{s1_hours:,.2f}",
                      delta=f"-{oa_hours - s1_hours:,.2f}", delta_color="off")
            w4.metric(f"Avg JPH (ex. {wi1_level})", f"{s1_avg:.2f}",
                      delta=f"{s1_avg - oa_avg:+.2f} vs overall", delta_color="normal")
            render_summary_table(build_summary(s1_df))

        # ── Scenario 2: Target JPH ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### What If Scenario 2: Target JPH")
        st.caption(
            "Select a level, choose how many associates in that level hit a target JPH, "
            "and see the impact on the overall average."
        )

        wi2_level = st.selectbox("Select level", options=available_levels, key="wi2_level")
        s2_lv_df  = deduped[deduped["level"].str.strip() == wi2_level].copy()
        s2_count  = s2_lv_df["login"].nunique()

        wi2_n = st.slider(
            f"Number of {wi2_level} associates hitting the target JPH",
            min_value=0, max_value=s2_count, value=0,
            help=f"There are {s2_count} associates in {wi2_level}.",
        )
        wi2_target = st.number_input(
            "Target JPH", min_value=0.0,
            value=round(float(s2_lv_df["jph"].mean()), 2),
            step=0.5, format="%.2f",
        )

        s2_lv_sorted = s2_lv_df.sort_values("jph").copy()
        if wi2_n > 0:
            s2_lv_sorted.iloc[:wi2_n, s2_lv_sorted.columns.get_loc("jph")] = wi2_target
        s2_df    = pd.concat([deduped[deduped["level"].str.strip() != wi2_level], s2_lv_sorted], ignore_index=True)
        s2_assoc = s2_df["login"].nunique()
        s2_jobs  = int(s2_df["jobs"].sum())
        s2_hours = round(float(s2_df["hours"].sum()), 2)
        s2_avg   = s2_df["jph"].mean()

        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Associates", s2_assoc)
        w2.metric("Total Jobs", f"{s2_jobs:,}")
        w3.metric("Total Hours", f"{s2_hours:,.2f}")
        w4.metric("Avg JPH (projected)", f"{s2_avg:.2f}",
                  delta=f"{s2_avg - oa_avg:+.2f} vs overall", delta_color="normal")
        render_summary_table(build_summary(s2_df))

        # ── Scenario 3: JPH Threshold ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### What If Scenario 3: JPH Threshold")
        st.caption(
            "Slide to set a JPH ceiling. Associates at or below that rate are flagged "
            "and the overall numbers are recalculated without them."
        )

        wi3_thresh  = st.slider("JPH threshold", min_value=0, max_value=75, value=0, step=1)
        s3_below    = deduped[deduped["jph"] <= wi3_thresh]
        s3_above    = deduped[deduped["jph"] >  wi3_thresh].copy()
        s3_flagged  = s3_below["login"].nunique()

        st.info(
            f"**{s3_flagged} associate{'s' if s3_flagged != 1 else ''}** "
            f"{'are' if s3_flagged != 1 else 'is'} at or below **{wi3_thresh} JPH** and would be removed."
        )

        if s3_above.empty:
            st.warning("No associates remain above this threshold.")
        else:
            s3_assoc = s3_above["login"].nunique()
            s3_jobs  = int(s3_above["jobs"].sum())
            s3_hours = round(float(s3_above["hours"].sum()), 2)
            s3_avg   = s3_above["jph"].mean()

            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Associates (ex. below threshold)", s3_assoc,
                      delta=f"-{s3_flagged} removed", delta_color="off")
            w2.metric("Total Jobs (ex. below threshold)", f"{s3_jobs:,}",
                      delta=f"-{oa_jobs - s3_jobs:,}", delta_color="off")
            w3.metric("Total Hours (ex. below threshold)", f"{s3_hours:,.2f}",
                      delta=f"-{oa_hours - s3_hours:,.2f}", delta_color="off")
            w4.metric("Avg JPH (projected)", f"{s3_avg:.2f}",
                      delta=f"{s3_avg - oa_avg:+.2f} vs overall", delta_color="normal")
            render_summary_table(build_summary(s3_above))

        # ── Scenario 4: Best Zone Projection ─────────────────────────────────
        st.markdown("---")
        st.markdown("#### What If Scenario 4: Best Zone Projection")
        st.caption(
            "Identifies the temp zone where each associate achieved their highest JPH "
            "(jobs ÷ hours per zone). Projects overall numbers if every associate "
            "worked all their hours in their best zone."
        )

        # Per associate per zone: computed JPH = jobs / hours
        per_az = (
            all_raw.groupby(["login", "zone"])
            .agg(level=("level", lambda x: x.mode().iloc[0]),
                 jobs =("jobs",  "sum"),
                 hours=("hours", "sum"))
            .reset_index()
        )
        per_az = per_az[per_az["hours"] > 0].copy()
        per_az["eff_jph"] = (per_az["jobs"] / per_az["hours"]).round(2)

        zones_worked = (
            per_az.groupby("login")["zone"]
            .agg(lambda x: ", ".join(sorted(set(x))))
            .reset_index()
            .rename(columns={"zone": "zones_worked"})
        )

        best_idx  = per_az.groupby("login")["eff_jph"].idxmax()
        best_zone = (
            per_az.loc[best_idx, ["login", "zone", "eff_jph"]]
            .rename(columns={"zone": "best_zone", "eff_jph": "best_jph"})
            .reset_index(drop=True)
        )

        assoc_tot = (
            all_raw.groupby("login")
            .agg(level      =("level", lambda x: x.mode().iloc[0]),
                 total_jobs =("jobs",  "sum"),
                 total_hours=("hours", "sum"))
            .reset_index()
        )
        assoc_tot = assoc_tot[assoc_tot["total_hours"] > 0].copy()
        assoc_tot["actual_jph"] = (assoc_tot["total_jobs"] / assoc_tot["total_hours"]).round(2)

        s4 = (
            assoc_tot
            .merge(best_zone[["login", "best_zone", "best_jph"]], on="login")
            .merge(zones_worked, on="login")
        )
        s4["projected_jobs"] = (s4["total_hours"] * s4["best_jph"]).round(0).astype(int)
        s4["jph_gain"]       = (s4["best_jph"] - s4["actual_jph"]).round(2)

        proj_df = pd.DataFrame({
            "login": s4["login"],
            "level": s4["level"],
            "jobs":  s4["projected_jobs"].astype(float),
            "jph":   s4["best_jph"],
            "hours": s4["total_hours"],
        })

        s4_assoc = s4["login"].nunique()
        s4_jobs  = int(s4["projected_jobs"].sum())
        s4_hours = round(float(s4["total_hours"].sum()), 2)
        s4_avg   = s4["best_jph"].mean()

        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Associates", s4_assoc)
        w2.metric("Total Jobs (projected)", f"{s4_jobs:,}",
                  delta=f"{s4_jobs - oa_jobs:+,}", delta_color="normal")
        w3.metric("Total Hours", f"{s4_hours:,.2f}")
        w4.metric("Avg JPH (projected)", f"{s4_avg:.2f}",
                  delta=f"{s4_avg - oa_avg:+.2f} vs overall", delta_color="normal")

        render_summary_table(build_summary(proj_df))

        st.markdown("**Associate Best-Zone Detail**")
        st.caption("Click one or more rows to select associates and see the projected impact of placing them in their best zone.")

        detail_df = (
            s4[["login", "level", "zones_worked", "best_zone",
                "actual_jph", "best_jph", "jph_gain", "projected_jobs"]]
            .sort_values("jph_gain", ascending=False)
            .reset_index(drop=True)
        )
        detail_display = detail_df.rename(columns={
            "login": "Login", "level": "Level", "zones_worked": "Zones Worked",
            "best_zone": "Best Zone (Place Here)", "actual_jph": "Actual JPH",
            "best_jph": "Best Zone JPH", "jph_gain": "JPH Gain",
            "projected_jobs": "Projected Jobs",
        })

        selection = st.dataframe(
            detail_display.style.format({
                "Actual JPH": "{:.2f}", "Best Zone JPH": "{:.2f}",
                "JPH Gain": "{:+.2f}", "Projected Jobs": "{:,}",
            }),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="s4_detail_selection",
        )

        selected_rows = selection.selection.rows

        # ── Selection impact ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Selection Impact**")

        if not selected_rows:
            st.info("Select one or more associates in the table above to see the projected impact.")
        else:
            selected_logins = detail_df.loc[selected_rows, "login"].tolist()
            selected_s4     = s4[s4["login"].isin(selected_logins)].copy()

            st.caption(
                f"Projecting the impact of placing **{len(selected_logins)} associate{'s' if len(selected_logins) != 1 else ''}** "
                "in their best zones while keeping all others at their actual rates."
            )

            # Show who is selected
            sel_preview = selected_s4[["login", "level", "best_zone", "actual_jph", "best_jph", "jph_gain"]].copy()
            sel_preview.columns = ["Login", "Level", "Best Zone (Place Here)", "Actual JPH", "Best Zone JPH", "JPH Gain"]
            st.dataframe(
                sel_preview.style.format({
                    "Actual JPH": "{:.2f}", "Best Zone JPH": "{:.2f}", "JPH Gain": "{:+.2f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Build projected deduped: swap selected associates to their best JPH/jobs
            impact_df = deduped.copy()
            for _, row in selected_s4.iterrows():
                mask = impact_df["login"] == row["login"]
                impact_df.loc[mask, "jph"]  = row["best_jph"]
                impact_df.loc[mask, "jobs"] = row["projected_jobs"]

            imp_assoc = impact_df["login"].nunique()
            imp_jobs  = int(impact_df["jobs"].sum())
            imp_hours = round(float(impact_df["hours"].sum()), 2)
            imp_avg   = impact_df["jph"].mean()

            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Associates Reallocated", len(selected_logins))
            w2.metric("Total Jobs (projected)", f"{imp_jobs:,}",
                      delta=f"{imp_jobs - oa_jobs:+,}", delta_color="normal")
            w3.metric("Total Hours", f"{imp_hours:,.2f}")
            w4.metric("Avg JPH (projected)", f"{imp_avg:.2f}",
                      delta=f"{imp_avg - oa_avg:+.2f} vs overall", delta_color="normal")

            render_summary_table(build_summary(impact_df))

        # ── Scenario 5: Remove Individual Associates ──────────────────────────
        st.markdown("---")
        st.markdown("#### What If Scenario 5: Remove Individual Associates")
        st.caption(
            "Click one or more associates in the table below to remove them. "
            "The overall numbers are recalculated without those associates."
        )

        assoc_table = (
            deduped[["login", "level", "jph", "jobs", "hours"]]
            .sort_values(["level", "login"])
            .reset_index(drop=True)
            .rename(columns={
                "login":  "Login",
                "level":  "Level",
                "jph":    "JPH",
                "jobs":   "Total Jobs",
                "hours":  "Total Hours",
            })
        )

        s5_sel = st.dataframe(
            assoc_table.style.format({
                "JPH":         "{:.2f}",
                "Total Jobs":  "{:,}",
                "Total Hours": "{:,.2f}",
            }),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="s5_assoc_selection",
        )

        s5_rows = s5_sel.selection.rows

        st.markdown("**Adjusted Results**")
        if not s5_rows:
            st.info("Click one or more associates in the table above to see the adjusted numbers.")
        else:
            removed_logins = assoc_table.iloc[s5_rows]["Login"].tolist()
            removed_count  = len(removed_logins)

            st.caption(
                f"Removing **{removed_count} associate{'s' if removed_count != 1 else ''}**: "
                + ", ".join(removed_logins)
            )

            s5_df = deduped[~deduped["login"].isin(removed_logins)].copy()

            if s5_df.empty:
                st.warning("No associates remain after removing the selection.")
            else:
                s5_assoc = s5_df["login"].nunique()
                s5_jobs  = int(s5_df["jobs"].sum())
                s5_hours = round(float(s5_df["hours"].sum()), 2)
                s5_avg   = s5_df["jph"].mean()

                w1, w2, w3, w4 = st.columns(4)
                w1.metric("Associates Remaining", s5_assoc,
                          delta=f"-{removed_count} removed", delta_color="off")
                w2.metric("Total Jobs", f"{s5_jobs:,}",
                          delta=f"-{oa_jobs - s5_jobs:,}", delta_color="off")
                w3.metric("Total Hours", f"{s5_hours:,.2f}",
                          delta=f"-{oa_hours - s5_hours:,.2f}", delta_color="off")
                w4.metric("Avg JPH (adjusted)", f"{s5_avg:.2f}",
                          delta=f"{s5_avg - oa_avg:+.2f} vs overall", delta_color="normal")

                render_summary_table(build_summary(s5_df))

    # ── Clear all ─────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("Clear All Results", key="btn_clear_all"):
        st.session_state["fr_zones"]   = []
        st.session_state["fr_overall"] = None
        st.session_state["fr_input_key"] += 1
        st.rerun()
