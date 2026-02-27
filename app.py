import base64
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# UI THEME HELPERS
# ---------------------------

def apply_scenery_style(b64_str, img_type):
    """Injects high-contrast CSS for readability over complex backgrounds."""
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* Sidebar: High-opacity white for legible controls */
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.92) !important;
            backdrop-filter: blur(15px);
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{
            color: #0f172a !important; /* Deep navy text */
            font-weight: 700 !important;
        }}

        /* Chart Container: Darkened glass to make white text pop */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.7); 
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 45px;
            margin-top: 20px;
        }}

        /* Title Typography: Thick shadows for bright background areas */
        .main h1, .main h2, .main h
