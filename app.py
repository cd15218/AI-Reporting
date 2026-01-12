# app.py
import base64
import os
import pandas as pd
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

from report_ai import build_visuals

st.set_page_config(
    page_title="Dataset Reporting",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# Helpers
# ---------------------------

def read_df(uploaded_file) -> pd.DataFrame:
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

def safe_len(x) -> int:
    if x is None:
        return 0
    try:
        return len(x)
    except Exception:
        try:
            return len(list(x))
        except Exception:
            return 0

def enforce_y_axis_horizontal(fig):
    if fig is None:
        return fig
    try:
        fig.update_yaxes(tickangle=0, automargin=True)
    except Exception:
        pass
    try:
        layout_updates = {}
        if hasattr(fig, "layout") and fig.layout:
            for k in list(fig.layout.keys()):
                if isinstance(k, str) and k.startswith("yaxis"):
                    layout_updates[k] = dict(tickangle=0, automargin=True)
        if layout_updates:
            fig.update_layout(**layout_updates)
    except Exception:
        pass
    return fig

def force_theme(fig, theme: dict):
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
        fig.update_xaxes(
            tickfont=dict(color=theme["text"]),
            title_font=dict(color=theme["text"]),
            gridcolor=theme["border"],
            automargin=True,
        )
        fig.update_yaxes(
            tickfont=dict(color=theme["text"]),
            title_font=dict(color=theme["text"]),
            gridcolor=theme["border"],
            automargin=True,
        )
    except Exception:
        pass

    shade_idx = 0
    for tr in fig.data:
        t = (getattr(tr, "type", "") or "").lower()

        if t == "pie":
            try:
                labels = getattr(tr, "labels", None)
                values = getattr(tr, "values", None)
                n = safe_len(labels) or safe_len(values) or 12
                tr.marker = tr.marker or {}
                tr.marker.colors = theme["shades"][:max(1, min(n, len(theme["shades"])))]
                tr.marker.line = dict(width=1, color=theme["border"])
            except Exception:
                pass

        elif t == "bar":
            try:
                tr.marker = tr.marker or {}
                x = getattr(tr, "x", None)
                y = getattr(tr, "y", None)
                n = safe_len(x) or safe_len(y)
                if n > 0:
                    tr.marker.color = [theme["shades"][i % len(theme["shades"])] for i in range(n)]
                else:
                    tr.marker.color = theme["shades"][shade_idx % len(theme["shades"])]
                tr.marker.line = dict(width=0.7, color=theme["border"])
                shade_idx += 1
            except Exception:
                pass

        elif t == "scatter":
            try:
                tr.marker = tr.marker or {}
                tr.marker.color = theme["accent"]
                tr.marker.line = dict(width=0.7, color=theme["border"])
                if getattr(tr, "mode", "") and "lines" in str(getattr(tr, "mode", "")):
                    tr.line = tr.line or {}
                    tr.line.color = theme["accent"]
            except Exception:
                pass

        elif t == "histogram":
            try:
                tr.marker = tr.marker or {}
                tr.marker.color = theme["shades"][4] if len(theme["shades"]) > 4 else theme["accent"]
                tr.marker.line = dict(width=0.7, color=theme["border"])
            except Exception:
                pass

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

def compute_numeric_stats(df: pd.DataFrame, col: str) -> dict:
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return {"sum": "N/A", "mean": "N/A", "median": "N/A", "min": "N/A", "max": "N/A"}
    return {
        "sum": float(s.sum()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "min": float(s.min()),
        "max": float(s.max()),
    }

def load_png_data_uri(path: str) -> str | None:
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                b = f.read()
            return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")
    except Exception:
        return None
    return None

# ---------------------------
# Palettes
# ---------------------------

SOLID_PALETTES = {
    "Slate": "#0f172a",
    "Charcoal": "#111827",
    "Graphite": "#1f2937",
    "Ocean": "#0b3a5b",
    "Deep Teal": "#064e4e",
    "Indigo": "#1e1b4b",
    "Cobalt": "#1e3a8a",
    "Forest": "#0b3d2e",
    "Mocha": "#2b1d15",
    "Plum": "#2a1033",
    "Burgundy": "#3f0d1f",
    "Soft Gray": "#f3f4f6",
    "Light Studio": "#f8fafc",
    "Paper White": "#ffffff",
    "Warm Cream": "#fbf7ef",
    "Stone": "#e7e5e4",
    "Sand": "#f5efe6",
    "Mist Blue": "#eef2ff",
    "Mint": "#ecfdf5",
    "Blush": "#fff1f2",
}

def _sync_solid_picker():
    choice = st.session_state.get("solid_choice", None)
    if choice and choice in SOLID_PALETTES:
        st.session_state["solid_picker"] = SOLID_PALETTES[choice]

# ---------------------------
# CSS + dropdown sticky selection
# ---------------------------

def inject_dropdown_scroll_to_selected():
    components.html(
        """
        <script>
        (function() {
          if (window.__dropdownStickyApplied) return;
          window.__dropdownStickyApplied = true;

          function scrollSelected(menuEl) {
            if (!menuEl) return;
            const selected =
              menuEl.querySelector('[role="option"][aria-selected="true"]') ||
              menuEl.querySelector('[role="option"][data-selected="true"]') ||
              menuEl.querySelector('[role="option"][aria-checked="true"]');

            if (selected && selected.scrollIntoView) {
              selected.scrollIntoView({ block: "center" });
            }
          }

          const obs = new MutationObserver((mutations) => {
            for (const m of mutations) {
              for (const node of m.addedNodes || []) {
                if (!(node instanceof HTMLElement)) continue;
                const menu =
                  node.querySelector?.('div[data-baseweb="menu"]') ||
                  (node.matches?.('div[data-baseweb="menu"]') ? node : null);
                if (menu) {
                  setTimeout(() => scrollSelected(menu), 0);
                  setTimeout(() => scrollSelected(menu), 50);
                }
              }
            }
          });

          obs.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
        """,
        height=0,
        width=0,
    )

def apply_css(bg_css: str, palette: dict, text: str, muted: str, sidebar_icon_uri: str | None):
    icon_css = ""
    if sidebar_icon_uri:
        # Try multiple selectors so it works across Streamlit versions.
        icon_css = f"""
        /* Sidebar toggle button icon attachment */
        [data-testid="stSidebarCollapsedControl"] button::after,
        [data-testid="stSidebarCollapseButton"] button::after,
        button[title="Open sidebar"]::after,
        button[title="Close sidebar"]::after {{
            content: "" !important;
            display: inline-block !important;
            width: 18px !important;
            height: 18px !important;
            margin-left: 8px !important;
            background-image: url("{sidebar_icon_uri}") !important;
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            opacity: 0.95 !important;
        }}
        """
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
        [data-testid="stAppViewContainer"] > .main {{
            background-color: transparent !important;
            padding-top: 0rem !important;
            padding-bottom: 6.5rem !important;
        }}

        .block-container {{
            background: {palette["card_bg"]};
            border: 1px solid {palette["border"]};
            border-radius: 18px;
            padding: 1.1rem;
            backdrop-filter: blur(8px);
        }}

        html, body, [data-testid="stAppViewContainer"] * {{ color: {text}; }}
        .stCaption, .stMarkdown p, .stMarkdown li {{ color: {muted}; }}

        /* Title tight spacing */
        h1 {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.08 !important;
        }}
        .title-desc-tight p {{
            margin: 0.12rem 0 0 0 !important;
            padding: 0 !important;
        }}

        /* Widgets */
        div[data-baseweb="select"] > div,
        textarea, input:not([type="file"]) {{
            background: {palette["widget_bg"]} !important;
            border: 1px solid {palette["border"]} !important;
            color: {palette["widget_text"]} !important;
        }}
        div[data-baseweb="select"] span {{
            color: {palette["widget_text"]} !important;
        }}

        div[data-baseweb="popover"] div[data-baseweb="menu"] {{
            background: {palette["menu_bg"]} !important;
            border: 1px solid {palette["border"]} !important;
            border-radius: 12px !important;
        }}
        div[data-baseweb="popover"] div[data-baseweb="menu"] * {{
            color: {palette["menu_text"]} !important;
        }}
        div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"]:hover {{
            background: {palette["hover_bg"]} !important;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            box-shadow: 0 0 0 3px {palette["focus_ring"]} !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            background: {palette["widget_bg"]};
            border: 1px dashed {palette["border"]};
            border-radius: 12px;
            padding: 0.65rem !important;
        }}
        [data-testid="stFileUploaderDropzone"] * {{
            color: {palette["widget_text"]} !important;
        }}

        [data-testid="stMetric"] {{
            background: {palette["widget_bg"]};
            border: 1px solid {palette{palette["border"]}};
            border-radius: 14px;
            padding: 0.6rem;
        }}

        button[kind="primary"], button[kind="secondary"], .stButton>button {{
            background: {palette["button_bg"]} !important;
            border: 1px solid {palette["border"]} !important;
            color: {palette["button_text"]} !important;
        }}
        .stButton>button:hover {{
            background: {palette["button_hover_bg"]} !important;
        }}

        /* Compact spacing helpers */
        .filters-tight [data-testid="stVerticalBlock"] {{
            gap: 0.35rem !important;
        }}
        .preview-autofit .stButton>button {{
            width: auto !important;
            padding: 0.35rem 0.7rem !important;
            border-radius: 999px !important;
        }}

        {icon_css}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------
# Defaults
# ---------------------------

if "bg_mode" not in st.session_state:
    st.session_state["bg_mode"] = "Gradient"
if "solid_choice" not in st.session_state:
    st.session_state["solid_choice"] = list(SOLID_PALETTES.keys())[0]
if "solid_picker" not in st.session_state:
    st.session_state["solid_picker"] = SOLID_PALETTES[st.session_state["solid_choice"]]
if "grad_a" not in st.session_state:
    st.session_state["grad_a"] = "#0b1020"
if "grad_b" not in st.session_state:
    st.session_state["grad_b"] = "#123055"
if "grad_angle" not in st.session_state:
    st.session_state["grad_angle"] = 135

# ---------------------------
# Sidebar: ONLY Page Appearance
# ---------------------------

with st.sidebar:
    st.markdown("## Page Appearance")
    st.selectbox("Background Type", ["Solid", "Gradient", "Image"], index=1, key="bg_mode")

    if st.session_state["bg_mode"] == "Solid":
        # Solid color picker directly under Background Type
        st.color_picker("Solid Color", value=st.session_state.get("solid_picker", "#0f172a"), key="solid_picker")
        st.selectbox(
            "Solid Palette",
            list(SOLID_PALETTES.keys()),
            index=list(SOLID_PALETTES.keys()).index(st.session_state.get("solid_choice", list(SOLID_PALETTES.keys())[0])),
            key="solid_choice",
            on_change=_sync_solid_picker,
        )

    elif st.session_state["bg_mode"] == "Gradient":
        st.caption("Real gradient background.")
        st.color_picker("Color A", value=st.session_state.get("grad_a", "#0b1020"), key="grad_a")
        st.color_picker("Color B", value=st.session_state.get("grad_b", "#123055"), key="grad_b")
        st.slider("Angle", 0, 360, int(st.session_state.get("grad_angle", 135)), key="grad_angle")

    elif st.session_state["bg_mode"] == "Image":
        st.file_uploader("Upload Background Image", type=["png", "jpg", "jpeg", "webp"], key="bg_image")

# ---------------------------
# Theme construction
# ---------------------------

bg_mode = st.session_state.get("bg_mode", "Gradient")
img_upload = st.session_state.get("bg_image", None)
solid_picker = st.session_state.get("solid_picker", "#0f172a")
grad_a = st.session_state.get("grad_a", "#0b1020")
grad_b = st.session_state.get("grad_b", "#123055")
grad_angle = st.session_state.get("grad_angle", 135)

img_b64, img_mime = b64_image(img_upload)

if bg_mode == "Solid":
    solid_hex = solid_picker
    dark = is_dark(solid_hex)
    bg_css = f"background: {solid_hex} !important;"
    accent = solid_hex
elif bg_mode == "Gradient":
    dark = is_dark_grad(grad_a, grad_b)
    grad_css = f"linear-gradient({grad_angle}deg, {grad_a} 0%, {grad_b} 100%)"
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

page_text = "#e5e7eb" if dark else "#0f172a"
page_muted = "#cbd5e1" if dark else "#334155"

widget_bg = "rgba(255,255,255,0.10)" if dark else "rgba(15,23,42,0.06)"
widget_text = "#e5e7eb" if dark else "#0f172a"

menu_bg = "rgba(15, 23, 42, 0.96)" if dark else "rgba(255, 255, 255, 0.98)"
menu_text = "#e5e7eb" if dark else "#0f172a"

button_bg = "rgba(255,255,255,0.12)" if dark else "rgba(15,23,42,0.08)"
button_hover_bg = "rgba(255,255,255,0.18)" if dark else "rgba(15,23,42,0.12)"
button_text = "#e5e7eb" if dark else "#0f172a"

palette = {
    "card_bg": "rgba(2, 6, 23, 0.58)" if dark else "rgba(255, 255, 255, 0.92)",
    "border": "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.16)",
    "widget_bg": widget_bg,
    "widget_text": widget_text,
    "menu_bg": menu_bg,
    "menu_text": menu_text,
    "hover_bg": "rgba(148, 163, 184, 0.22)" if dark else "rgba(15, 23, 42, 0.10)",
    "focus_ring": "rgba(148, 163, 184, 0.40)" if dark else "rgba(15, 23, 42, 0.25)",
    "button_bg": button_bg,
    "button_hover_bg": button_hover_bg,
    "button_text": button_text,
}

# Use your provided paint.png if you include it in your repo next to app.py
# If you want a different location, update this path.
sidebar_icon_uri = load_png_data_uri("paint.png")
apply_css(bg_css, palette, page_text, page_muted, sidebar_icon_uri)

inject_dropdown_scroll_to_selected()

plotly_template = "plotly_dark" if dark else "plotly_white"
pio.templates.default = plotly_template

sh = shades(accent, 12, dark)
theme = {
    "plotly_template": plotly_template,
    "paper_bg": "rgba(2, 6, 23, 0.18)" if dark else "rgba(255, 255, 255, 0.80)",
    "plot_bg": "rgba(2, 6, 23, 0.06)" if dark else "rgba(255, 255, 255, 0.55)",
    "text": page_text,
    "border": palette["border"],
    "accent": accent,
    "shades": sh,
    "colorscale": colorscale(sh),
}

# ---------------------------
# Title + description
# ---------------------------

st.markdown("# Dataset Reporting")
st.markdown("<div class='title-desc-tight'>", unsafe_allow_html=True)
st.markdown("Upload a CSV or Excel file to generate key statistics and charts.")
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Upload + filters + preview (filters between upload and preview)
# ---------------------------

left_upload, _ = st.columns([2, 6], vertical_alignment="top")

with left_upload:
    file_top = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], key="data_upload_top")

    # Filters row placed here (no "Filters" title)
    st.markdown("<div class='filters-tight'>", unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1.7, 1.1, 1.1], vertical_alignment="center")

    with r1:
        report_type = st.selectbox(
            "Report Type",
            ["Overview", "Trends", "Quality Check", "Executive Summary"],
            index=0,
            key="report_type_main",
        )

    with r2:
        max_categories = st.slider(
            "Max Categories",
            5,
            50,
            20,
            key="max_categories_main",
        )

    with r3:
        max_preview_rows = st.slider(
            "Preview Rows",
            5,
            100,
            25,
            key="max_preview_rows_main",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        @st.dialog("Dataset Preview")
        def preview_dialog(df_to_show: pd.DataFrame, rows: int):
            st.dataframe(df_to_show.head(rows), use_container_width=True)
            st.caption(f"Showing the first {rows} rows.")
    except Exception:
        preview_dialog = None

    preview_clicked = st
