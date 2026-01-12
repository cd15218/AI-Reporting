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
    # ---------------- THEME DECISION ----------------
    if mode == "Solid":
        dark = is_dark_hex(solid_hex)
    elif mode == "Gradient":
        dark = True if gradient_dark is None else gradient_dark
    else:
        dark = True

    # ---------------- COLOR TOKENS ----------------
    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#334155"

    card_bg = "rgba(2, 6, 23, 0.58)" if dark else "rgba(255, 255, 255, 0.92)"
    border = "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.16)"
    widget_bg = "rgba(255,255,255,0.06)" if dark else "rgba(15,23,42,0.06)"

    plot_paper_bg = "rgba(2, 6, 23, 0.18)" if dark else "rgba(255, 255, 255, 0.80)"
    plot_plot_bg = "rgba(2, 6, 23, 0.06)" if dark else "rgba(255, 255, 255, 0.55)"

    # BaseWeb Select menu colors
    menu_bg = "rgba(15, 23, 42, 0.96)" if dark else "rgba(255, 255, 255, 0.98)"
    option_text = "#e5e7eb" if dark else "#0f172a"
    option_hover_bg = "rgba(148, 163, 184, 0.22)" if dark else "rgba(15, 23, 42, 0.10)"
    option_selected_bg = "rgba(148, 163, 184, 0.30)" if dark else "rgba(15, 23, 42, 0.14)"
    option_selected_text = "#ffffff" if dark else "#0f172a"
    focus_ring = "rgba(148, 163, 184, 0.40)" if dark else "rgba(15, 23, 42, 0.25)"

    # ---------------- BACKGROUND (FULL PAGE) ----------------
    if mode == "Solid":
        page_bg_rule = f"background: {solid_hex} !important;"
    elif mode == "Gradient":
        page_bg_rule = f"background: {gradient_css} !important;"
    else:
        page_bg_rule = (
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
        /* Keep header so sidebar toggle works */
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Hide deploy / repo controls only */
        [data-testid="stDeployButton"],
        [data-testid="stStatusWidget"],
        [data-testid="stToolbarActions"] {{
            display: none !important;
        }}

        /* ---- Force Streamlit surfaces transparent so the page background is visible ---- */
        html, body {{
            background: transparent !important;
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {{
            background: transparent !important;
        }}

        /* ---- True full screen background layer ---- */
        body::before {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            {page_bg_rule}
            pointer-events: none;
        }}

        /* Ensure app renders above background */
        [data-testid="stAppViewContainer"] {{
            position: relative;
            z-index: 1;
        }}

        /* Layout padding */
        [data-testid="stAppViewContainer"] > .main {{
            padding-top: 0rem;
        }}

        /* Content panel */
        .block-container {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1.2rem;
            backdrop-filter: blur(8px);
        }}

        /* Global text */
        html, body, [data-testid="stAppViewContainer"] * {{
            color: {text};
        }}

        .stCaption, .stMarkdown p, .stMarkdown li {{
            color: {muted};
        }}

        /* Sidebar panel */
        section[data-testid="stSidebar"] > div {{
            background: {card_bg};
            border-right: 1px solid {border};
        }}

        /* Select input (closed state) */
        div[data-baseweb="select"] > div {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        /* IMPORTANT: do NOT style file inputs, it can break Streamlit uploader */
        textarea, input:not([type="file"]) {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        /* Uploader dropzone */
        [data-testid="stFileUploaderDropzone"] {{
            background: {widget_bg};
            border: 1px dashed {border};
            border-radius: 12px;
        }}

        /* Expanders */
        details {{
            background: {widget_bg};
            border: 1px solid {border};
            border-radius: 12px;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background: {widget_bg};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 0.6rem;
        }}

        /* Dataframe container */
        [data-testid="stDataFrame"] {{
            border: 1px solid {border};
            border-radius: 12px;
            overflow: hidden;
        }}

        /* Code blocks */
        pre, code {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 10px !important;
        }}

        /* BaseWeb Select dropdown menu */
        div[data-baseweb="popover"] div[data-baseweb="menu"] {{
            background: {menu_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"] {{
            color: {option_text} !important;
            background: transparent !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"]:hover,
        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][data-highlighted="true"],
        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][aria-selected="false"][data-highlighted="true"] {{
            background: {option_hover_bg} !important;
            color: {option_text} !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][aria-selected="true"] {{
            background: {option_selected_bg} !important;
            color: {option_selected_text} !important;
            font-weight: 600 !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"] * {{
            color: inherit !important;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            box-shadow: 0 0 0 3px {focus_ring} !important;
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

    if hasattr(fig.layout, "xaxis"):
        fig.update_xaxes(
            title_font=dict(color=theme["text"]),
            tickfont=dict(color=theme["text"]),
            gridcolor=theme["border"]
        )
    if hasattr(fig.layout, "yaxis"):
        fig.update_yaxes(
            title_font=dict(color=theme["text"]),
            tickfont=dict(color=theme["text"]),
            gridcolor=theme["border"]
        )

    return fig

# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.header("Appearance")

    bg_mode = st.selectbox("Background Type", ["Solid", "Gradient", "Image"], index=1)

    solid_palettes = {
        "Slate": "#0f172a",
        "Midnight": "#0b1020",
        "Soft Gray": "#f3f4f6",
        "Warm Cream": "#fbf7ef",
        "Forest": "#0b3d2e",
        "Ocean": "#0b3a5b",
        "Plum": "#2a1033",
    }

    solid_choice = None
    custom_solid = ""
    img_upload = None

    # Gradient builder controls
    gradient_color_a = "#0b1020"
    gradient_color_b = "#123055"
    gradient_angle = 135

    if bg_mode == "Solid":
        solid_choice = st.selectbox("Solid Palette", list(solid_palettes.keys()), index=0, key="solid_palette")
        custom_solid = st.text_input("Optional Custom Hex", value="", placeholder="#112233", key="custom_hex")

    if bg_mode == "Gradient":
        st.caption("Build a real gradient background.")
        gradient_color_a = st.color_picker("Gradient Color A", value="#0b1020", key="grad_a")
        gradient_color_b = st.color_picker("Gradient Color B", value="#123055", key="grad_b")
        gradient_angle = st.slider("Gradient Angle", 0, 360, 135, key="grad_angle")

    if bg_mode == "Image":
        img_upload = st.file_uploader("Upload Background Image", type=["png", "jpg", "jpeg", "webp"], key="bg_image")

    st.divider()
    st.header("Inputs")

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
        key="data_upload"
    )

    report_type = st.selectbox(
        "Report Type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0,
        key="report_type"
    )

    max_preview_rows = st.slider("Preview Rows", 5, 100, 25, key="preview_rows")
    max_categories = st.slider("Max Categories Per Chart", 5, 50, 20, key="max_categories")

# ---------------- APPLY THEME ----------------

solid_hex = "#0f172a"
if bg_mode == "Solid":
    solid_hex = solid_palettes.get(solid_choice or "Slate", "#0f172a")
    if custom_solid and custom_solid.strip().startswith("#") and len(custom_solid.strip()) in (4, 7):
        solid_hex = custom_solid.strip()

gradient_css = f"linear-gradient({gradient_angle}deg, {gradient_color_a} 0%, {gradient_color_b} 100%)"
gradient_dark = is_dark_gradient(gradient_color_a, gradient_color_b)

image_b64 = image_file_to_base64(img_upload)
image_mime = img_upload.type if img_upload else "image/png"

plotly_template, theme = apply_background_and_theme_css(
    bg_mode,
    solid_hex,
    gradient_css,
    image_b64,
    image_mime,
    gradient_dark
)
pio.templates.default = plotly_template

# ---------------- MAIN CONTENT ----------------

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")

if not uploaded_file:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = load_file_to_df(uploaded_file)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

df = basic_clean(df)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

st.subheader("Data Preview")
st.dataframe(df.head(max_preview_rows), use_container_width=True)

st.divider()

# ---------------- KEY STATISTICS ----------------

st.subheader("Key Statistics")

left, right = st.columns([1, 2])

with left:
    primary_numeric = st.selectbox(
        "Primary Numeric Column (KPIs)",
        options=["None"] + numeric_cols,
        key="kpi_primary_numeric"
    )

user_choices = {
    "primary_numeric": None if primary_numeric == "None" else primary_numeric,
    "scatter_x": None,
    "scatter_y": None,
    "category_volume": None,
    "category_a": None,
    "category_b": None,
    "radial_category_col": None,
    "radial_categories": [],
    "radial_mode": "count",
    "radial_value_col": None,
}

summary, visuals_kpi, numeric_df, categorical_df = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

with right:
    k1, k2, k3, k4 = st.columns(4)

    if summary["primary_numeric_column"]:
        col = summary["primary_numeric_column"]
        k1.metric(f"Average {col}", summary["mean"])
        k2.metric(f"Median {col}", summary["median"])
        k3.metric(f"Minimum {col}", summary["min"])
        k4.metric(f"Maximum {col}", summary["max"])
    else:
        k1.metric("Average", "N/A")
        k2.metric("Median", "N/A")
        k3.metric("Minimum", "N/A")
        k4.metric("Maximum", "N/A")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Total Rows", summary["rows"])
    k6.metric("Numeric Columns", summary["numeric_count"])
    k7.metric("Categorical Columns", summary["categorical_count"])
    k8.metric("Missing Cells", summary["missing_cells"])

with st.expander("Numeric Statistics Table"):
    st.dataframe(numeric_df, use_container_width=True)

with st.expander("Categorical Statistics Table"):
    st.dataframe(categorical_df, use_container_width=True)

if summary["primary_numeric_column"]:
    with st.expander("Distribution Chart", expanded=True):
        fig = get_fig(visuals_kpi, "numeric_distribution")
        if fig is not None:
            fig = apply_plotly_theme(fig, theme)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- VISUALIZATIONS ----------------

st.subheader("Visualizations")

for key, default in [
    ("scatter_x", "None"),
    ("scatter_y", "None"),
    ("cat_volume_col", "None"),
    ("cat_a", "None"),
    ("cat_b", "None"),
    ("radial_col", "None"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if "radial_mode" not in st.session_state:
    st.session_state["radial_mode"] = "Count"
if "radial_value_col" not in st.session_state:
    st.session_state["radial_value_col"] = "None"
if "radial_pick" not in st.session_state:
    st.session_state["radial_pick"] = []

scatter_ready = (
    st.session_state["scatter_x"] != "None"
    and st.session_state["scatter_y"] != "None"
    and st.session_state["scatter_x"] != st.session_state["scatter_y"]
)
cat_volume_ready = st.session_state["cat_volume_col"] != "None"
heatmap_ready = (
    st.session_state["cat_a"] != "None"
    and st.session_state["cat_b"] != "None"
    and st.session_state["cat_a"] != st.session_state["cat_b"]
)
radial_ready = st.session_state["radial_col"] != "None"

with st.expander("Numeric Comparison Scatter Plot", expanded=scatter_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("X Axis (Numeric)", options=["None"] + numeric_cols, key="scatter_x")
        st.selectbox("Y Axis (Numeric)", options=["None"] + numeric_cols, key="scatter_y")

    user_choices = {
        "primary_numeric": None,
        "scatter_x": None if st.session_state["scatter_x"] == "None" else st.session_state["scatter_x"],
        "scatter_y": None if st.session_state["scatter_y"] == "None" else st.session_state["scatter_y"],
        "category_volume": None,
        "category_a": None,
        "category_b": None,
        "radial_category_col": None,
        "radial_categories": [],
        "radial_mode": "count",
        "radial_value_col": None,
    }

    _, visuals_scatter, _, _ = build_visuals(df, report_type, user_choices, max_categories)

    with chart:
        fig = get_fig(visuals_scatter, "numeric_scatter")
        if fig is not None:
            fig = apply_plotly_theme(fig, theme)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different numeric columns to generate the scatter plot.")

with st.expander("Category Distribution Bar Chart", expanded=cat_volume_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category Column", options=["None"] + categorical_cols, key="cat_volume_col")

    user_choices = {
        "primary_numeric": None,
        "scatter_x": None,
        "scatter_y": None,
        "category_volume": None if st.session_state["cat_volume_col"] == "None" else st.session_state["cat_volume_col"],
        "category_a": None,
        "category_b": None,
        "radial_category_col": None,
        "radial_categories": [],
        "radial_mode": "count",
        "radial_value_col": None,
    }

    _, visuals_cat_vol, _, _ = build_visuals(df, report_type, user_choices, max_categories)

    with chart:
        fig = get_fig(visuals_cat_vol, "category_volume")
        if fig is not None:
            fig = apply_plotly_theme(fig, theme)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select a categorical column to generate the bar chart.")

with st.expander("Category Relationship Heatmap", expanded=heatmap_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category A", options=["None"] + categorical_cols, key="cat_a")
        st.selectbox("Category B", options=["None"] + categorical_cols, key="cat_b")

    user_choices = {
        "primary_numeric": None,
        "scatter_x": None,
        "scatter_y": None,
        "category_volume": None,
        "category_a": None if st.session_state["cat_a"] == "None" else st.session_state["cat_a"],
        "category_b": None if st.session_state["cat_b"] == "None" else st.session_state["cat_b"],
        "radial_category_col": None,
        "radial_categories": [],
        "radial_mode": "count",
        "radial_value_col": None,
    }

    _, visuals_heatmap, _, _ = build_visuals(df, report_type, user_choices, max_categories)

    with chart:
        fig = get_fig(visuals_heatmap, "category_heatmap")
        if fig is not None:
            fig = apply_plotly_theme(fig, theme)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different categorical columns to generate the heatmap.")

with st.expander("Radial Category Donut Chart", expanded=radial_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category Column", options=["None"] + categorical_cols, key="radial_col")

        selected_col = st.session_state["radial_col"]
        category_options = []
        if selected_col != "None":
            category_options = (
                df[selected_col]
                .astype("string")
                .fillna("Missing")
                .value_counts()
                .head(max_categories)
                .index
                .tolist()
            )

        st.multiselect(
            "Include Categories (Optional)",
            options=category_options,
            default=st.session_state["radial_pick"] if st.session_state["radial_pick"] else [],
            key="radial_pick"
        )

        st.selectbox(
            "Value Type",
            options=["Count", "Sum of Numeric Column"],
            key="radial_mode"
        )

        if st.session_state["radial_mode"] == "Sum of Numeric Column":
            st.selectbox(
                "Numeric Column to Sum",
                options=["None"] + numeric_cols,
                key="radial_value_col"
            )
        else:
            st.session_state["radial_value_col"] = "None"

    radial_mode = "sum" if st.session_state["radial_mode"] == "Sum of Numeric Column" else "count"
    radial_value_col = None if st.session_state["radial_value_col"] == "None" else st.session_state["radial_value_col"]

    user_choices = {
        "primary_numeric": None,
        "scatter_x": None,
        "scatter_y": None,
        "category_volume": None,
        "category_a": None,
        "category_b": None,
        "radial_category_col": None if st.session_state["radial_col"] == "None" else st.session_state["radial_col"],
        "radial_categories": st.session_state["radial_pick"],
        "radial_mode": radial_mode,
        "radial_value_col": radial_value_col,
    }

    _, visuals_radial, _, _ = build_visuals(df, report_type, user_choices, max_categories)

    with chart:
        fig = get_fig(visuals_radial, "radial_donut")
        if fig is not None:
            fig = apply_plotly_theme(fig, theme)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Colors use different shades of one base color for a cohesive look.")
        else:
            st.info("Select a categorical column to generate the donut chart.")

st.divider()

# ---------------- EXPORT ----------------

st.subheader("Export")
st.write("Download your cleaned dataset for use in other visualization tools.")

st.download_button(
    label="Download CSV",
    data=df.to_csv(index=False),
    file_name="report_data.csv",
    mime="text/csv"
)
