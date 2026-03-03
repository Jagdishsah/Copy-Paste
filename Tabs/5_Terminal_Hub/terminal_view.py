
import streamlit as st
from Services.app.terminal_ui import render_terminal_hub

def render(storage):
    """
    This function is called by run_tab in TMS_Ledger.py
    """
    st.header("🖥️ Terminal Hub")
    # Pass the storage object to the actual UI renderer
    render_terminal_hub(storage)
