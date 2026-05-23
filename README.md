# Shift Planner

A Streamlit web app for managing a pick shift at an Amazon warehouse. It takes a raw roster export and produces a ready-to-use pick plan in a few clicks.

## What it does

- **Pick Planning** — uploads the shift roster, filters by shift window, assigns associates to process paths (CR, Reach, Forks, Clamp, EPJ, GTDR) using a master database, and removes VTO employees. Outputs a downloadable pick plan CSV.
- **Attendance Reconciliation** — compares who is physically in the building (time-off-task report) against who is on the shift schedule and flags discrepancies in both directions.
- **Voice Pick** — parses raw voice pick export text and reports utilization metrics, highlighting associates below 70%.
- **Equipment Utilization** — looks up the last operator for any piece of equipment by its number.
- **Database Update** — rebuilds the master associate database (`HMW1_Master_Combined_Paths.csv`) from per-path trained-list exports without overwriting unrelated certifications.

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
3. Review who is absent but scheduled and who is present but not scheduled.

### Voice Pick
1. Copy the raw text from the voice pick export.
2. Go to **Voice Pick**, paste the text, and click **Process**.
3. Review utilization metrics and download the report.

### Equipment Utilization
1. Export the equipment utilization CSV (`EquipmentUtilizationByLogIn-*.csv`).
2. Go to **Equipment Utilization** and upload the file.
3. Enter one or more equipment numbers to look up the last operator.

### Updating the Associate Database
1. Export the trained-list CSVs for each path you want to update.
2. Go to **Database Update** and upload the relevant files.
3. Click **Build Database**, review the preview, then click **Save & Activate**.

---

## Stopping the App

Press `Ctrl + C` in the terminal to stop the Streamlit server.
