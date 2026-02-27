import base64
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# UI THEME HELPERS
# ---------------------------

def apply_scenery_style(b64_str, img_type):
    """Injects CSS for fixed background and high-contrast glassmorphism."""
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* Sidebar Styling for Readability */
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(10px);
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{
            color: #1e1b4b !important; /* Dark blue for sidebar text */
            text-shadow: none !important;
        }}

        /* Darker Glassmorphism container for charts */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(0, 0, 0, 0.5); /* Increased opacity for text contrast */
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            margin-bottom: 25px;
        }}

        /* Main Area Typography */
        .main h1, .main h2, .main h3, .main p, .main span, .main label {{
            color: white !important;
            text-shadow: 2px 2px 8px rgba(0,0,0,1); /* Heavier shadow for readability */
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_readable(fig):
    """Optimizes Plotly axes for dark glassmorphism containers."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False, 
            zeroline=False, 
            color="white",
            tickfont=dict(size=12, color="white"),
            titlefont=dict(size=14, color="white")
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.2)', 
            zeroline=False, 
            color="white",
            tickfont=dict(size=12, color="white"),
            titlefont=dict(size=14, color="white")
        ),
    )
    return fig

def hex_to_rgba(hex_color, opacity=0.3):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"

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

if bg_image:
    img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
    apply_scenery_style(img_b64, bg_image.type)
else:
    st.markdown("<style>.stApp {background: #0f172a;}</style>", unsafe_allow_html=True)

if data_file:
    try:
        df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
        
        # Data Cleaning for the Float vs Str error
        cols = df.columns
        plot_df = df.copy()
        for col in cols[:2]:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
        plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

        st.title("Data Narrative")
        
        # Create Area Chart
        fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
        
        # Style the Plot
        fig.update_traces(
            line_color=accent_color,
            fillcolor=hex_to_rgba(accent_color, 0.4),
            line=dict(width=4)
        )
        
        # Apply Readability Fixes
        fig = make_fig_readable(fig)
        fig.update_layout(font=dict(family="Inter, sans-serif", color="white"))
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with st.expander("Explore Raw Data"):
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload your background and dataset in the Design Studio sidebar.")
