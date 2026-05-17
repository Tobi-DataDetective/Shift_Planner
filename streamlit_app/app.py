import streamlit as st

st.set_page_config(page_title="Amazon Pick Planning", layout="wide")

pick_planning    = st.Page("pages/pick_planning.py",    title="Pick Planning")
attendance_recon = st.Page("pages/attendance_recon.py", title="Attendance Reconciliation")
voice_pick       = st.Page("pages/voice_pick.py",       title="Voice Pick")
database_update  = st.Page("pages/database_update.py",  title="Database Update")

pg = st.navigation([pick_planning, attendance_recon, voice_pick, database_update])
pg.run()
