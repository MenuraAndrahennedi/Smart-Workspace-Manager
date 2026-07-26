from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

st.set_page_config(
    page_title="Smart Workspace Manager", 
    page_icon="SWM", 
    layout="wide"
)

st.title("Smart Workspace Manager")
st.write("Welcome to the Smart Workspace Manager! This application helps you manage your workspace efficiently.")
