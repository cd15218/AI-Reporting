import base64
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# UI THEME HELPERS
# ---------------------------

def apply_scenery_style(b64_str, img_type):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}

        h1, h2, h3, p, span {{
            color: white !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_transparent(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False),
        font=dict(family="Inter, sans-serif", color="white", size=14)
    )
    return fig

# ---------------------------
# MAIN APP
# ---------------------------

st.set_page_config(page_title="Aesthetic Data Scenery", layout="wide")

with st.sidebar:
    st.header("🎨 Design Studio")
    bg_image = st.file_uploader("Upload Scenery Image", type=["png", "jpg", "jpeg"])
    accent_color = st.color_picker("Pick Data Accent Color", "#00F2FF")
    st.markdown("---")
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

# Handle Background
if bg_image:
    b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
    apply_scenery_style(b64, bg_image.type)
else:
    st.markdown("<style>.stApp {background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);}</style>", unsafe_allow_html=True)

# Data Handling
if data_file:
    try:
        # Check file extension to determine loading method
        if data_file.name.endswith('.csv'):
            df = pd.read_csv(data_file)
        else:
            df = pd.read_excel(data_file)
            
        st.title("Data Narrative")
        
        if df.shape[1] < 2:
            st.warning("Please upload a dataset with at least two columns for visualization.")
        else:
            # Aesthetic Area Chart
            cols = df.columns
            fig = px.area(df, x=cols[0], y=cols[1], title="Thematic Trend Analysis")
            
            # Formatting
            fig.update_traces(
                line_color=accent_color,
                fillcolor=accent_color.replace("#", "rgba(") + ",0.2)"
            )
            fig = make_fig_transparent(fig)
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
    except Exception as e:
        st.error(f"Could not process file: {e}")
else:
    st.info("Upload a background image and a dataset to see the magic.")
