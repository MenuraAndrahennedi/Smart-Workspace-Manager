import streamlit as st

from backend.utils.logging_config import configure_logging

configure_logging()

st.set_page_config(
    page_title="Smart Workspace Manager", 
    page_icon="SWM", 
    layout="wide"
)

st.title("Smart Workspace Manager")
st.write("Welcome to the Smart Workspace Manager! This application helps you manage your workspace efficiently.")
