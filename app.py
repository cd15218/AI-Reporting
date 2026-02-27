import base64
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
import io

# ---------------------------
# COLOR & PALETTE LOGIC
# ---------------------------

def get_dominant_color(uploaded_image):
    """Extracts the dominant color for the graph accent ONLY."""
    uploaded_image.seek(0)
    img = Image.open(uploaded_image).convert('RGB')
    img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
    dominant_color = img.getpixel((0, 0))
    return '#{:02x}{:02x}{:02x}'.format(*dominant_color)

def get_readability_color(hex_color):
    """Determines if the main page text (H1, etc.) should be Black or White."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # Standard accessibility luminance formula
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def apply_final_styling(b64_str, img_type, auto_accent):
    """Applies isolated sidebar styling and dynamic main page text with NO shadows."""
    # Main page text color flips based on the image brightness
    main_text_color = get_readability_color(auto_accent)
    
    st.markdown(
        f"""
        <style>
        /* 1. Global Theme Redefinition for Sidebar Widgets */
        :root {{
            --primary-color: {auto_accent};
            --secondary-background-color: #262730;
        }}

        /* 2. Main Page Background ONLY */
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        [data-testid="stHeader"], [data-testid="stMain"] {{
            background: transparent !important;
        }}
        
        /* 3. Sidebar: LOCKED DARK THEME (The 'Browse Files' Fix) */
        [data-testid="stSidebar"] {{
            background-color: #0E1117 !important;
            background-image: none !important;
        }}
        
        /* Force EVERYTHING in the sidebar to be White and Bold */
        [data-testid="stSidebar"] * {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            text-shadow: none !important;
        }}

        /* Targeting the internal Streamlit file uploader 'Browse files' button text specifically */
        [data-testid="stSidebar"] button p, 
        [data-testid="stSidebar"] button div div small {{
            color: #FFFFFF !important;
            opacity: 1 !important;
        }}

        /* 4. Main Page Text: Automatic Flip (Black/White, NO shadows) */
        .title-box {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(15px);
            padding: 10px 30px;
            border-radius: 12px;
            display: inline-block;
            margin-bottom: 25px;
        }}
        
        h1, h2, h3, .main p, .main label, .main span, summary {{
            color: {main_text_color} !important;
            text-shadow: none !important;
            font-weight: 700 !important;
        }}

        /* 5. Chart Glassmorphism Container */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.85) !important; 
            backdrop-filter: blur(35px) !important;
            border-radius: 24px !important;
            padding: 40px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        
        /* Icon Visibility Sync */
        svg {{ fill: {main_text_color} !important; }}
        [data-testid="stSidebar"] svg {{ fill: #FFFFFF !important; }}
        </style>
        """,
        unsafe_allow_html=True
    )

def make_fig_readable(fig):
    """Ensures chart labels remain white for the dark glass container."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white", size=14),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', color="white"),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', color="white"),
        title=dict(font=dict(color="white", size=22))
    )
    return fig

# ---------------------------
# MAIN APP
# ---------------------------

st.set_page_config(page_title="Data Narrative Studio", layout="wide")

with st.sidebar:
    st.markdown("### 🎨 Design Studio")
    bg_image = st.file_uploader("Upload Scenery Image", type=["png", "jpg", "jpeg"])
    st.divider()
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

if bg_image:
    try:
        # Detect accent color for the GRAPH ONLY
        accent_color = get_dominant_color(bg_image)
        
        bg_image.seek(0)
        img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
        
        # Apply styling: Sidebar stays dark, Main Text flips based on brightness
        apply_final_styling(img_b64, bg_image.type, accent_color)
        
        if data_file:
            # Load Data
            df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
            
            # Title Ribbon
            st.markdown('<div class="title-box"><h1>Data Narrative</h1></div>', unsafe_allow_html=True)
            
            cols = df.columns
            if len(cols) >= 2:
                plot_df = df.copy()
                for col in cols[:2]:
                    plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
                plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

                # Plotly Chart with synced accent color
                fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
                fig = make_fig_readable(fig)
                
                # Chart accents match image palette automatically
                fig.update_traces(
                    line_color=accent_color, 
                    fillcolor=f"rgba{tuple(list(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.3])}"
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                with st.expander("Explore Raw Data"):
                    st.dataframe(df)
    except Exception as e:
        st.error(f"Error: {e}")
else:
    # Default State
    auto_theme_color = "#00F2FF"
    st.markdown("<style>.stApp {background: #0f172a;}</style>", unsafe_allow_html=True)
