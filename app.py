# app.py
import streamlit as st
import pandas as pd
import base64
import plotly.io as pio
from report_ai import build_visuals

st.set_page_config(
    page_title="AI Reporting",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- HELPER FUNCTIONS ----------------

def load_file_to_df(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unsupported file type.")

def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def get_fig(visuals, key: str):
    for name, fig in visuals:
        if name == key:
            return fig
    return None

def image_file_to_base64(uploaded_image) -> str:
    if uploaded_image is None:
        return ""
    return base64.b64encode(uploaded_image.getvalue()).decode("utf-8")

def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _relative_luminance(rgb):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def is_dark_hex(hex_color: str) -> bool:
    try:
        return _relative_luminance(_hex_to_rgb(hex_color)) < 0.40
    except Exception:
        return True

def apply_background_and_theme_css(
    mode: str,
    solid_hex: str,
    gradient_css: str,
    image_b64: str,
    image_mime: str
):
    if mode == "Solid":
        dark = is_dark_hex(solid_hex)
    elif mode == "Gradient":
        dark = "ffffff" not in (gradient_css or "").lower()
    else:
        dark = True

    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#334155"
    card_bg = "rgba(2, 6, 23, 0.55)" if dark else "rgba(255, 255, 255, 0.85)"
    border = "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.15)"
    widget_bg = "rgba(255,255,255,0.06)" if dark else "rgba(15,23,42,0.06)"

    if mode == "Solid":
        bg_css = f"background: {solid_hex} !important;"
    elif mode == "Gradient":
        bg_css = f"background: {gradient_css} !important;"
    else:
        bg_css = (
            f"""
            background-image: url("data:{image_mime};base64,{image_b64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            """
            if image_b64
            else "background: #0f172a !important;"
        )

    st.markdown(
        f"""
        <style>
        /* Keep header so sidebar toggle works, but make it visually minimal */
        header[data-testid="stHeader"] {{
            background: transparent !important;
            height: 0.75rem;
        }}

        /* Hide toolbar buttons (deploy / GitHub-like controls) */
        div[data-testid="stToolbar"] {{
            visibility: hidden;
        }}

        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        html, body, [data-testid="stAppViewContainer"] {{
            {bg_css}
        }}
        [data-testid="stAppViewContainer"] > .main {{
            {bg_css}
            padding-top: 0rem;
        }}

        .block-container {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1.2rem;
            backdrop-filter: blur(8px);
        }}

        html, body, [data-testid="stAppViewContainer"] * {{
            color: {text};
        }}

        .stCaption, .stMarkdown p {{
            color: {muted};
        }}

        section[data-testid="stSidebar"] > div {{
            background: {card_bg};
            border-right: 1px solid {border};
        }}

        div[data-baseweb="select"] > div {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        textarea, input:not([type="file"]) {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            background: {widget_bg};
            border: 1px dashed {border};
            border-radius: 12px;
        }}

        details {{
            background: {widget_bg};
            border: 1px solid {border};
            border-radius: 12px;
        }}

        [data-testid="stMetric"] {{
            background: {widget_bg};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 0.6rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    return "plotly_dark" if dark else "plotly_white"

# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.header("Appearance")

    bg_mode = st.selectbox("Background type", ["Solid", "Gradient", "Image"], index=1)

    solid_palettes = {
        "Slate": "#0f172a",
        "Midnight": "#0b1020",
        "Soft Gray": "#f3f4f6",
        "Warm Cream": "#fbf7ef",
        "Forest": "#0b3d2e",
        "Ocean": "#0b3a5b",
        "Plum": "#2a1033",
    }

    gradient_presets = {
        "Midnight Blue": "linear-gradient(135deg, #0b1020, #123055)",
        "Deep Ocean": "linear-gradient(135deg, #06202b, #0b3a5b)",
        "Purple Night": "linear-gradient(135deg, #120b2a, #3b1a66)",
        "Light Studio": "linear-gradient(135deg, #ffffff, #f3f4f6)",
    }

    solid_choice = st.selectbox("Solid palette", list(solid_palettes)) if bg_mode == "Solid" else None
    custom_solid = st.text_input("Custom hex") if bg_mode == "Solid" else ""

    gradient_choice = st.selectbox("Gradient preset", list(gradient_presets)) if bg_mode == "Gradient" else None
    img_upload = st.file_uploader("Background image", ["png", "jpg", "jpeg", "webp"]) if bg_mode == "Image" else None

    st.divider()
    st.header("Inputs")

    uploaded_file = st.file_uploader("Upload CSV or Excel", ["csv", "xlsx", "xls"])
    report_type = st.selectbox("Report type", ["Overview", "Trends", "Quality Check", "Executive Summary"])
    max_preview_rows = st.slider("Preview rows", 5, 100, 25)
    max_categories = st.slider("Max categories per chart", 5, 50, 20)

# ---------------- APPLY THEME ----------------

solid_hex = solid_palettes.get(solid_choice, "#0f172a")
if custom_solid.startswith("#"):
    solid_hex = custom_solid

gradient_css = gradient_presets.get(gradient_choice, "")
image_b64 = image_file_to_base64(img_upload)
image_mime = img_upload.type if img_upload else "image/png"

plotly_template = apply_background_and_theme_css(
    bg_mode, solid_hex, gradient_css, image_b64, image_mime
)
pio.templates.default = plotly_template

# ---------------- MAIN ----------------

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate visual analytics.")

if not uploaded_file:
    st.info("Upload a dataset to begin.")
    st.stop()

df = basic_clean(load_file_to_df(uploaded_file))

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

summary, visuals, _, _ = build_visuals(
    df,
    report_type,
    {"primary_numeric": None},
    max_categories
)

for _, fig in visuals:
    fig.update_layout(template=plotly_template)
    st.plotly_chart(fig, use_container_width=True)
