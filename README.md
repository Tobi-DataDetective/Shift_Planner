# Shift Planner

A Streamlit web app for managing a pick shift at an Amazon warehouse. It takes a raw roster export and produces a ready-to-use pick plan in a few clicks, with additional tools for attendance reconciliation, voice pick analysis, equipment lookup, Rodeo planning, and multi-zone workforce performance analysis.

---

## What it does

- **Pick Planning** — uploads the shift roster, filters by shift window, assigns associates to process paths (CR, Reach, Forks, Clamp, EPJ, GTDR) using a master database, removes VTO employees, and deduplicates by Alias. Outputs a downloadable pick plan CSV.
- **Attendance Reconciliation** — compares who is physically in the building (time-off-task report) against who is on the shift schedule. Single table with a radio filter for **All**, **Present – Not Scheduled**, or **Absent – Scheduled**.
- **Voice Pick** — parses raw voice pick export text and reports utilization metrics. Associates below 70% are highlighted in a separate table.
- **Equipment Utilization** — looks up the last operator for any piece of equipment by its number.
- **Rodeo Planning** — uploads an ExSD Report and filters it by Process Path (FPP / Frozen / Chilled, include or exclude) and Work Pool status.
- **Function Rollup** — multi-zone workforce JPH and volume analysis tool. Paste data for each temp zone (Ambient, Chiller, Frozen), map columns manually, and get a breakdown by Level. Includes an Overall Analysis across all zones and four interactive what-if scenarios.
- **Database Update** — rebuilds the master associate database (`HMW1_Master_Combined_Paths.csv`) from per-path trained-list exports.

---

## Key files

| File | Purpose |
|------|---------|
| `HMW1_Master_Combined_Paths.csv` | Master associate database (Name, Login, certified Paths) |
| `HMW1_roster_*.csv` | Shift roster export — primary input for Pick Planning |
| `VTO.csv` | Daily VTO list |
| `streamlit_app/app.py` | App entry point |

---

## Setup Guide

### Prerequisites

- [Python 3.10 or newer](https://www.python.org/downloads/) — during installation, check **"Add Python to PATH"**
- [Git](https://git-scm.com/downloads) — needed to clone the repository

---

### Step 1 — Download the project

Open a terminal (Command Prompt or PowerShell) and run:

```bash
git clone https://github.com/Tobi-DataDetective/Shift_Planner.git
cd Shift_Planner
```

Or click the green **Code** button on GitHub and choose **Download ZIP**, then extract it and open a terminal inside the extracted folder.

---

### Step 2 — Create a virtual environment

```bash
python -m venv venv
```

Then activate it:

- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **Mac / Linux:**
  ```bash
  source venv/bin/activate
  ```

---

### Step 3 — Install dependencies

```bash
pip install -r streamlit_app/requirements.txt
```

---

### Step 4 — Launch the app

```bash
cd streamlit_app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Daily Operation

### Pick Planning
1. Download the shift roster (`HMW1_roster_*.csv`).
2. Upload it on the **Pick Planning** page and set the shift window (default 18:30–23:00).
3. Optionally upload `VTO.csv` to remove VTO employees.
4. Download the final pick plan CSV.

### Attendance Reconciliation
1. Export the time-off-task report (`timeOffTask-ppr-HMW1-*.csv`).
2. Upload both the time-off-task report and the pick plan CSV from above.
3. Use the radio filter to view **All**, **Present – Not Scheduled**, or **Absent – Scheduled**.
4. Download the filtered report.

### Voice Pick
1. Copy the raw text from the voice pick export.
2. Paste it on the **Voice Pick** page and click **Process**.
3. Review utilization metrics and download the report.

### Equipment Utilization
1. Export the equipment utilization CSV (`EquipmentUtilizationByLogIn-*.csv`).
2. Upload it and enter one or more equipment numbers to look up the last operator.

### Rodeo Planning
1. Export the ExSD Report CSV.
2. Upload it on **Rodeo Planning**.
3. Use the Process Path filter and Work Pool multi-select to narrow the data.
4. Download the filtered result.

### Function Rollup
1. Go to the **Function Rollup** page.
2. Paste the tab-separated dataset for your first temp zone (e.g. Ambient) into the text area.
3. Type the zone name in the **Temp Zone label** field and click **Process**.
4. In the **Column Preview**, use the 5 dropdowns to map: Login, Level, Jobs, JPH, and Hours/Time columns.
5. Click **Run Analysis** — the zone results appear below and the input clears for the next zone.
6. Repeat steps 2–5 for Chiller and Frozen.
7. Click **View Overall** to see the combined, deduplicated analysis across all zones.
8. Use the **What If Scenarios** to explore projections:
   - **Scenario 1** — remove a level entirely and see the JPH/volume impact
   - **Scenario 2** — set a target JPH for N associates in a level and see the projected overall rate
   - **Scenario 3** — slide a JPH threshold (0–75) to flag and remove low performers, see remaining metrics
   - **Scenario 4** — identifies each associate's best-performing temp zone; click rows in the detail table to select specific associates and see the projected impact of placing them in their best zones

### Updating the Associate Database
1. Export the trained-list CSVs for each path you want to update.
2. Go to **Database Update** and upload the relevant files.
3. Click **Build Database**.
4. Click **Save & Activate** to write the new database to disk.

---

## Function Rollup — Calculation Reference

### Individual Zone Analysis

Each zone is analysed independently using the **pasted JPH** value from the source report.

| Output | Formula |
|--------|---------|
| Associates | Count of rows in that zone's dataset |
| Total Jobs | Sum of the Jobs column |
| Total Hours | Sum of the Hours/Time column |
| Overall Avg JPH | Mean of the pasted JPH column across all associates |
| Avg JPH per Level | Mean of pasted JPH for associates in that level |
| % of Workforce | (Associates in level ÷ Total associates) × 100 |

### Overall Analysis

When **View Overall** is clicked, all zone datasets are stacked and deduplicated by associate login:

| Field | Deduplication Method |
|-------|---------------------|
| Level | Most frequent level across zones (mode) |
| Jobs | Sum across all zones |
| Hours | Sum across all zones |
| JPH | **Computed:** Total Jobs ÷ Total Hours (not the pasted value) |

Associates who appear in multiple zones get a single row with their combined totals and a computed rate reflecting their actual combined output.

### What If Scenario 1 — Remove Level

Filters out all associates at the selected level. Shows new Associates, Total Jobs, Total Hours, and Avg JPH with delta vs the actual overall.

### What If Scenario 2 — Target JPH

Takes the N lowest-performing associates in the selected level (sorted by actual JPH ascending) and replaces their JPH with the target value. All others remain unchanged. Recalculates the overall summary.

### What If Scenario 3 — JPH Threshold

Removes all associates with JPH ≤ the slider value (0–75). Shows how many are flagged and what the remaining workforce metrics look like.

### What If Scenario 4 — Best Zone Projection

For each associate:
1. Computes effective JPH per zone: `jobs ÷ hours` for each zone they worked in
2. Identifies their best zone (highest effective JPH)
3. Projects their output if all their total hours were spent in that zone: `projected_jobs = total_hours × best_zone_jph`
4. `jph_gain = best_zone_jph − actual_jph`

The overall projection replaces every associate's actual JPH/jobs with their best-zone equivalents.

**Interactive selection:** Click rows in the Associate Best-Zone Detail table to select specific associates. The Selection Impact section then shows what the overall numbers would look like if only those selected associates were placed in their best zones, with everyone else staying at their actual rates.

---

## Stopping the App

Press `Ctrl + C` in the terminal to stop the Streamlit server.
