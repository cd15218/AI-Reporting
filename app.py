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
        .main h1, .main h2, .main h3, .main p, .main span, .main label {{
            color: white !important;
            text-shadow: 3px 3px 12px rgba(0,0,0,1) !important;
            font-weight: 700 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_readable(fig):
    """Fixes contrast for graph titles, axis labels, and ticks."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        # Explicitly setting the Chart Title to pure white
        title={
            'font': {'color': "white", 'size': 26, 'family': "Inter, sans-serif"},
            'x': 0.0,
            'xanchor': 'left'
        },
        font=dict(color="white", size=15),
        xaxis=dict(
            showgrid=False, 
            zeroline=False, 
            tickfont=dict(color="white", size=13),
            title_font=dict(color="white", size=16)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.15)', 
            zeroline=False, 
            tickfont=dict(color="white", size=13),
            title_font=dict(color="white", size=16)
        ),
        margin=dict(t=100, b=50, l=50, r=50)
    )
    return fig

def hex_to_rgba(hex_color, opacity=0.3):
    """Converts hex to proper Plotly RGBA format."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"

# ---------------------------
# MAIN APP
# ---------------------------

st.set_page_config(page_title="Data Narrative Studio", layout="wide")

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
        # Load Data
        df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
        
        # Numeric Cleaning to prevent float/str errors
        cols = df.columns
        plot_df = df.copy()
        for col in cols[:2]:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
        plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

        st.title("Data Narrative")
        
        # Create Area Chart
        fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
        
        # Apply Aesthetic Styling
        fig.update_traces(
            line_color=accent_color,
            fillcolor=hex_to_rgba(accent_color, 0.45),
            line=dict(width=5)
        )
        
        # Final Readability Pass
        fig = make_fig_readable(fig)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with st.expander("Explore Raw Data"):
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"Error processing data: {e}")
else:
    st.info("Upload your background and dataset in the sidebar to begin.")
