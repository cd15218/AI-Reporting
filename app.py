# app.py
import base64
import os
import pandas as pd
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

# Assuming build_visuals is your existing logic
# from report_ai import build_visuals 

# ---------------------------
# NEW: UI THEME HELPERS
# ---------------------------

def apply_scenery_style(b64_str, img_type):
    """Injects CSS to set the background and style containers with glassmorphism."""
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        
        /* Glassmorphism container for charts */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}

        /* Make Streamlit headers readable over images */
        h1, h2, h3, p, span {{
            color: white !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_transparent(fig):
    """Removes all background colors from Plotly so the scenery shows through."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False),
    )
    return fig

# ---------------------------
# EXISTING HELPERS (MODIFIED)
# ---------------------------

def b64_image(uploaded_image):
    if not uploaded_image:
        return None, None
    return base64.b64encode(uploaded_image.getvalue()).decode("utf-8"), uploaded_image.type

# ... (Keep your hex_to_rgb, rel_lum, and color logic as is) ...

# ---------------------------
# MAIN APP
# ---------------------------

st.set_page_config(page_title="Aesthetic Data Scenery", layout="wide")

# 1. Sidebar for Aesthetic Controls
with st.sidebar:
    st.header("🎨 Design Studio")
    bg_image = st.file_uploader("Upload Scenery Image", type=["png", "jpg", "jpeg"])
    accent_color = st.color_picker("Pick Data Accent Color", "#00F2FF")
    
    st.markdown("---")
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

# 2. Handle Image/Scenery Background
if bg_image:
    img_b64, img_type = b64_image(bg_image)
    apply_scenery_style(img_b64, img_type)
else:
    # Fallback gradient if no image is uploaded
    st.markdown("<style>.stApp {background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);}</style>", unsafe_allow_html=True)

# 3. Main Logic
if data_file:
    df = pd.read_csv(data_file) # Simplified for example
    st.title("Data Narrative")
    
    # Example: Generating a visual (Using Plotly directly for this mockup)
    import plotly.express as px
    
    # Let's say we pick the first two columns for a quick aesthetic area chart
    cols = df.columns
    fig = px.area(df, x=cols[0], y=cols[1], title="Thematic Trend Analysis")
    
    # Apply our aesthetic "Scenery" treatments
    fig.update_traces(
        line_color=accent_color,
        fillcolor=f"rgba{tuple(list(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.2])}" 
    )
    
    # MUST CALL THESE TO FIT THE SCENERY
    fig = make_fig_transparent(fig)
    fig.update_layout(font=dict(family="Inter, sans-serif", color="white", size=14))
    
    # Display
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("Upload a background image and a dataset to see the magic.")
