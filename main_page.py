import streamlit as st

st.set_page_config(page_title="Veterinary Clinic Appointment Scheduler", layout="wide")

st.markdown("# Purfect timing 🐾 🎈")

st.page_link( "pages/customer_booking.py", label="- Booking form", icon="📅")
st.page_link( "pages/optimum_scheduling.py", label="- Schedule analysis", icon="📊")
