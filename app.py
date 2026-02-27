import base64
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
import io

# ---------------------------
# COLOR & AESTHETIC LOGIC
# ---------------------------

def get_dominant_color(uploaded_image):
    """Extracts the most dominant color from the background image."""
    uploaded_image.seek(0)
    img = Image.open(uploaded_image).convert('RGB')
    img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
    dominant_color = img.getpixel((0, 0))
    return '#{:02x}{:02x}{:02x}'.format(*dominant_color)

def get_contrast_color(hex_color):
    """Determines if white or black text has better contrast against a hex color."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def apply_auto_scenery_style(b64_str, img_type, auto_color):
    """Isolates background and fixes 'Data Narrative' contrast issues."""
    contrast_text = get_contrast_color(auto_color)
    # Determine the glow color for the main title (white for dark backgrounds)
    glow_color = "rgba(0,0,0,0.9)" if contrast_text == "#FFFFFF" else "rgba(255,255,255,0.8)"
    
    st.markdown(
        f"""
        <style>
        /* 1. Main Page Background ONLY */
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        [data-testid="stHeader"], [data-testid="stMain"] {{
            background: transparent !important;
        }}
        
        /* 2. Sidebar: SOLID background, isolated from image */
        [data-testid="stSidebar"] {{
            background-color: {auto_color} !important;
            background-image: none !important;
        }}
        
        /* Sidebar Text & 'Browse Files' Fix */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] button p {{
            color: {contrast_text} !important;
            font-weight: 700 !important;
        }}

        /* 3. Data Narrative Title: FORCED COLOR & GLOW */
        [data-testid="stHeader"] h1, .main h1 {{
            color: {auto_color} !important;
            text-shadow: 2px 2px 15px {glow_color}, 0px 0px 10px {glow_color} !important;
            font-weight: 800 !important;
            font-size: 4rem !important;
            transition: color 0.5s ease;
        }}
        
        /* 4. Global Text Visibility */
        .main p, .main label, .main span, summary, h2, h3 {{
            color: white !important;
            text-shadow: 2px 2px 10px rgba(0,0,0,1) !important;
        }}
        
        /* 5. Chart Glassmorphism Container */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.8) !important; 
            backdrop-filter: blur(30px) !important;
            border-radius: 28px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            padding: 40px !important;
        }}

        /* 6. Icon/Expander Fixes */
        svg {{ fill: white !important; }}
        [data-testid="stSidebar"] svg {{ fill: {contrast_text} !important; }}

        details {{
            background: rgba(0, 0, 0, 0.6) !important;
            border-radius: 12px !important;
            padding: 10px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_readable(fig):
    """Standardizes Plotly fonts for high-contrast visibility."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title={'font': {'color': 'white', 'size': 26}, 'x': 0.05},
        font=dict(color="white", size=14),
        xaxis=dict(showgrid=False, tickfont=dict(color="white"), title_font=dict(color="white")),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)', tickfont=dict(color="white")),
        margin=dict(t=100, b=50)
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
    st.markdown("---")
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

if bg_image:
    try:
        # Detect palette color
        auto_theme_color = get_dominant_color(bg_image)
        
        # Prepare background
        bg_image.seek(0)
        img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
        
        # Apply styles
        apply_auto_scenery_style(img_b64, bg_image.type, auto_theme_color)
    except Exception as e:
        st.error(f"UI Error: {e}")
else:
    auto_theme_color = "#00F2FF"
    st.markdown("<style>.stApp {background: #0f172a;}</style>", unsafe_allow_html=True)

if data_file:
    try:
        df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
        
        cols = df.columns
        if len(cols) >= 2:
            plot_df = df.copy()
            for col in cols[:2]:
                plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
            plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

            st.title("Data Narrative")
            
            fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend Analysis: {cols[1]}")
            fig.update_traces(
                line_color=auto_theme_color, 
                fillcolor=hex_to_rgba(auto_theme_color, 0.45), 
                line=dict(width=5)
            )
            
            fig = make_fig_readable(fig)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            with st.expander("Explore Raw Data"):
                st.dataframe(df)
        else:
            st.warning("Upload a dataset with at least two columns.")
            
    except Exception as e:
        st.error(f"Data Error: {e}")
else:
    st.info("Upload your background and dataset to begin.")
