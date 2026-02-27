import base64
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
import io

# ---------------------------
# COLOR & PALETTE LOGIC
# ---------------------------

def get_dominant_palette(uploaded_image):
    """Extracts the most dominant color to use as the theme's primary accent."""
    uploaded_image.seek(0)
    img = Image.open(uploaded_image).convert('RGB')
    # Resize to 1x1 to average the image colors
    img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
    dominant = img.getpixel((0, 0))
    return '#{:02x}{:02x}{:02x}'.format(*dominant)

def apply_dynamic_theme(b64_str, img_type, theme_color):
    """Redefines Streamlit core variables and forces visibility on all widgets."""
    st.markdown(
        f"""
        <style>
        /* 1. Global Variable Redefinition - Forces High Contrast */
        :root {{
            --primary-color: {theme_color};
            --background-color: #0E1117;
            --secondary-background-color: #262730;
            --text-color: #FFFFFF;
        }}

        /* 2. Isolated Page Background */
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        [data-testid="stHeader"], [data-testid="stMain"] {{
            background: transparent !important;
        }}

        /* 3. Sidebar Visibility Fix (Forces white text on ALL components) */
        [data-testid="stSidebar"] {{
            background-color: #0E1117 !important;
            border-right: 1px solid rgba(255,255,255,0.1);
        }}
        
        /* Targets the 'Browse files' button text and all sidebar labels */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] small {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}

        /* 4. Title Ribbon - Solves the 'Data Narrative' readability issue */
        .title-box {{
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(15px);
            padding: 10px 30px;
            border-radius: 12px;
            display: inline-block;
            border-left: 6px solid {theme_color};
            margin-bottom: 25px;
        }}

        /* 5. Chart Container Glassmorphism */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.9) !important; 
            backdrop-filter: blur(35px) !important;
            border-radius: 24px !important;
            padding: 40px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

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
        # 1. Sync palette with image background
        detected_theme = get_dominant_palette(bg_image)
        
        # 2. Apply theme and background
        bg_image.seek(0)
        img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
        apply_dynamic_theme(img_b64, bg_image.type, detected_theme)
        
        if data_file:
            # 3. Process and Plot
            df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
            
            # Use High-Contrast Ribbon for Title
            st.markdown(f'<div class="title-box"><h1 style="color:white;margin:0;">Data Narrative</h1></div>', unsafe_allow_html=True)
            
            cols = df.columns
            if len(cols) >= 2:
                plot_df = df.copy()
                for col in cols[:2]:
                    plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
                plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

                # 4. Plotly Graph Palette Matching
                fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white"),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)', color="white"),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.1)', color="white")
                )
                
                # Chart now uses the EXACT color from the background
                fig.update_traces(line_color=detected_theme, fillcolor=f"rgba{tuple(list(int(detected_theme.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.3])}")
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                with st.expander("Explore Raw Data"):
                    st.dataframe(df)
                    
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload imagery and data in the Design Studio to begin.")
