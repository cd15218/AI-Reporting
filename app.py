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

def _rgb_to_hex(rgb):
    r, g, b = rgb
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b)))
    )

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

def _mix_rgb(a, b, t: float):
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t
    )

def generate_shades(base_hex: str, n: int, dark_mode: bool) -> list[str]:
    try:
        base = _hex_to_rgb(base_hex)
    except Exception:
        base = (59, 130, 246)  # fallback blue

    if dark_mode:
        target_a = base
        target_b = (245, 245, 245)
        ts = [0.05 + (i / max(1, n - 1)) * 0.75 for i in range(n)]
        rgbs = [_mix_rgb(target_a, target_b, t) for t in ts]
    else:
        target_a = (250, 250, 250)
        target_b = base
        ts = [0.20 + (i / max(1, n - 1)) * 0.70 for i in range(n)]
        rgbs = [_mix_rgb(target_a, target_b, t) for t in ts]

    return [_rgb_to_hex(rgb) for rgb in rgbs]

def build_colorscale(shades: list[str]) -> list:
    if not shades:
        return [(0.0, "#93c5fd"), (1.0, "#1d4ed8")]
    if len(shades) == 1:
        return [(0.0, shades[0]), (1.0, shades[0])]
    steps = len(shades) - 1
    return [(i / steps, c) for i, c in enumerate(shades)]

def _safe_set(obj, path: list[str], value):
    try:
        cur = obj
        for i, key in enumerate(path):
            if i == len(path) - 1:
                setattr(cur, key, value)
                return True
            nxt = getattr(cur, key, None)
            if nxt is None:
                try:
                    setattr(cur, key, {})
                    nxt = getattr(cur, key, None)
                except Exception:
                    return False
            cur = nxt
        return False
    except Exception:
        return False

def apply_background_and_theme_css(
    mode: str,
    solid_hex: str,
    gradient_css: str,
    image_b64: str,
    image_mime: str,
    gradient_dark: bool | None,
    accent_hex: str
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

        [data-testid="stDataFrame"] {{
            border: 1px solid {border};
            border-radius: 12px;
            overflow: hidden;
        }}

        pre, code {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 10px !important;
        }}

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

        .link-btn button {{
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            text-decoration: underline !important;
            cursor: pointer !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    plotly_template = "plotly_dark" if dark else "plotly_white"

    shades = generate_shades(accent_hex, 12, dark)
    continuous_scale = build_colorscale(shades)

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
        "accent": accent_hex,
        "shades": shades,
        "continuous_scale": continuous_scale,
    }

    return plotly_template, theme

def apply_plotly_theme_all(fig, theme: dict):
    """
    Forces theme styling for ALL charts, overriding existing colors set upstream.
    """
    fig.update_layout(
        template=theme["plotly_template"],
        paper_bgcolor=theme["plot_paper_bg"],
        plot_bgcolor=theme["plot_plot_bg"],
        font=dict(color=theme["text"]),
        title=dict(font=dict(color=theme["text"])),
        legend=dict(font=dict(color=theme["text"]), title=dict(font=dict(color=theme["text"]))),
        margin=dict(t=72, l=40, r=40, b=40),
        colorway=theme["shades"],
    )

    try:
        fig.update_xaxes(title_font=dict(color=theme["text"]), tickfont=dict(color=theme["text"]), gridcolor=theme["border"])
        fig.update_yaxes(title_font=dict(color=theme["text"]), tickfont=dict(color=theme["text"]), gridcolor=theme["border"])
    except Exception:
        pass

    # Sequential assignment for multi-trace figures (bars grouped, multiple scatters, etc.)
    shade_idx = 0

    for tr in fig.data:
        t = getattr(tr, "type", "") or ""

        # Pie/Donut
        if t == "pie":
            try:
                n = len(getattr(tr, "labels", []) or [])
                if n <= 0:
                    # fallback: try to infer from values
                    n = len(getattr(tr, "values", []) or []) or 12
                colors = theme["shades"][:max(1, min(n, len(theme["shades"])))]
                _safe_set(tr, ["marker", "colors"], colors)
                _safe_set(tr, ["marker", "line"], dict(width=1, color=theme["border"]))
                _safe_set(tr, ["textfont", "color"], theme["text"])
            except Exception:
                pass

        # Bar
        elif t == "bar":
            try:
                x = getattr(tr, "x", None)
                y = getattr(tr, "y", None)
                n = 0
                if x is not None:
                    n = len(x)
                elif y is not None:
                    n = len(y)
                if n <= 0:
                    # if grouped bars, each trace often represents a series — use a single shade
                    _safe_set(tr, ["marker", "color"], theme["shades"][shade_idx % len(theme["shades"])])
                else:
                    # per-category shades for a single trace bar chart
                    colors = [theme["shades"][i % len(theme["shades"])] for i in range(n)]
                    _safe_set(tr, ["marker", "color"], colors)

                _safe_set(tr, ["marker", "line"], dict(width=0.7, color=theme["border"]))
                shade_idx += 1
            except Exception:
                pass

        # Scatter
        elif t == "scatter":
            # Force accent color, even if upstream set something else
            _safe_set(tr, ["marker", "color"], theme["accent"])
            _safe_set(tr, ["marker", "line"], dict(width=0.7, color=theme["border"]))
            try:
                # If lines exist, keep them on theme too
                _safe_set(tr, ["line", "color"], theme["accent"])
            except Exception:
                pass

        # Histogram
        elif t == "histogram":
            _safe_set(tr, ["marker", "color"], theme["shades"][4] if len(theme["shades"]) > 4 else theme["accent"])
            _safe_set(tr, ["marker", "line"], dict(width=0.7, color=theme["border"]))

        # Heatmap + continuous maps
        elif t in {"heatmap", "contour", "histogram2d", "histogram2dcontour", "densitymapbox"}:
            try:
                tr.colorscale = theme["continuous_scale"]
            except Exception:
                pass

        # Box/Violin
        elif t in {"box", "violin"}:
            try:
                tr.fillcolor = theme["shades"][6] if len(theme["shades"]) > 6 else theme["accent"]
            except Exception:
                pass
            _safe_set(tr, ["line", "color"], theme["border"])

        # Fallback
        else:
            try:
                marker = getattr(tr, "marker", None)
                if marker is not None:
                    _safe_set(tr, ["marker", "color"], theme["accent"])
            except Exception:
                pass

    return fig

# ---------------- SIDEBAR ----------------

with st.sidebar:
    with st.expander("Appearance", expanded=False):
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

    st.header("Inputs")

    uploaded_file_sidebar = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
        key="data_upload_sidebar"
    )

    report_type = st.selectbox(
        "Report Type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0,
        key="report_type"
    )

    max_preview_rows = st.slider("Preview Rows", 5, 100, 25, key="preview_rows")
    max_categories = st.slider("Max Categories Per Chart", 5, 50, 20, key="max_categories")

# ---------------- APPLY THEME + CHART ACCENT ----------------

solid_hex = "#0f172a"
if bg_mode == "Solid":
    solid_hex = solid_palettes.get(solid_choice or "Slate", "#0f172a")
    if custom_solid and custom_solid.strip().startswith("#") and len(custom_solid.strip()) in (4, 7):
        solid_hex = custom_solid.strip()

gradient_css = f"linear-gradient({gradient_angle}deg, {gradient_color_a} 0%, {gradient_color_b} 100%)"
gradient_dark = is_dark_gradient(gradient_color_a, gradient_color_b)

image_b64 = image_file_to_base64(img_upload)
image_mime = img_upload.type if img_upload else "image/png"

if bg_mode == "Solid":
    accent_hex = solid_hex
elif bg_mode == "Gradient":
    accent_hex = gradient_color_b
else:
    accent_hex = "#3b82f6"

plotly_template, theme = apply_background_and_theme_css(
    bg_mode,
    solid_hex,
    gradient_css,
    image_b64,
    image_mime,
    gradient_dark,
    accent_hex
)
pio.templates.default = plotly_template

# ---------------- TITLE + TOP UPLOAD ----------------

title_left, title_right = st.columns([3, 2], vertical_alignment="center")

with title_left:
    st.markdown("# Dataset Reporting")
    st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")

with title_right:
    uploaded_file_top = st.file_uploader(
        "Upload Dataset",
        type=["csv", "xlsx", "xls"],
        key="data_upload_top",
        help="You can upload here or in the sidebar. The most recent upload will be used."
    )

uploaded_file = uploaded_file_top if uploaded_file_top is not None else uploaded_file_sidebar

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

# ---------------- DEFAULTS FOR VISUALIZATION CONTROLS ----------------

def _set_default_if_missing(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value

_set_default_if_missing("scatter_x", numeric_cols[0] if len(numeric_cols) >= 1 else "None")
_set_default_if_missing("scatter_y", numeric_cols[1] if len(numeric_cols) >= 2 else "None")
_set_default_if_missing("cat_volume_col", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
_set_default_if_missing("cat_a", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
_set_default_if_missing("cat_b", categorical_cols[1] if len(categorical_cols) >= 2 else "None")
_set_default_if_missing("radial_col", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
_set_default_if_missing("radial_mode", "Count")
_set_default_if_missing("radial_value_col", numeric_cols[0] if len(numeric_cols) >= 1 else "None")
_set_default_if_missing("radial_pick", [])

# ---------------- KEY STATISTICS (FRONT AND CENTER) ----------------

st.subheader("Key Statistics")

kpi_left, kpi_right = st.columns([1, 3])

with kpi_left:
    default_kpi_index = 1 if len(numeric_cols) > 0 else 0
    primary_numeric = st.selectbox(
        "Primary Numeric Column (KPIs)",
        options=["None"] + numeric_cols,
        index=default_kpi_index,
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

with kpi_right:
    # Add SUM metric here (Totals)
    k1, k2, k3, k4, k5 = st.columns(5)

    if summary["primary_numeric_column"]:
        col = summary["primary_numeric_column"]
        k1.metric(f"Average {col}", summary["mean"])
        k2.metric(f"Median {col}", summary["median"])
        k3.metric(f"Minimum {col}", summary["min"])
        k4.metric(f"Maximum {col}", summary["max"])
        k5.metric(f"Total {col}", summary.get("sum", "N/A"))
    else:
        k1.metric("Average", "N/A")
        k2.metric("Median", "N/A")
        k3.metric("Minimum", "N/A")
        k4.metric("Maximum", "N/A")
        k5.metric("Total", "N/A")

    k6, k7, k8, k9 = st.columns(4)
    k6.metric("Total Rows", summary["rows"])
    k7.metric("Numeric Columns", summary["numeric_count"])
    k8.metric("Categorical Columns", summary["categorical_count"])
    k9.metric("Missing Cells", summary["missing_cells"])

st.markdown("Radial Category Breakdown")

rad_controls, rad_chart = st.columns([1, 2])

with rad_controls:
    default_cat_index = 1 if len(categorical_cols) > 0 else 0
    radial_col_kpi = st.selectbox(
        "Category Column",
        options=["None"] + categorical_cols,
        index=default_cat_index,
        key="kpi_radial_col"
    )

    radial_mode_label = st.selectbox(
        "Value Type",
        options=["Count", "Sum of Numeric Column"],
        index=0,
        key="kpi_radial_mode"
    )

    radial_value_col_kpi = None
    if radial_mode_label == "Sum of Numeric Column":
        if len(numeric_cols) == 0:
            st.info("No numeric columns available to sum.")
        else:
            numeric_default_idx = 0
            if primary_numeric != "None" and primary_numeric in numeric_cols:
                numeric_default_idx = numeric_cols.index(primary_numeric)

            radial_value_col_kpi = st.selectbox(
                "Numeric Column to Sum",
                options=numeric_cols,
                index=numeric_default_idx,
                key="kpi_radial_value_col"
            )

with rad_chart:
    if radial_col_kpi != "None" and len(categorical_cols) > 0:
        radial_mode = "sum" if radial_mode_label == "Sum of Numeric Column" else "count"

        user_choices_radial_kpi = {
            "primary_numeric": None if primary_numeric == "None" else primary_numeric,
            "scatter_x": None,
            "scatter_y": None,
            "category_volume": None,
            "category_a": None,
            "category_b": None,
            "radial_category_col": radial_col_kpi,
            "radial_categories": [],
            "radial_mode": radial_mode,
            "radial_value_col": radial_value_col_kpi,
        }

        _, visuals_radial_kpi, _, _ = build_visuals(
            df=df,
            report_type=report_type,
            user_choices=user_choices_radial_kpi,
            max_categories=max_categories
        )

        fig = get_fig(visuals_radial_kpi, "radial_donut")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_kpi_radial_donut")
            st.caption("Colors use different shades of the active theme accent.")
        else:
            st.info("Select a valid category column to generate the radial chart.")
    else:
        st.info("No categorical columns found for a radial chart.")

with st.expander("Numeric Statistics Table"):
    st.dataframe(numeric_df, use_container_width=True)

with st.expander("Categorical Statistics Table"):
    st.dataframe(categorical_df, use_container_width=True)

if summary["primary_numeric_column"]:
    with st.expander("Distribution Chart", expanded=True):
        fig = get_fig(visuals_kpi, "numeric_distribution")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_kpi_distribution")

st.divider()

# ---------------- DATASET (COMPACT) ----------------

row_ct = int(df.shape[0])
col_ct = int(df.shape[1])
st.caption(f"Dataset loaded: {row_ct:,} rows • {col_ct:,} columns")

preview_clicked = False
try:
    @st.dialog("Dataset Preview")
    def _preview_dialog(df_to_show: pd.DataFrame, rows: int):
        st.dataframe(df_to_show.head(rows), use_container_width=True)
        st.caption(f"Showing the first {rows} rows.")

    c1, c2 = st.columns([1, 5], vertical_alignment="center")
    with c1:
        st.markdown('<div class="link-btn">', unsafe_allow_html=True)
        preview_clicked = st.button("Preview", key="preview_dataset_btn")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.caption("Opens a popup with a quick preview.")

    if preview_clicked:
        _preview_dialog(df, max_preview_rows)

except Exception:
    with st.expander("Preview Dataset", expanded=False):
        st.dataframe(df.head(max_preview_rows), use_container_width=True)
        st.caption(f"Showing the first {max_preview_rows} rows.")

st.divider()

# ---------------- VISUALIZATIONS ----------------

st.subheader("Visualizations")

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

    user_choices_scatter = {
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

    _, visuals_scatter, _, _ = build_visuals(df, report_type, user_choices_scatter, max_categories)

    with chart:
        fig = get_fig(visuals_scatter, "numeric_scatter")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_scatter")

with st.expander("Category Distribution Bar Chart", expanded=cat_volume_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category Column", options=["None"] + categorical_cols, key="cat_volume_col")

    user_choices_cat_vol = {
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

    _, visuals_cat_vol, _, _ = build_visuals(df, report_type, user_choices_cat_vol, max_categories)

    with chart:
        fig = get_fig(visuals_cat_vol, "category_volume")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_category_volume")

with st.expander("Category Relationship Heatmap", expanded=heatmap_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category A", options=["None"] + categorical_cols, key="cat_a")
        st.selectbox("Category B", options=["None"] + categorical_cols, key="cat_b")

    user_choices_heatmap = {
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

    _, visuals_heatmap, _, _ = build_visuals(df, report_type, user_choices_heatmap, max_categories)

    with chart:
        fig = get_fig(visuals_heatmap, "category_heatmap")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_heatmap")

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

    user_choices_radial = {
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

    _, visuals_radial, _, _ = build_visuals(df, report_type, user_choices_radial, max_categories)

    with chart:
        fig = get_fig(visuals_radial, "radial_donut")
        if fig is not None:
            fig = apply_plotly_theme_all(fig, theme)
            st.plotly_chart(fig, use_container_width=True, key="chart_radial_donut")

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
