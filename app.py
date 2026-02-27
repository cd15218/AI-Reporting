import base64
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# UI THEME HELPERS
# ---------------------------

def apply_scenery_style(b64_str, img_type):
    """Injects CSS for fixed background and glassmorphism containers."""
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* Glassmorphism container for chart blocks */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
            margin-bottom: 25px;
        }}

        /* Typography styling for readability */
        h1, h2, h3, p, span, label, .stMarkdown {{
            color: white !important;
            text-shadow: 2px 2px 5px rgba(0,0,0,0.7);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_transparent(fig):
    """Removes standard backgrounds so the scenery shows through."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, color="white"),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False, color="white"),
    )
    return fig

def hex_to_rgba(hex_color, opacity=0.3):
    """Properly converts hex to an RGBA string Plotly can read."""
    hex_color = hex_color.lstrip('#')
    # Convert hex pairs to decimal integers
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {opacity})"

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

# 2. Handle Background Image
if bg_image:
    img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
    apply_scenery_style(img_b64, bg_image.type)
else:
    # Default dark gradient if no image is uploaded
    st.markdown(
        "<style>.stApp {background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);}</style>", 
        unsafe_allow_html=True
    )

# 3. Data Narrative Logic
if data_file:
    try:
        # Support both CSV and Excel
        if data_file.name.endswith('.csv'):
            df = pd.read_csv(data_file)
        else:
            df = pd.read_excel(data_file)
            
        st.title("Data Narrative")
        
        if len(df.columns) >= 2:
            cols = df.columns
            # Use the first two columns for a demonstration plot
            fig = px.area(df, x=cols[0], y=cols[1], title=f"Trend Analysis: {cols[1]}")
            
            # Apply our corrected accent styling
            fig.update_traces(
                line_color=accent_color,
                fillcolor=hex_to_rgba(accent_color, 0.3),
                line=dict(width=3)
            )
            
            # Clean up fonts and layout
            fig = make_fig_transparent(fig)
            fig.update_layout(
                font=dict(family="Arial, sans-serif", color="white", size=14),
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Display the aesthetic chart
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # Additional detail container
            with st.expander("Explore Raw Data"):
                st.dataframe(df.style.highlight_max(axis=0))
        else:
            st.warning("Your dataset needs at least two columns for an area chart.")
            
    except Exception as e:
        st.error(f"Could not process file: {e}")

else:
    st.info("Step 1: Upload a background. Step 2: Upload your data to see the magic.")
