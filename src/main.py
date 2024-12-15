import streamlit as st
from db import db
from os import environ
from os.path import join

if "demo_db" not in st.session_state.keys():
    st.session_state["demo_db"] = db(str(join(
        environ.get("DEMO_HOME"), 
        environ.get("DEMO_DB_NAME")
    )))

demo_db = st.session_state["demo_db"]

st.title('Terminals availability')

# Selecting parking
parking_name = st.selectbox(
    "Parking name", 
    options=[items[0] for items in demo_db.get_parking_names()]
    )

# Selecting time frame
min_value = demo_db.get_min_date()
max_value = demo_db.get_max_date()
date_from = st.date_input(
    "Start date", 
    value=min_value, 
    min_value=min_value, 
    max_value=max_value
)
date_to = st.date_input(
    "End date", 
    value=max_value, 
    min_value=min_value, 
    max_value=max_value
)

df = demo_db.get_sla(parking_name, date_from, date_to)

# Show terminals
if st.button("Show"):
    df = demo_db.get_sla(parking_name, date_from, date_to)
    st.table(df)