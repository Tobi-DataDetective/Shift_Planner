# Amazon Pick Planning — Project Log

## What This Project Does

A Python data-processing pipeline that builds a cleaned, assignment-ready list of associates for a pick shift.

**Flow:**

1. Load shift attendance → filter to the 18:30–23:00 window → deduplicate
2. Merge attendance with `pick_reach_final.csv` to get each person's process path (Pick/Reach) and JPH (jobs per hour)
3. Remove VTO (Voluntary Time Off) employees
4. Output a sorted final list by Path

---

## Input Files

| File                                         | Source                                | Purpose                                      |
| -------------------------------------------- | ------------------------------------- | -------------------------------------------- |
| `Attendance.csv`                             | Downloaded from shift schedule system | Raw attendance with Alias, Name, Shift Start |
| `pick_reach_final.csv`                       | Maintained manually                   | Maps Names → Path (Pick/Reach) + JPH rating  |
| `VTO.csv`                                    | Daily VTO list                        | Employee logins to exclude from planning     |
| `in_house.csv`                               | TBD                                   | (purpose to be documented)                   |
| `HMW1 Master Trained List(Center rider).csv` | TBD                                   | Master trained associate list                |

---

## Output Files (Generated)

| File                             | Contents                                                                  |
| -------------------------------- | ------------------------------------------------------------------------- |
| `attendance_cleaned.csv`         | Filtered + deduplicated attendance (Section 1 output)                     |
| `attendance_with_pick_reach.csv` | Attendance merged with path/JPH data (Section 2 output)                   |
| `attendance_without_vto.csv`     | Final list with VTO associates removed, sorted by Path (Section 3 output) |

---

## Script Structure (`script.py`)

- **Section 1** — Load `Attendance.csv`, keep Alias/Name/Shift Start, filter 18:30–23:00, deduplicate by name (earliest shift wins)
- **Section 2** — Left-join cleaned attendance with `pick_reach_final.csv` on Names, keep Alias/Names/Path/JPH
- **Section 3** — Remove any associate whose Alias appears in `VTO.csv["Employee Login"]`, sort by Path

---

## Key Columns

- `Alias` — employee login ID (used for VTO matching)
- `Names` — full name (used for pick_reach lookup)
- `Path` — process path assignment (e.g., Pick, Reach)
- `JPH` — jobs per hour rate

---

## Change Log

| Date       | Change                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------ |
| 2026-05-16 | Initial project setup; script.py has all 3 sections working end-to-end                                       |
| 2026-05-16 | Created `streamlit_app/` folder with full single-page Streamlit app (app.py + requirements.txt)              |
| 2026-05-16 | Restructured to multi-page app: app.py is now the nav entry point; each page lives in `streamlit_app/pages/` |

---

## Notes / Known Issues

- `pick_reach_final.csv` must be kept up to date as associates are trained on new paths — unmatched names will have NaN for Path/JPH
- Names matching between Attendance and pick_reach is case/space sensitive; both are `.str.strip()`-ed but not lowercased — ensure consistent casing in `pick_reach_final.csv`
- The old commented-out code at the top of `script.py` (pre-Alias version) can be deleted once the current version is confirmed stable
