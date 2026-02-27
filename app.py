import base64
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# UI THEME HELPERS
# ---------------------------

def get_contrast_color(hex_color):
    """Determines if white or black text has better contrast against a hex color."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def apply_scenery_style(b64_str, img_type, accent_color):
    """Comprehensive CSS targeting all UI elements for 100% visibility."""
    contrast_text = get_contrast_color(accent_color)
    
    st.markdown(
        f"""
        <style>
        /* 1. Background with Dark Tint Overlay */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                        url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* 2. Sidebar Overhaul */
        [data-testid="stSidebar"] {{
            background-color: {accent_color} !important;
            backdrop-filter: blur(20px);
        }}
        /* Force ALL sidebar text and icons to contrast color */
        [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{
            color: {contrast_text} !important;
            font-weight: 700 !important;
        }}

        /* 3. Global Text Override for Main Area */
        /* Targets headers, paragraphs, labels, and expanders */
        .main *, .main p, .main label, .main span, summary {{
            color: white !important;
            text-shadow: 2px 2px 10px rgba(0,0,0,1) !important;
        }}
        
        /* 4. Glassmorphism Chart Container */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.8) !important; 
            backdrop-filter: blur(30px) !important;
            border-radius: 28px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            padding: 40px !important;
        }}

        /* 5. Icon Visibility (Arrows, Chevrons) */
        svg {{
            fill: white !important;
        }}
        [data-testid="stSidebar"] svg {{
            fill: {contrast_text} !important;
        }}

        /* 6. Expander Box Styling */
        details {{
            background: rgba(0, 0, 0, 0.5) !important;
            border-radius: 12px !important;
            padding: 10px !important;
            margin-bottom: 10px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_readable(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title={'font': {'color': "white", 'size': 26}},
        font=dict(color="white", size=14),
        xaxis=dict(showgrid=False, tickfont=dict(color="white"), title_font=dict(color="white")),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.15)', tickfont=dict(color="white")),
        margin=dict(t=100)
    )
    return fig

def hex_to_rgba(hex_color, opacity=0.3):
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
    accent_color = st.color_picker("Pick Sidebar & Accent Color", "#00F2FF")
    st.markdown("---")
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

if bg_image:
    img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
    apply_scenery_style(img_b64, bg_image.type, accent_color)
else:
    st.markdown(f"<style>.stApp {{background: #0f172a;}}</style>", unsafe_allow_html=True)

if data_file:
    try:
        df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
        cols = df.columns
        plot_df = df.copy()
        for col in cols[:2]:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
        plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

        st.title("Data Narrative")
        fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
        fig.update_traces(line_color=accent_color, fillcolor=hex_to_rgba(accent_color, 0.45), line=dict(width=5))
        fig = make_fig_readable(fig)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with st.expander("Explore Raw Data"):
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"Error: {e}")
