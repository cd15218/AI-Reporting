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
    uploaded_image.seek(0)
    img = Image.open(uploaded_image).convert('RGB')
    img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
    dominant_color = img.getpixel((0, 0))
    return '#{:02x}{:02x}{:02x}'.format(*dominant_color)

def get_contrast_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def apply_final_fix(b64_str, img_type, auto_color):
    contrast_text = get_contrast_color(auto_color)
    
    # Injecting CSS that targets the container, not just the text
    st.markdown(
        f"""
        <style>
        /* 1. Main Background */
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:{img_type};base64,{b64_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}

        /* 2. Sidebar Isolation */
        [data-testid="stSidebar"] {{
            background-color: #0E1117 !important; /* Force a dark solid color */
            border-right: 1px solid rgba(255,255,255,0.1);
        }}
        
        /* 3. The 'Data Narrative' Ribbon - Ensures visibility without shadows */
        .title-ribbon {{
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            display: inline-block;
            margin-bottom: 20px;
        }}

        /* 4. Glassmorphism for Charts */
        [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {{
            background: rgba(15, 23, 42, 0.8) !important; 
            backdrop-filter: blur(30px) !important;
            border-radius: 24px !important;
            padding: 30px !important;
        }}

        /* 5. Fixing the Sidebar Button Text */
        .stButton>button, .stFileUploader label {{
            color: white !important;
            background-color: rgba(255,255,255,0.1) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------------------
# MAIN APP
# ---------------------------

st.set_page_config(page_title="Data Narrative Studio", layout="wide")

# Sidebar
with st.sidebar:
    st.markdown("### 🎨 Design Studio")
    bg_image = st.file_uploader("Upload Scenery Image", type=["png", "jpg", "jpeg"])
    st.divider()
    data_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

if bg_image:
    try:
        auto_color = get_dominant_color(bg_image)
        bg_image.seek(0)
        img_b64 = base64.b64encode(bg_image.getvalue()).decode("utf-8")
        apply_final_fix(img_b64, bg_image.type, auto_color)
    except Exception:
        pass

if data_file:
    try:
        df = pd.read_csv(data_file) if data_file.name.endswith('.csv') else pd.read_excel(data_file)
        
        # Using a custom HTML container for the title to bypass Streamlit's H1 styling
        st.markdown(f'''
            <div class="title-ribbon">
                <h1 style="color:white; margin:0; padding:0;">Data Narrative</h1>
            </div>
        ''', unsafe_allow_html=True)
        
        cols = df.columns
        if len(cols) >= 2:
            plot_df = df.copy()
            for col in cols[:2]:
                plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
            plot_df = plot_df.dropna(subset=[cols[0], cols[1]])

            fig = px.area(plot_df, x=cols[0], y=cols[1], title=f"Trend: {cols[1]}")
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="white"),
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
            )
            fig.update_traces(line_color="#00F2FF", fillcolor="rgba(0, 242, 255, 0.3)")
            
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Explore Raw Data"):
                st.dataframe(df)
                
    except Exception as e:
        st.error(f"Error: {e}")
