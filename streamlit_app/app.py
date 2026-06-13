import streamlit as st

st.set_page_config(page_title="Amazon Pick Planning", layout="wide")

pick_planning         = st.Page("pages/pick_planning.py",         title="Pick Planning")
attendance_recon      = st.Page("pages/attendance_recon.py",      title="Attendance Reconciliation")
voice_pick            = st.Page("pages/voice_pick.py",            title="Voice Pick")
equipment_utilization = st.Page("pages/equipment_utilization.py", title="Equipment Utilization")
rodeo_planning        = st.Page("pages/rodeo_planning.py",        title="Rodeo Planning")
database_update       = st.Page("pages/database_update.py",       title="Database Update")
function_rollup       = st.Page("pages/function_rollup.py",       title="Function Rollup")

pg = st.navigation([pick_planning, attendance_recon, voice_pick, equipment_utilization, rodeo_planning, function_rollup, database_update])
pg.run()
