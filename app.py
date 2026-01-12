# app.py
import streamlit as st
import pandas as pd
import base64
import plotly.io as pio
from report_ai import build_visuals

st.set_page_config(
    page_title="Dataset Reporting",
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
    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

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

def is_dark_gradient(hex_a: str, hex_b: str) -> bool:
    try:
        lum_a = _relative_luminance(_hex_to_rgb(hex_a))
        lum_b = _relative_luminance(_hex_to_rgb(hex_b))
        return ((lum_a + lum_b) / 2.0) < 0.40
    except Exception:
        return True

def apply_background_and_theme_css(
    mode: str,
    solid_hex: str,
    gradient_css: str,
    image_b64: str,
    image_mime: str,
    gradient_dark: bool | None
):
    if mode == "Solid":
        dark = is_dark_hex(solid_hex)
    elif mode == "Gradient":
        dark = True if gradient_dark is None else gradient_dark
    else:
        dark = True

    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#334155"

    card_bg = "rgba(2, 6, 23, 0.58)" if dark else "rgba(255, 255, 255, 0.92)"
    border = "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.16)"
    widget_bg = "rgba(255,255,255,0.06)" if dark else "rgba(15,23,42,0.06)"

    plot_paper_bg = "rgba(2, 6, 23, 0.18)" if dark else "rgba(255, 255, 255, 0.80)"
    plot_plot_bg = "rgba(2, 6, 23, 0.06)" if dark else "rgba(255, 255, 255, 0.55)"

    menu_bg = "rgba(15, 23, 42, 0.96)" if dark else "rgba(255, 255, 255, 0.98)"
    option_text = "#e5e7eb" if dark else "#0f172a"
    option_hover_bg = "rgba(148, 163, 184, 0.22)" if dark else "rgba(15, 23, 42, 0.10)"
    option_selected_bg = "rgba(148, 163, 184, 0.30)" if dark else "rgba(15, 23, 42, 0.14)"
    option_selected_text = "#ffffff" if dark else "#0f172a"
    focus_ring = "rgba(148, 163, 184, 0.40)" if dark else "rgba(15, 23, 42, 0.25)"

    if mode == "Solid":
        bg_style = f"background: {solid_hex} !important;"
    elif mode == "Gradient":
        bg_style = f"background-image: {gradient_css} !important; background-attachment: fixed !important;"
    else:
        if image_b64:
            bg_style = f"""
                background-image: url("data:{image_mime};base64,{image_b64}") !important;
                background-size: cover !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
            """
        else:
            bg_style = "background: #0f172a !important;"

    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        [data-testid="stDeployButton"],
        [data-testid="stStatusWidget"],
        [data-testid="stToolbarActions"] {{
            display: none !important;
        }}

        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {{
            {bg_style}
        }}

        [data-testid="stAppViewContainer"] {{
            background-color: transparent !important;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            background-color: transparent !important;
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

        .stCaption, .stMarkdown p, .stMarkdown li {{
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

    plotly_template = "plotly_dark" if dark else "plotly_white"

    theme = {
        "dark": dark,
        "text": text,
        "muted": muted,
        "border": border,
        "card_bg": card_bg,
        "widget_bg": widget_bg,
        "plot_paper_bg": plot_paper_bg,
        "plot_plot_bg": plot_plot_bg,
        "plotly_template": plotly_template,
    }

    return plotly_template, theme

def apply_plotly_theme(fig, theme: dict):
    fig.update_layout(
        template=theme["plotly_template"],
        paper_bgcolor=theme["plot_paper_bg"],
        plot_bgcolor=theme["plot_plot_bg"],
        font=dict(color=theme["text"]),
        title=dict(font=dict(color=theme["text"])),
        legend=dict(font=dict(color=theme["text"]), title=dict(font=dict(color=theme["text"]))),
        margin=dict(t=72, l=40, r=40, b=40),
    )
    return fig

# ---------------- MAIN CONTENT ----------------

st.title("Dataset Reporting")
st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")
