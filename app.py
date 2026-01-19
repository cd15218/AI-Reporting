# app.py
import streamlit as st
import pandas as pd
import base64
import plotly.io as pio
import re
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")

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
    data = uploaded_image.getvalue()
    return base64.b64encode(data).decode("utf-8")

# ---------------- READABILITY HELPERS ----------------
def _hex_to_rgb(hex_color: str):
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    if len(h) != 6:
        raise ValueError("Bad hex")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _relative_luminance(rgb):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    a = _relative_luminance(_hex_to_rgb(hex_a))
    b = _relative_luminance(_hex_to_rgb(hex_b))
    l1, l2 = (a, b) if a >= b else (b, a)
    return (l1 + 0.05) / (l2 + 0.05)

def _extract_hexes(s: str):
    if not s:
        return []
    return re.findall(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", s)

def _is_dark_like_from_colors(hex_list) -> bool:
    if not hex_list:
        return True
    lums = []
    for hx in hex_list:
        try:
            lums.append(_relative_luminance(_hex_to_rgb(hx)))
        except Exception:
            pass
    if not lums:
        return True
    return (sum(lums) / len(lums)) < 0.40

def _safe_text_for_bg(bg_hex: str):
    light_text = "#e5e7eb"
    dark_text = "#0f172a"
    try:
        cr_light = _contrast_ratio(bg_hex, light_text)
        cr_dark = _contrast_ratio(bg_hex, dark_text)
        return light_text if cr_light >= cr_dark else dark_text
    except Exception:
        return light_text

def _filter_solid_palette(pal: dict, min_ratio: float = 4.5):
    safe = {}
    for name, hx in pal.items():
        try:
            txt = _safe_text_for_bg(hx)
            if _contrast_ratio(hx, txt) >= min_ratio:
                safe[name] = hx
        except Exception:
            pass
    return safe

def _filter_gradients(presets: dict, min_ratio: float = 4.5):
    safe = {}
    for name, css in presets.items():
        hexes = _extract_hexes(css)
        if not hexes:
            continue

        try:
            dark_like = _is_dark_like_from_colors(hexes)
            if dark_like:
                rep = min(hexes, key=lambda h: _relative_luminance(_hex_to_rgb(h)))
                txt = "#e5e7eb"
            else:
                rep = max(hexes, key=lambda h: _relative_luminance(_hex_to_rgb(h)))
                txt = "#0f172a"

            if _contrast_ratio(rep, txt) >= min_ratio:
                safe[name] = css
        except Exception:
            continue

    return safe

def apply_background_and_theme_css(
    mode: str,
    solid_hex: str,
    gradient_css: str,
    image_b64: str,
    image_mime: str
):
    if mode == "Solid":
        bg_for_theme = solid_hex
        dark = _is_dark_like_from_colors([bg_for_theme])
    elif mode == "Gradient":
        stops = _extract_hexes(gradient_css)
        dark = _is_dark_like_from_colors(stops)
        bg_for_theme = (
            min(stops, key=lambda h: _relative_luminance(_hex_to_rgb(h))) if dark
            else max(stops, key=lambda h: _relative_luminance(_hex_to_rgb(h)))
        ) if stops else "#0f172a"
    else:
        dark = True
        bg_for_theme = "#0f172a"

    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#334155"

    main_panel_bg = "rgba(2, 6, 23, 0.62)" if dark else "rgba(255, 255, 255, 0.90)"
    sidebar_panel_bg = "rgba(2, 6, 23, 0.72)" if dark else "rgba(255, 255, 255, 0.94)"

    border = "rgba(148, 163, 184, 0.40)" if dark else "rgba(15, 23, 42, 0.18)"
    widget_bg = "rgba(255,255,255,0.08)" if dark else "rgba(15,23,42,0.06)"

    menu_bg = "rgba(2, 6, 23, 0.98)" if dark else "rgba(255, 255, 255, 0.98)"
    menu_text = "#e5e7eb" if dark else "#0f172a"
    menu_hover_bg = "rgba(148, 163, 184, 0.18)" if dark else "rgba(15, 23, 42, 0.08)"

    try:
        if _contrast_ratio(bg_for_theme, text) < 3.0:
            dark = True
            text = "#e5e7eb"
            muted = "#cbd5e1"
            main_panel_bg = "rgba(2, 6, 23, 0.62)"
            sidebar_panel_bg = "rgba(2, 6, 23, 0.72)"
            border = "rgba(148, 163, 184, 0.40)"
            widget_bg = "rgba(255,255,255,0.08)"
            menu_bg = "rgba(2, 6, 23, 0.98)"
            menu_text = "#e5e7eb"
            menu_hover_bg = "rgba(148, 163, 184, 0.18)"
    except Exception:
        pass

    if mode == "Solid":
        bg_css = f"background: {solid_hex} !important;"
    elif mode == "Gradient":
        bg_css = f"background: {gradient_css} !important;"
    else:
        if not image_b64:
            bg_css = "background: #0f172a !important;"
        else:
            bg_css = f"""
            background-image: url("data:{image_mime};base64,{image_b64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            """

    st.markdown(
        f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            {bg_css}
        }}
        [data-testid="stAppViewContainer"] > .main {{
            {bg_css}
        }}

        .block-container {{
            background: {main_panel_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 18px;
            padding: 1.2rem 1.2rem;
            backdrop-filter: blur(8px);
        }}

        section[data-testid="stSidebar"] > div {{
            background: {sidebar_panel_bg} !important;
            border-right: 1px solid {border} !important;
        }}

        /* Keep text readable without breaking BaseWeb dropdown internals */
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stAppViewContainer"] .main * {{
            color: {text};
        }}
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] * {{
            color: {text};
        }}

        .stCaption, .stMarkdown p, .stMarkdown li {{
            color: {muted} !important;
        }}

        /* Widget surfaces */
        div[data-baseweb="select"] > div {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}
        textarea, input {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        /* Dropdown menus and popovers: make them opaque and readable
           This is what fixes the washed out menu in your screenshot */
        div[data-baseweb="popover"] {{
            z-index: 100000 !important;
        }}
        div[data-baseweb="popover"] * {{
            color: {menu_text} !important;
        }}
        ul[role="listbox"], div[role="listbox"] {{
            background: {menu_bg} !important;
            border: 1px solid {border} !important;
            box-shadow: 0 16px 40px rgba(0,0,0,0.35) !important;
            backdrop-filter: blur(10px) !important;
        }}
        li[role="option"] {{
            background: transparent !important;
        }}
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {{
            background: {menu_hover_bg} !important;
        }}

        /* Buttons */
        button[kind], button {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
        }}

        /* File uploader readability */
        [data-testid="stFileUploader"] small {{
            color: {muted} !important;
        }}

        /* Expanders */
        details {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 12px;
            padding: 0.35rem 0.6rem;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background: {widget_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 14px;
            padding: 0.6rem;
        }}

        /* Dataframe container */
        [data-testid="stDataFrame"] {{
            border: 1px solid {border} !important;
            border-radius: 12px;
            overflow: hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    return "plotly_dark" if dark else "plotly_white"

# ---------------- SIDEBAR: APPEARANCE + INPUTS ----------------
with st.sidebar:
    st.header("Appearance")

    bg_mode = st.selectbox(
        "Background type",
        ["Solid", "Gradient", "Image"],
        index=1
    )

    solid_palettes_raw = {
        "Slate": "#0f172a",
        "Midnight": "#0b1020",
        "Soft Gray": "#f3f4f6",
        "Warm Cream": "#fbf7ef",
        "Forest": "#0b3d2e",
        "Ocean": "#0b3a5b",
        "Plum": "#2a1033",
    }
    solid_palettes = _filter_solid_palette(solid_palettes_raw, min_ratio=4.5)
    if not solid_palettes:
        solid_palettes = {"Slate": "#0f172a"}

    gradient_presets_raw = {
        "Midnight Blue": "linear-gradient(135deg, #0b1020 0%, #123055 55%, #0b1020 100%)",
        "Deep Ocean": "linear-gradient(135deg, #06202b 0%, #0b3a5b 55%, #06202b 100%)",
        "Purple Night": "linear-gradient(135deg, #120b2a 0%, #3b1a66 55%, #120b2a 100%)",
        "Forest Fade": "linear-gradient(135deg, #061a14 0%, #0b3d2e 55%, #061a14 100%)",
        "Light Studio": "linear-gradient(135deg, #ffffff 0%, #f3f4f6 60%, #ffffff 100%)",
    }
    gradient_presets = _filter_gradients(gradient_presets_raw, min_ratio=4.5)
    if not gradient_presets:
        gradient_presets = {
            "Midnight Blue": "linear-gradient(135deg, #0b1020 0%, #123055 55%, #0b1020 100%)"
        }

    solid_choice = None
    custom_solid = ""
    gradient_choice = None
    img_upload = None

    if bg_mode == "Solid":
        solid_choice = st.selectbox("Solid palette", list(solid_palettes.keys()), index=0)
        custom_solid = st.text_input("Optional custom hex", value="", placeholder="#112233")

    if bg_mode == "Gradient":
        gradient_choice = st.selectbox("Gradient preset", list(gradient_presets.keys()), index=0)

    if bg_mode == "Image":
        img_upload = st.file_uploader("Upload background image", type=["png", "jpg", "jpeg", "webp"])
        st.caption("Tip: large images look best. The content panel stays readable.")

    st.divider()
    st.header("Inputs")

    uploaded_file_sidebar = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
        key="data_upload_sidebar"
    )

    report_type = st.selectbox(
        "Report type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0
    )

    max_preview_rows = st.slider("Preview rows", 5, 100, 25)
    max_categories = st.slider("Max categories per chart", 5, 50, 20)

# Resolve background settings
solid_hex = "#0f172a"
if bg_mode == "Solid":
    solid_hex = solid_palettes.get(solid_choice or "Slate", "#0f172a")
    if custom_solid:
        cs = custom_solid.strip()
        if cs.startswith("#") and len(cs) in (4, 7):
            try:
                _hex_to_rgb(cs)
                txt = _safe_text_for_bg(cs)
                if _contrast_ratio(cs, txt) >= 4.5:
                    solid_hex = cs
            except Exception:
                pass

gradient_css = gradient_presets.get(
    gradient_choice or next(iter(gradient_presets.keys())),
    next(iter(gradient_presets.values()))
)

image_b64 = ""
image_mime = "image/png"
if bg_mode == "Image" and img_upload is not None:
    image_b64 = image_file_to_base64(img_upload)
    image_mime = img_upload.type or "image/png"

plotly_template = apply_background_and_theme_css(
    bg_mode,
    solid_hex,
    gradient_css,
    image_b64,
    image_mime
)
pio.templates.default = plotly_template

# ---------------- MAIN PAGE UPLOAD (ALSO INCLUDED HERE) ----------------
st.subheader("Upload")
uploaded_file_main = st.file_uploader(
    "Upload CSV or Excel (optional, same as sidebar)",
    type=["csv", "xlsx", "xls"],
    key="data_upload_main"
)

uploaded_file = uploaded_file_sidebar or uploaded_file_main

# ---------------- LOAD DATA ----------------
if not uploaded_file:
    st.info("Upload a file to get started.")
    st.stop()

try:
    df = load_file_to_df(uploaded_file)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

df = basic_clean(df)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

st.subheader("Data preview")
st.dataframe(df.head(max_preview_rows), use_container_width=True)

st.divider()

# ---------------- KEY STATISTICS ----------------
st.subheader("Key statistics")

left, right = st.columns([1, 2])

with left:
    primary_numeric = st.selectbox(
        "Primary numeric column (KPIs)",
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
    k5.metric("Total rows", summary["rows"])
    k6.metric("Numeric columns", summary["numeric_count"])
    k7.metric("Categorical columns", summary["categorical_count"])
    k8.metric("Missing cells", summary["missing_cells"])

with st.expander("Numeric statistics table"):
    st.dataframe(numeric_df, use_container_width=True)

with st.expander("Categorical statistics table"):
    st.dataframe(categorical_df, use_container_width=True)

if summary["primary_numeric_column"]:
    with st.expander("Numeric distribution chart", expanded=True):
        fig = get_fig(visuals_kpi, "numeric_distribution")
        if fig is not None:
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- ACCORDION STYLE CHART SECTIONS ----------------
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

with st.expander("Numeric comparison scatter", expanded=scatter_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("X axis (numeric)", options=["None"] + numeric_cols, key="scatter_x")
        st.selectbox("Y axis (numeric)", options=["None"] + numeric_cols, key="scatter_y")

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
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different numeric columns to generate the scatter chart.")

with st.expander("Categorical volume chart", expanded=cat_volume_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category column", options=["None"] + categorical_cols, key="cat_volume_col")

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
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select a categorical column to generate a category volume chart.")

with st.expander("Categorical comparison heatmap", expanded=heatmap_ready):
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
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different categorical columns to generate a comparison heatmap.")

with st.expander("Radial category chart (donut)", expanded=radial_ready):
    controls, chart = st.columns([1, 2])

    with controls:
        st.selectbox("Category column", options=["None"] + categorical_cols, key="radial_col")

        selected_col = st.session_state["radial_col"]
        category_options = []
        if selected_col != "None":
            category_options = (
                df[selected_col].astype("string").fillna("Missing").value_counts().head(max_categories).index.tolist()
            )

        st.multiselect(
            "Include categories (optional)",
            options=category_options,
            default=st.session_state["radial_pick"] if st.session_state["radial_pick"] else [],
            key="radial_pick"
        )

        st.selectbox(
            "Value type",
            options=["Count", "Sum of numeric column"],
            key="radial_mode"
        )

        if st.session_state["radial_mode"] == "Sum of numeric column":
            st.selectbox(
                "Numeric column to sum",
                options=["None"] + numeric_cols,
                key="radial_value_col"
            )
        else:
            st.session_state["radial_value_col"] = "None"

    radial_mode = "sum" if st.session_state["radial_mode"] == "Sum of numeric column" else "count"
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
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Colors are different shades of one base color for a cohesive look.")
        else:
            st.info("Select a categorical column to generate the radial chart.")

st.divider()

# ---------------- EXPORT ----------------
st.subheader("Export")
st.write("Download your cleaned dataset for use in GraphMaker.ai or other visualization tools.")

st.download_button(
    label="Download CSV",
    data=df.to_csv(index=False),
    file_name="report_data.csv",
    mime="text/csv"
)
