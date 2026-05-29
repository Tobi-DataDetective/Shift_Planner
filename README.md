# Shift Planner

A Streamlit web app for managing a pick shift at an Amazon warehouse. It takes a raw roster export and produces a ready-to-use pick plan in a few clicks.

## What it does

- **Pick Planning** — uploads the shift roster, filters by shift window, assigns associates to process paths (CR, Reach, Forks, Clamp, EPJ, GTDR) using a master database, removes VTO employees, and deduplicates by Alias. Outputs a downloadable pick plan CSV.
- **Attendance Reconciliation** — compares who is physically in the building (time-off-task report) against who is on the shift schedule. Single table with a radio filter for **All**, **Present – Not Scheduled**, or **Absent – Scheduled**. Login is resolved from both the DB and the pick plan for maximum coverage.
- **Voice Pick** — parses raw voice pick export text and reports utilization metrics. Total Associates card shows overall average utilization coloured green (≥ 70%) or red (< 70%). Associates below 70% are highlighted in a separate table.
- **Equipment Utilization** — looks up the last operator for any piece of equipment by its number.
- **Rodeo Planning** — uploads an ExSD Report and filters it by Process Path (FPP / Frozen / Chilled, include or exclude) and Work Pool status. Live table and download.
- **Database Update** — rebuilds the master associate database (`HMW1_Master_Combined_Paths.csv`) from per-path trained-list exports. Displays all associates in a single table with a radio filter for **All Associates** or **Multi-path Associates** only.

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

You should see `(venv)` appear at the start of your terminal prompt.

---

### Step 3 — Install dependencies

```bash
pip install -r streamlit_app/requirements.txt
```

This installs Streamlit and Pandas — the only two libraries the app needs.

---

### Step 4 — Launch the app

```bash
cd streamlit_app
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## Daily Operation

### Pick Planning
1. Download the shift roster from the scheduling system (`HMW1_roster_*.csv`).
2. Go to the **Pick Planning** page and upload the roster file.
3. Set the shift time window (default 18:30 – 23:00).
4. Optionally upload `VTO.csv` to remove VTO employees.
5. Download the final pick plan CSV.

### Attendance Reconciliation
1. Export the time-off-task report (`timeOffTask-ppr-HMW1-*.csv`).
2. Go to **Attendance Reconciliation** and upload both the time-off-task report and the pick plan CSV from the step above.
3. Use the radio filter to view **All**, **Present – Not Scheduled**, or **Absent – Scheduled** associates.
4. Download the filtered report as a CSV.

### Voice Pick
1. Copy the raw text from the voice pick export.
2. Go to **Voice Pick**, paste the text, and click **Process**.
3. Review utilization metrics and download the report.

### Equipment Utilization
1. Export the equipment utilization CSV (`EquipmentUtilizationByLogIn-*.csv`).
2. Go to **Equipment Utilization** and upload the file.
3. Enter one or more equipment numbers to look up the last operator.

### Rodeo Planning
1. Export the ExSD Report CSV.
2. Go to **Rodeo Planning** and upload the file.
3. Use the **Process Path** filter (Include/Exclude toggle + FPP / Frozen / Chilled checkboxes) and the **Work Pool** multi-select to narrow the data.
4. The table updates live — download the filtered result as a CSV.

### Updating the Associate Database
1. Export the trained-list CSVs for each path you want to update.
2. Go to **Database Update** and upload the relevant files.
3. Click **Build Database** — metrics and the full associate table appear immediately.
4. Use the radio filter to switch between **All Associates** and **Multi-path Associates**.
5. Click **Save & Activate** to write the new database to disk.

---

## Stopping the App

Press `Ctrl + C` in the terminal to stop the Streamlit server.
