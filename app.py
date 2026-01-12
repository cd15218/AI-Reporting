# app.py
import base64
import pandas as pd
import plotly.io as pio
import streamlit as st

from report_ai import build_visuals


st.set_page_config(
    page_title="Dataset Reporting",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# Small, reusable helpers
# ---------------------------

def read_df(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Upload a CSV or Excel file.")
    df = df.dropna(axis=1, how="all").drop_duplicates()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def b64_image(uploaded_image) -> tuple[str, str]:
    if not uploaded_image:
        return "", "image/png"
    return base64.b64encode(uploaded_image.getvalue()).decode("utf-8"), uploaded_image.type

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rel_lum(rgb: tuple[int, int, int]) -> float:
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def is_dark(hex_color: str) -> bool:
    try:
        return rel_lum(hex_to_rgb(hex_color)) < 0.40
    except Exception:
        return True

def is_dark_grad(a: str, b: str) -> bool:
    try:
        return ((rel_lum(hex_to_rgb(a)) + rel_lum(hex_to_rgb(b))) / 2.0) < 0.40
    except Exception:
        return True

def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )

def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"

def shades(base_hex: str, n: int, dark_mode: bool) -> list[str]:
    try:
        base = hex_to_rgb(base_hex)
    except Exception:
        base = (59, 130, 246)
    if dark_mode:
        ts = [0.05 + (i / max(1, n - 1)) * 0.75 for i in range(n)]
        rgbs = [mix(base, (245, 245, 245), t) for t in ts]
    else:
        ts = [0.20 + (i / max(1, n - 1)) * 0.70 for i in range(n)]
        rgbs = [mix((250, 250, 250), base, t) for t in ts]
    return [rgb_to_hex(x) for x in rgbs]

def colorscale(sh: list[str]) -> list[tuple[float, str]]:
    if not sh:
        return [(0.0, "#93c5fd"), (1.0, "#1d4ed8")]
    if len(sh) == 1:
        return [(0.0, sh[0]), (1.0, sh[0])]
    steps = len(sh) - 1
    return [(i / steps, c) for i, c in enumerate(sh)]

def get_fig(visuals, name: str):
    for k, fig in visuals:
        if k == name:
            return fig
    return None

def force_theme(fig, theme: dict):
    """
    Forces ALL chart colors to match the active theme.
    Bar: per category shades
    Scatter: accent
    Heatmap: continuous colorscale
    """
    fig.update_layout(
        template=theme["plotly_template"],
        paper_bgcolor=theme["paper_bg"],
        plot_bgcolor=theme["plot_bg"],
        font=dict(color=theme["text"]),
        title=dict(font=dict(color=theme["text"])),
        legend=dict(font=dict(color=theme["text"]), title=dict(font=dict(color=theme["text"]))),
        margin=dict(t=70, l=35, r=35, b=35),
        colorway=theme["shades"],
    )
    try:
        fig.update_xaxes(tickfont=dict(color=theme["text"]), title_font=dict(color=theme["text"]), gridcolor=theme["border"])
        fig.update_yaxes(tickfont=dict(color=theme["text"]), title_font=dict(color=theme["text"]), gridcolor=theme["border"])
    except Exception:
        pass

    shade_idx = 0
    for tr in fig.data:
        t = (getattr(tr, "type", "") or "").lower()

        if t == "pie":
            n = len(getattr(tr, "labels", []) or []) or len(getattr(tr, "values", []) or []) or 12
            tr.marker = tr.marker or {}
            tr.marker.colors = theme["shades"][:max(1, min(n, len(theme["shades"])))]
            tr.marker.line = dict(width=1, color=theme["border"])

        elif t == "bar":
            tr.marker = tr.marker or {}
            x = getattr(tr, "x", None)
            y = getattr(tr, "y", None)
            n = len(x) if x is not None else (len(y) if y is not None else 0)
            if n > 0:
                tr.marker.color = [theme["shades"][i % len(theme["shades"])] for i in range(n)]
            else:
                tr.marker.color = theme["shades"][shade_idx % len(theme["shades"])]
            tr.marker.line = dict(width=0.7, color=theme["border"])
            shade_idx += 1

        elif t == "scatter":
            tr.marker = tr.marker or {}
            tr.marker.color = theme["accent"]
            tr.marker.line = dict(width=0.7, color=theme["border"])
            if getattr(tr, "mode", "") and "lines" in str(getattr(tr, "mode", "")):
                tr.line = tr.line or {}
                tr.line.color = theme["accent"]

        elif t == "histogram":
            tr.marker = tr.marker or {}
            tr.marker.color = theme["shades"][4] if len(theme["shades"]) > 4 else theme["accent"]
            tr.marker.line = dict(width=0.7, color=theme["border"])

        elif t in {"heatmap", "contour", "histogram2d", "histogram2dcontour"}:
            try:
                tr.colorscale = theme["colorscale"]
            except Exception:
                pass

        else:
            marker = getattr(tr, "marker", None)
            if marker is not None:
                try:
                    marker.color = theme["accent"]
                except Exception:
                    pass

    return fig

def apply_css(bg_css: str, dark: bool, palette: dict):
    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#334155"
    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        [data-testid="stDeployButton"], [data-testid="stStatusWidget"], [data-testid="stToolbarActions"] {{ display:none !important; }}

        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {{
            {bg_css}
        }}

        [data-testid="stAppViewContainer"] {{ background-color: transparent !important; }}
        [data-testid="stAppViewContainer"] > .main {{ background-color: transparent !important; padding-top: 0rem; }}

        .block-container {{
            background: {palette["card_bg"]};
            border: 1px solid {palette["border"]};
            border-radius: 18px;
            padding: 1.2rem;
            backdrop-filter: blur(8px);
        }}

        html, body, [data-testid="stAppViewContainer"] * {{ color: {text}; }}
        .stCaption, .stMarkdown p, .stMarkdown li {{ color: {muted}; }}

        section[data-testid="stSidebar"] > div {{
            background: {palette["card_bg"]};
            border-right: 1px solid {palette["border"]};
        }}

        div[data-baseweb="select"] > div,
        textarea, input:not([type="file"]) {{
            background: {palette["widget_bg"]} !important;
            border: 1px solid {palette["border"]} !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            background: {palette["widget_bg"]};
            border: 1px dashed {palette["border"]};
            border-radius: 12px;
        }}

        [data-testid="stMetric"] {{
            background: {palette["widget_bg"]};
            border: 1px solid {palette["border"]};
            border-radius: 14px;
            padding: 0.6rem;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] {{
            background: {palette["menu_bg"]} !important;
            border: 1px solid {palette["border"]} !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"]:hover {{
            background: {palette["hover_bg"]} !important;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            box-shadow: 0 0 0 3px {palette["focus_ring"]} !important;
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
        unsafe_allow_html=True,
    )

# ---------------------------
# Sidebar
# ---------------------------

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

        solid_choice = "Slate"
        custom_solid = ""
        img_upload = None

        grad_a = "#0b1020"
        grad_b = "#123055"
        grad_angle = 135

        if bg_mode == "Solid":
            solid_choice = st.selectbox("Solid Palette", list(solid_palettes.keys()), index=0)
            custom_solid = st.text_input("Optional Custom Hex", value="", placeholder="#112233")

        if bg_mode == "Gradient":
            st.caption("Real gradient background.")
            grad_a = st.color_picker("Gradient Color A", value=grad_a)
            grad_b = st.color_picker("Gradient Color B", value=grad_b)
            grad_angle = st.slider("Gradient Angle", 0, 360, grad_angle)

        if bg_mode == "Image":
            img_upload = st.file_uploader("Upload Background Image", type=["png", "jpg", "jpeg", "webp"])

    st.header("Inputs")
    file_sidebar = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"], key="data_upload_sidebar")
    report_type = st.selectbox("Report Type", ["Overview", "Trends", "Quality Check", "Executive Summary"], index=0)
    max_preview_rows = st.slider("Preview Rows", 5, 100, 25)
    max_categories = st.slider("Max Categories Per Chart", 5, 50, 20)

# ---------------------------
# Theme construction
# ---------------------------

solid_hex = solid_palettes.get(solid_choice, "#0f172a")
if custom_solid and custom_solid.strip().startswith("#") and len(custom_solid.strip()) in (4, 7):
    solid_hex = custom_solid.strip()

grad_css = f"linear-gradient({grad_angle}deg, {grad_a} 0%, {grad_b} 100%)"
grad_dark = is_dark_grad(grad_a, grad_b)

img_b64, img_mime = b64_image(img_upload)

if bg_mode == "Solid":
    dark = is_dark(solid_hex)
    bg_css = f"background: {solid_hex} !important;"
    accent = solid_hex
elif bg_mode == "Gradient":
    dark = grad_dark
    bg_css = f"background-image: {grad_css} !important; background-attachment: fixed !important;"
    accent = grad_b
else:
    dark = True
    if img_b64:
        bg_css = (
            f'background-image: url("data:{img_mime};base64,{img_b64}") !important;'
            "background-size: cover !important;"
            "background-position: center !important;"
            "background-repeat: no-repeat !important;"
            "background-attachment: fixed !important;"
        )
    else:
        bg_css = "background: #0f172a !important;"
    accent = "#3b82f6"

palette = {
    "card_bg": "rgba(2, 6, 23, 0.58)" if dark else "rgba(255, 255, 255, 0.92)",
    "border": "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.16)",
    "widget_bg": "rgba(255,255,255,0.06)" if dark else "rgba(15,23,42,0.06)",
    "menu_bg": "rgba(15, 23, 42, 0.96)" if dark else "rgba(255, 255, 255, 0.98)",
    "hover_bg": "rgba(148, 163, 184, 0.22)" if dark else "rgba(15, 23, 42, 0.10)",
    "focus_ring": "rgba(148, 163, 184, 0.40)" if dark else "rgba(15, 23, 42, 0.25)",
}

apply_css(bg_css, dark, palette)

plotly_template = "plotly_dark" if dark else "plotly_white"
pio.templates.default = plotly_template

sh = shades(accent, 12, dark)
theme = {
    "plotly_template": plotly_template,
    "paper_bg": "rgba(2, 6, 23, 0.18)" if dark else "rgba(255, 255, 255, 0.80)",
    "plot_bg": "rgba(2, 6, 23, 0.06)" if dark else "rgba(255, 255, 255, 0.55)",
    "text": "#e5e7eb" if dark else "#0f172a",
    "border": palette["border"],
    "accent": accent,
    "shades": sh,
    "colorscale": colorscale(sh),
}

# ---------------------------
# Title and upload
# ---------------------------

left, right = st.columns([3, 2], vertical_alignment="center")
with left:
    st.markdown("# Dataset Reporting")
    st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")
with right:
    file_top = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], key="data_upload_top")

uploaded = file_top if file_top is not None else file_sidebar
if not uploaded:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = read_df(uploaded)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

# Defaults that never start as None when possible
def ensure(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value

ensure("scatter_x", numeric_cols[0] if len(numeric_cols) >= 1 else "None")
ensure("scatter_y", numeric_cols[1] if len(numeric_cols) >= 2 else "None")
ensure("cat_volume_col", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
ensure("cat_a", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
ensure("cat_b", categorical_cols[1] if len(categorical_cols) >= 2 else "None")
ensure("radial_col", categorical_cols[0] if len(categorical_cols) >= 1 else "None")
ensure("radial_mode", "Count")
ensure("radial_value_col", numeric_cols[0] if len(numeric_cols) >= 1 else "None")
ensure("radial_pick", [])

# ---------------------------
# Key Statistics
# ---------------------------

st.subheader("Key Statistics")

kpi_left, kpi_right = st.columns([1, 3])
with kpi_left:
    default_idx = 1 if len(numeric_cols) > 0 else 0
    primary_numeric = st.selectbox(
        "Primary Numeric Column (KPIs)",
        options=["None"] + numeric_cols,
        index=default_idx,
        key="kpi_primary_numeric",
    )

user_choices_kpi = {
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
    user_choices=user_choices_kpi,
    max_categories=max_categories,
)

with kpi_right:
    a, b, c, d, e = st.columns(5)
    if summary.get("primary_numeric_column"):
        col = summary["primary_numeric_column"]
        a.metric(f"Average {col}", summary.get("mean", "N/A"))
        b.metric(f"Median {col}", summary.get("median", "N/A"))
        c.metric(f"Minimum {col}", summary.get("min", "N/A"))
        d.metric(f"Maximum {col}", summary.get("max", "N/A"))
        e.metric(f"Total {col}", summary.get("sum", "N/A"))
    else:
        a.metric("Average", "N/A")
        b.metric("Median", "N/A")
        c.metric("Minimum", "N/A")
        d.metric("Maximum", "N/A")
        e.metric("Total", "N/A")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Total Rows", summary.get("rows", df.shape[0]))
    r2.metric("Numeric Columns", summary.get("numeric_count", len(numeric_cols)))
    r3.metric("Categorical Columns", summary.get("categorical_count", len(categorical_cols)))
    r4.metric("Missing Cells", summary.get("missing_cells", int(df.isna().sum().sum())))

st.markdown("Radial Category Breakdown")
rad_controls, rad_chart = st.columns([1, 2])

with rad_controls:
    default_cat_idx = 1 if len(categorical_cols) > 0 else 0
    radial_col_kpi = st.selectbox(
        "Category Column",
        options=["None"] + categorical_cols,
        index=default_cat_idx,
        key="kpi_radial_col",
    )
    radial_mode_label = st.selectbox(
        "Value Type",
        options=["Count", "Sum of Numeric Column"],
        index=0,
        key="kpi_radial_mode",
    )

    radial_value_col_kpi = None
    if radial_mode_label == "Sum of Numeric Column":
        if numeric_cols:
            default_num_idx = numeric_cols.index(primary_numeric) if primary_numeric in numeric_cols else 0
            radial_value_col_kpi = st.selectbox(
                "Numeric Column to Sum",
                options=numeric_cols,
                index=default_num_idx,
                key="kpi_radial_value_col",
            )
        else:
            st.info("No numeric columns available to sum.")

with rad_chart:
    if radial_col_kpi != "None" and categorical_cols:
        radial_mode = "sum" if radial_mode_label == "Sum of Numeric Column" else "count"
        _, visuals_radial_kpi, _, _ = build_visuals(
            df=df,
            report_type=report_type,
            user_choices={
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
            },
            max_categories=max_categories,
        )
        fig = get_fig(visuals_radial_kpi, "radial_donut")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_kpi_radial_donut")
            st.caption("Colors use different shades of the active theme accent.")
        else:
            st.info("Select a valid category column to generate the radial chart.")
    else:
        st.info("No categorical columns found for a radial chart.")

with st.expander("Numeric Statistics Table"):
    st.dataframe(numeric_df, use_container_width=True)
with st.expander("Categorical Statistics Table"):
    st.dataframe(categorical_df, use_container_width=True)

if summary.get("primary_numeric_column"):
    with st.expander("Distribution Chart", expanded=True):
        fig = get_fig(visuals_kpi, "numeric_distribution")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_kpi_distribution")

st.divider()

# ---------------------------
# Dataset compact preview
# ---------------------------

st.caption(f"Dataset loaded: {df.shape[0]:,} rows • {df.shape[1]:,} columns")

try:
    @st.dialog("Dataset Preview")
    def preview_dialog(df_to_show: pd.DataFrame, rows: int):
        st.dataframe(df_to_show.head(rows), use_container_width=True)
        st.caption(f"Showing the first {rows} rows.")

    c1, c2 = st.columns([1, 5], vertical_alignment="center")
    with c1:
        st.markdown('<div class="link-btn">', unsafe_allow_html=True)
        open_preview = st.button("Preview", key="preview_dataset_btn")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.caption("Opens a popup with a quick preview.")
    if open_preview:
        preview_dialog(df, max_preview_rows)
except Exception:
    with st.expander("Preview Dataset", expanded=False):
        st.dataframe(df.head(max_preview_rows), use_container_width=True)

st.divider()

# ---------------------------
# Visualizations
# ---------------------------

st.subheader("Visualizations")

with st.expander("Numeric Comparison Scatter Plot", expanded=(st.session_state["scatter_x"] != "None" and st.session_state["scatter_y"] != "None")):
    controls, chart = st.columns([1, 2])
    with controls:
        st.selectbox("X Axis (Numeric)", options=["None"] + numeric_cols, key="scatter_x")
        st.selectbox("Y Axis (Numeric)", options=["None"] + numeric_cols, key="scatter_y")
    _, visuals, _, _ = build_visuals(
        df,
        report_type,
        {
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
        },
        max_categories,
    )
    with chart:
        fig = get_fig(visuals, "numeric_scatter")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_scatter")
        else:
            st.info("Select two different numeric columns to generate the scatter plot.")

with st.expander("Category Distribution Bar Chart", expanded=(st.session_state["cat_volume_col"] != "None")):
    controls, chart = st.columns([1, 2])
    with controls:
        st.selectbox("Category Column", options=["None"] + categorical_cols, key="cat_volume_col")
    _, visuals, _, _ = build_visuals(
        df,
        report_type,
        {
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
        },
        max_categories,
    )
    with chart:
        fig = get_fig(visuals, "category_volume")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_category_volume")
        else:
            st.info("Select a categorical column to generate the bar chart.")

with st.expander("Category Relationship Heatmap", expanded=(st.session_state["cat_a"] != "None" and st.session_state["cat_b"] != "None" and st.session_state["cat_a"] != st.session_state["cat_b"])):
    controls, chart = st.columns([1, 2])
    with controls:
        st.selectbox("Category A", options=["None"] + categorical_cols, key="cat_a")
        st.selectbox("Category B", options=["None"] + categorical_cols, key="cat_b")
    _, visuals, _, _ = build_visuals(
        df,
        report_type,
        {
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
        },
        max_categories,
    )
    with chart:
        fig = get_fig(visuals, "category_heatmap")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_heatmap")
        else:
            st.info("Select two different categorical columns to generate the heatmap.")

with st.expander("Radial Category Donut Chart", expanded=(st.session_state["radial_col"] != "None")):
    controls, chart = st.columns([1, 2])
    with controls:
        st.selectbox("Category Column", options=["None"] + categorical_cols, key="radial_col")

        selected_col = st.session_state["radial_col"]
        opts = []
        if selected_col != "None":
            opts = (
                df[selected_col]
                .astype("string")
                .fillna("Missing")
                .value_counts()
                .head(max_categories)
                .index
                .tolist()
            )

        st.multiselect("Include Categories (Optional)", options=opts, default=st.session_state["radial_pick"], key="radial_pick")
        st.selectbox("Value Type", ["Count", "Sum of Numeric Column"], key="radial_mode")

        if st.session_state["radial_mode"] == "Sum of Numeric Column":
            st.selectbox("Numeric Column to Sum", options=["None"] + numeric_cols, key="radial_value_col")
        else:
            st.session_state["radial_value_col"] = "None"

    radial_mode = "sum" if st.session_state["radial_mode"] == "Sum of Numeric Column" else "count"
    radial_value_col = None if st.session_state["radial_value_col"] == "None" else st.session_state["radial_value_col"]

    _, visuals, _, _ = build_visuals(
        df,
        report_type,
        {
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
        },
        max_categories,
    )

    with chart:
        fig = get_fig(visuals, "radial_donut")
        if fig is not None:
            st.plotly_chart(force_theme(fig, theme), use_container_width=True, key="chart_radial_donut")

st.divider()

# ---------------------------
# Export
# ---------------------------

st.subheader("Export")
st.write("Download your cleaned dataset for use in other visualization tools.")
st.download_button(
    "Download CSV",
    data=df.to_csv(index=False),
    file_name="report_data.csv",
    mime="text/csv",
)
