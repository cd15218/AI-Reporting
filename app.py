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
# Sticky dropdown selection everywhere
# ---------------------------

def inject_dropdown_scroll_to_selected():
    components.html(
        """
        <script>
        (function() {
          if (window.__dropdownStickyAppliedV3) return;
          window.__dropdownStickyAppliedV3 = true;

          function getMenus() {
            return Array.from(document.querySelectorAll('div[data-baseweb="menu"]'));
          }

          function findSelected(menuEl) {
            if (!menuEl) return null;

            let sel =
              menuEl.querySelector('[role="option"][aria-selected="true"]') ||
              menuEl.querySelector('[role="option"][data-selected="true"]') ||
              menuEl.querySelector('[role="option"][aria-checked="true"]');

            if (!sel) sel = menuEl.querySelector('[aria-selected="true"]') || menuEl.querySelector('[aria-checked="true"]');

            if (!sel) {
              const opts = menuEl.querySelectorAll('[role="option"]');
              for (const o of opts) {
                const cls = (o.className || "").toString().toLowerCase();
                if (cls.includes("selected") || cls.includes("active")) { sel = o; break; }
              }
            }
            return sel;
          }

          function scrollToSelected(menuEl) {
            const sel = findSelected(menuEl);
            if (sel && sel.scrollIntoView) {
              sel.scrollIntoView({ block: "center" });
            }
          }

          function scrollAllMenus() {
            const menus = getMenus();
            for (const m of menus) scrollToSelected(m);
          }

          function scheduleScroll() {
            requestAnimationFrame(() => scrollAllMenus());
            setTimeout(scrollAllMenus, 30);
            setTimeout(scrollAllMenus, 90);
            setTimeout(scrollAllMenus, 180);
            setTimeout(scrollAllMenus, 320);
          }

          const addObs = new MutationObserver((mutations) => {
            let sawSomething = false;
            for (const m of mutations) {
              for (const node of m.addedNodes || []) {
                if (!(node instanceof HTMLElement)) continue;
                if (node.matches?.('div[data-baseweb="menu"]') || node.querySelector?.('div[data-baseweb="menu"]')) {
                  sawSomething = true;
                }
              }
            }
            if (sawSomething) scheduleScroll();
          });
          addObs.observe(document.body, { childList: true, subtree: true });

          const attrObs = new MutationObserver((mutations) => {
            for (const m of mutations) {
              const t = m.target;
              if (!(t instanceof HTMLElement)) continue;

              const isMenu = t.matches?.('div[data-baseweb="menu"]');
              const hasMenuChild = t.querySelector?. && t.querySelector('div[data-baseweb="menu"]');

              if (isMenu || hasMenuChild) {
                scheduleScroll();
                return;
              }
            }
          });
          attrObs.observe(document.body, { attributes: true, subtree: true, attributeFilter: ["style", "class", "aria-hidden", "aria-expanded"] });

          document.addEventListener("pointerdown", (e) => {
            const sel = e.target?.closest?.('div[data-baseweb="select"]');
            if (sel) scheduleScroll();
          }, true);

          document.addEventListener("keydown", (e) => {
            const keys = ["Enter", " ", "ArrowDown", "ArrowUp"];
            if (!keys.includes(e.key)) return;
            const active = document.activeElement;
            if (active && active.closest && active.closest('div[data-baseweb="select"]')) scheduleScroll();
          }, true);

        })();
        </script>
        """,
        height=0,
        width=0,
    )


# ---------------------------
# CSS injection (FIXED)
# ---------------------------

def apply_css(bg_css: str, palette: dict, text: str, muted: str, sidebar_icon_uri: str | None, dark_mode: bool):
    # Use the computed page colors as the single source of truth
    select_value_color = text
    select_placeholder_color = muted
    menu_text_color = text

    # Sidebar surface
    sidebar_bg = "rgba(2, 6, 23, 0.78)" if dark_mode else "rgba(255, 255, 255, 0.92)"
    sidebar_border = palette["border"]

    # Optional icon on sidebar toggle
    icon_css = ""
    if sidebar_icon_uri:
        icon_css = f"""
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
/* Hide top widgets you don’t want */
header[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stDeployButton"], [data-testid="stStatusWidget"], [data-testid="stToolbarActions"] {{ display:none !important; }}

/* Page background */
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

/* Main content surface */
.block-container {{
    background: {palette["card_bg"]};
    border: 1px solid {palette["border"]};
    border-radius: 18px;
    padding: 1.1rem;
    backdrop-filter: blur(8px);
}}

/* Default text everywhere */
html, body, [data-testid="stAppViewContainer"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}
.stCaption, .stMarkdown p, .stMarkdown li {{
    color: {muted} !important;
    -webkit-text-fill-color: {muted} !important;
}}

/* Title spacing */
h1 {{
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.08 !important;
}}
.title-desc-tight p {{
    margin: 0.12rem 0 0 0 !important;
    padding: 0 !important;
}}

/* ===============================
   FORCE WIDGET TEXT READABILITY
   =============================== */

/* Widget labels */
label[data-testid="stWidgetLabel"] p,
label[data-testid="stWidgetLabel"] span,
label[data-testid="stWidgetLabel"] div {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
    opacity: 1 !important;
}}

/* Selectbox / Multiselect control surface */
div[data-baseweb="select"] > div {{
    background: {palette["widget_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    border-radius: 12px !important;
}}

/* Selected value inside control (this is the big one) */
div[data-baseweb="select"] > div * {{
    color: {select_value_color} !important;
    -webkit-text-fill-color: {select_value_color} !important;
    opacity: 1 !important;
}}

/* Placeholder text inside control */
div[data-baseweb="select"] [aria-placeholder="true"],
div[data-baseweb="select"] [data-baseweb="placeholder"] {{
    color: {select_placeholder_color} !important;
    -webkit-text-fill-color: {select_placeholder_color} !important;
    opacity: 1 !important;
}}

/* Dropdown arrow / chevrons (SVG) */
div[data-baseweb="select"] svg,
div[data-baseweb="select"] svg * {{
    fill: {select_value_color} !important;
    stroke: {select_value_color} !important;
    opacity: 0.95 !important;
}}

/* Dropdown menu container */
div[data-baseweb="popover"] div[data-baseweb="menu"] {{
    background: {palette["menu_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    border-radius: 12px !important;
}}

/* Dropdown menu text (options) */
div[data-baseweb="popover"] div[data-baseweb="menu"] * {{
    color: {menu_text_color} !important;
    -webkit-text-fill-color: {menu_text_color} !important;
    opacity: 1 !important;
}}

/* ===============================
   FIX SIDEBAR DROPDOWN LIST READABILITY (PORTAL MENUS)
   =============================== */

/* The dropdown list is rendered in a portal, not inside the sidebar.
   Force menu background + item text with higher specificity. */
div[data-baseweb="popover"] div[data-baseweb="menu"],
div[data-baseweb="popover"] div[role="listbox"] {{
    background: {palette["menu_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}

/* Force option text to be readable (Streamlit sometimes lowers opacity) */
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"],
div[data-baseweb="popover"] div[role="listbox"] div[role="option"] {{
    color: {menu_text_color} !important;
    -webkit-text-fill-color: {menu_text_color} !important;
    opacity: 1 !important;
}}

/* Most option labels are spans inside the option row */
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"] span,
div[data-baseweb="popover"] div[role="listbox"] div[role="option"] span {{
    color: {menu_text_color} !important;
    -webkit-text-fill-color: {menu_text_color} !important;
    opacity: 1 !important;
}}

/* Hover + selected states (keep readable on both light/dark menus) */
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"]:hover,
div[data-baseweb="popover"] div[role="listbox"] div[role="option"]:hover {{
    background: {palette["hover_bg"]} !important;
}}

div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][aria-selected="true"],
div[data-baseweb="popover"] div[role="listbox"] div[role="option"][aria-selected="true"] {{
    background: {palette["hover_bg"]} !important;
}}

/* Hover state */
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"]:hover {{
    background: {palette["hover_bg"]} !important;
}}

/* Selected option state (keeps it readable even if BaseWeb changes it) */
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][aria-selected="true"],
div[data-baseweb="popover"] div[data-baseweb="menu"] div[role="option"][data-selected="true"] {{
    background: {palette["hover_bg"]} !important;
}}

/* Inputs & textareas */
textarea,
input:not([type="file"]) {{
    background: {palette["widget_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    color: {select_value_color} !important;
    -webkit-text-fill-color: {select_value_color} !important;
}}

/* Focus ring */
div[data-baseweb="select"] > div:focus-within {{
    box-shadow: 0 0 0 3px {palette["focus_ring"]} !important;
}}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {{
    background: {palette["widget_bg"]} !important;
    border: 1px dashed {palette["border"]} !important;
    border-radius: 12px !important;
    padding: 0.65rem !important;
}}
[data-testid="stFileUploaderDropzone"] * {{
    color: {select_value_color} !important;
    -webkit-text-fill-color: {select_value_color} !important;
}}

/* Metrics */
[data-testid="stMetric"] {{
    background: {palette["widget_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    border-radius: 14px !important;
    padding: 0.6rem !important;
}}
[data-testid="stMetric"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

/* Tabs text */
button[data-baseweb="tab"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

/* Dataframe text */
[data-testid="stDataFrame"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

/* Buttons */
button[kind="primary"], button[kind="secondary"], .stButton>button {{
    background: {palette["button_bg"]} !important;
    border: 1px solid {palette["border"]} !important;
    color: {palette["button_text"]} !important;
    -webkit-text-fill-color: {palette["button_text"]} !important;
}}
.stButton>button:hover {{
    background: {palette["button_hover_bg"]} !important;
}}

/* Sidebar base */
section[data-testid="stSidebar"] {{
    background: {sidebar_bg} !important;
    border-right: 1px solid {sidebar_border} !important;
}}
section[data-testid="stSidebar"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

/* Sidebar select controls should match */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background: {palette["widget_bg"]} !important;
    border: 1px solid {sidebar_border} !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="popover"] div[data-baseweb="menu"] {{
    border: 1px solid {sidebar_border} !important;
}}

{icon_css}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------
# Defaults (UPDATED: default background is Solid Warm Cream)
# ---------------------------

if "bg_mode" not in st.session_state:
    st.session_state["bg_mode"] = "Solid"
if "solid_choice" not in st.session_state:
    st.session_state["solid_choice"] = "Warm Cream"
if "solid_picker" not in st.session_state:
    st.session_state["solid_picker"] = SOLID_PALETTES.get(st.session_state["solid_choice"], "#fbf7ef")
if "grad_a" not in st.session_state:
    st.session_state["grad_a"] = "#0b1020"
if "grad_b" not in st.session_state:
    st.session_state["grad_b"] = "#123055"
if "grad_angle" not in st.session_state:
    st.session_state["grad_angle"] = 135
if "max_categories_main" not in st.session_state:
    st.session_state["max_categories_main"] = 20
if "max_preview_rows_main" not in st.session_state:
    st.session_state["max_preview_rows_main"] = 25


# ---------------------------
# Sidebar: compact sections via expanders
# ---------------------------

with st.sidebar:
    with st.expander("Page Appearance", expanded=True):
        bg_type_options = ["Solid", "Gradient", "Image"]
        bg_index = bg_type_options.index(st.session_state.get("bg_mode", "Solid")) if st.session_state.get("bg_mode", "Solid") in bg_type_options else 0
        st.selectbox("Background Type", bg_type_options, index=bg_index, key="bg_mode")

        if st.session_state["bg_mode"] == "Solid":
            st.color_picker("Solid Color", value=st.session_state.get("solid_picker", "#fbf7ef"), key="solid_picker")

            keys = list(SOLID_PALETTES.keys())
            current = st.session_state.get("solid_choice", "Warm Cream")
            idx = keys.index(current) if current in keys else 0
            st.selectbox(
                "Solid Palette",
                keys,
                index=idx,
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

    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

    with st.expander("Filters", expanded=False):
        st.slider("Max Categories", 5, 50, int(st.session_state.get("max_categories_main", 20)), key="max_categories_main")
        st.slider("Preview Rows", 5, 100, int(st.session_state.get("max_preview_rows_main", 25)), key="max_preview_rows_main")

    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

    with st.expander("Jump To", expanded=False):
        st.markdown(
            """
            - [Upload](#upload)
            - [Key Statistics](#key-statistics)
            - [Radial Breakdown](#radial-breakdown)
            - [Export](#export)
            """,
            unsafe_allow_html=True,
        )


# ---------------------------
# Theme construction
# ---------------------------

bg_mode = st.session_state.get("bg_mode", "Solid")
img_upload = st.session_state.get("bg_image", None)
solid_picker = st.session_state.get("solid_picker", "#fbf7ef")
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

sidebar_icon_uri = load_png_data_uri("paint.png")
apply_css(bg_css, palette, page_text, page_muted, sidebar_icon_uri, dark)

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

st.markdown(
    """
    [Upload](#upload) ·
    [Key Statistics](#key-statistics) ·
    [Radial Breakdown](#radial-breakdown) ·
    [Export](#export)
    """,
    unsafe_allow_html=True,
)

SECTION_PAD = "<div style='height: 1.25rem;'></div>"


# ---------------------------
# Upload + preview
# ---------------------------

st.markdown(SECTION_PAD, unsafe_allow_html=True)
st.markdown("<div id='upload'></div>", unsafe_allow_html=True)

left_upload, _ = st.columns([2, 6], vertical_alignment="top")
with left_upload:
    file_top = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], key="data_upload_top")

preview_clicked = False
preview_dialog = None

if file_top is not None:
    try:
        @st.dialog("Dataset Preview")
        def preview_dialog(df_to_show: pd.DataFrame, rows: int):
            st.dataframe(df_to_show.head(rows), use_container_width=True)
            st.caption(f"Showing the first {rows} rows.")
    except Exception:
        preview_dialog = None

    with left_upload:
        preview_clicked = st.button("Preview Dataset", key="preview_dataset_btn_under_upload")

if file_top is None:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = read_df(file_top)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

if preview_dialog is not None and preview_clicked:
    preview_dialog(df, int(st.session_state.get("max_preview_rows_main", 25)))

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()


# ---------------------------
# Key Statistics
# ---------------------------

st.markdown(SECTION_PAD, unsafe_allow_html=True)
st.markdown("<div id='key-statistics'></div>", unsafe_allow_html=True)
st.subheader("Key Statistics")

kpi_left, kpi_right = st.columns([2, 6], vertical_alignment="top")

with kpi_left:
    if numeric_cols:
        primary_numeric = st.selectbox(
            "Primary Numeric Column (KPIs)",
            options=numeric_cols,
            index=0,
            key="kpi_primary_numeric",
        )
    else:
        primary_numeric = None
        st.info("No numeric columns found for KPI statistics.")

summary, visuals_kpi, numeric_df, categorical_df = build_visuals(
    df=df,
    report_type="Overview",
    user_choices={
        "primary_numeric": primary_numeric,
        "scatter_x": None,
        "scatter_y": None,
        "category_volume": None,
        "category_a": None,
        "category_b": None,
        "radial_category_col": None,
        "radial_categories": [],
        "radial_mode": "count",
        "radial_value_col": None,
    },
    max_categories=int(st.session_state.get("max_categories_main", 20)),
)

with kpi_right:
    kpi_cols = st.columns(5)
    if primary_numeric:
        stats = compute_numeric_stats(df, primary_numeric)
        kpi_cols[0].metric(f"Total {primary_numeric}", stats["sum"])
        kpi_cols[1].metric(f"Average {primary_numeric}", stats["mean"])
        kpi_cols[2].metric(f"Median {primary_numeric}", stats["median"])
        kpi_cols[3].metric(f"Minimum {primary_numeric}", stats["min"])
        kpi_cols[4].metric(f"Maximum {primary_numeric}", stats["max"])
    else:
        kpi_cols[0].metric("Total", "N/A")
        kpi_cols[1].metric("Average", "N/A")
        kpi_cols[2].metric("Median", "N/A")
        kpi_cols[3].metric("Minimum", "N/A")
        kpi_cols[4].metric("Maximum", "N/A")

meta_cols = st.columns(4)
meta_cols[0].metric("Total Rows", int(df.shape[0]))
meta_cols[1].metric("Numeric Columns", int(len(numeric_cols)))
meta_cols[2].metric("Categorical Columns", int(len(categorical_cols)))
meta_cols[3].metric("Missing Cells", int(df.isna().sum().sum()))


# ---------------------------
# Radial chart
# ---------------------------

st.markdown(SECTION_PAD, unsafe_allow_html=True)
st.markdown("<div id='radial-breakdown'></div>", unsafe_allow_html=True)
st.markdown("Radial Category Breakdown")
rad_controls, rad_chart = st.columns([1, 2])

with rad_controls:
    if categorical_cols:
        radial_col_kpi = st.selectbox("Category Column", options=categorical_cols, index=0, key="kpi_radial_col")
    else:
        radial_col_kpi = None
        st.info("No categorical columns found for a radial chart.")

    radial_mode_label = st.selectbox("Value Type", ["Count", "Sum of Numeric Column"], index=0, key="kpi_radial_mode")

    radial_value_col_kpi = None
    if radial_mode_label == "Sum of Numeric Column":
        if numeric_cols:
            radial_value_col_kpi = st.selectbox(
                "Numeric Column to Sum",
                options=numeric_cols,
                index=0,
                key="kpi_radial_value_col",
            )
        else:
            st.info("No numeric columns available to sum.")

with rad_chart:
    if radial_col_kpi:
        radial_mode = "sum" if radial_mode_label == "Sum of Numeric Column" else "count"
        _, visuals_radial_kpi, _, _ = build_visuals(
            df=df,
            report_type="Overview",
            user_choices={
                "primary_numeric": primary_numeric,
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
            max_categories=int(st.session_state.get("max_categories_main", 20)),
        )
        fig = get_fig(visuals_radial_kpi, "radial_donut")
        if fig is not None:
            fig = enforce_y_axis_horizontal(force_theme(fig, theme))
            st.plotly_chart(fig, use_container_width=True, key="chart_kpi_radial_donut")
            st.caption("Colors use different shades of the active theme accent.")
        else:
            st.info("Radial chart could not be generated for this column.")
    else:
        st.info("Add a categorical column to see the radial chart.")


# ---------------------------
# Tabs
# ---------------------------

st.markdown(SECTION_PAD, unsafe_allow_html=True)

tabs = st.tabs(["Tables", "Distribution", "Scatter Plot", "Bar Chart", "Heatmap", "Export"])

with tabs[0]:
    st.subheader("Statistics Tables")
    st.dataframe(numeric_df, use_container_width=True)
    st.dataframe(categorical_df, use_container_width=True)

with tabs[1]:
    st.subheader("Distribution")
    if primary_numeric:
        fig = get_fig(visuals_kpi, "numeric_distribution")
        if fig is not None:
            fig = enforce_y_axis_horizontal(force_theme(fig, theme))
            st.plotly_chart(fig, use_container_width=True, key="chart_kpi_distribution")
        else:
            st.info("No distribution chart available for the current selection.")
    else:
        st.info("No numeric columns available for a distribution chart.")

with tabs[2]:
    st.subheader("Numeric Comparison Scatter Plot")
    controls, chart = st.columns([1, 2])

    with controls:
        if numeric_cols:
            scatter_x = st.selectbox("X Axis (Numeric)", options=numeric_cols, index=0, key="scatter_x")
            y_index = 1 if len(numeric_cols) > 1 else 0
            scatter_y = st.selectbox("Y Axis (Numeric)", options=numeric_cols, index=y_index, key="scatter_y")
        else:
            scatter_x = None
            scatter_y = None
            st.info("No numeric columns found for a scatter plot.")

    _, visuals, _, _ = build_visuals(
        df,
        "Overview",
        {
            "primary_numeric": None,
            "scatter_x": scatter_x,
            "scatter_y": scatter_y,
            "category_volume": None,
            "category_a": None,
            "category_b": None,
            "radial_category_col": None,
            "radial_categories": [],
            "radial_mode": "count",
            "radial_value_col": None,
        },
        int(st.session_state.get("max_categories_main", 20)),
    )

    with chart:
        if scatter_x and scatter_y:
            fig = get_fig(visuals, "numeric_scatter")
            if fig is not None:
                fig = enforce_y_axis_horizontal(force_theme(fig, theme))
                st.plotly_chart(fig, use_container_width=True, key="chart_scatter")
            else:
                st.info("Scatter plot could not be generated for these columns.")
        else:
            st.info("Add numeric columns to generate the scatter plot.")

with tabs[3]:
    st.subheader("Category Distribution Bar Chart")
    controls, chart = st.columns([1, 2])

    with controls:
        if categorical_cols:
            cat_volume_col = st.selectbox("Category Column", options=categorical_cols, index=0, key="cat_volume_col")
        else:
            cat_volume_col = None
            st.info("No categorical columns found for a bar chart.")

    _, visuals, _, _ = build_visuals(
        df,
        "Overview",
        {
            "primary_numeric": None,
            "scatter_x": None,
            "scatter_y": None,
            "category_volume": cat_volume_col,
            "category_a": None,
            "category_b": None,
            "radial_category_col": None,
            "radial_categories": [],
            "radial_mode": "count",
            "radial_value_col": None,
        },
        int(st.session_state.get("max_categories_main", 20)),
    )

    with chart:
        if cat_volume_col:
            fig = get_fig(visuals, "category_volume")
            if fig is not None:
                fig = enforce_y_axis_horizontal(force_theme(fig, theme))
                st.plotly_chart(fig, use_container_width=True, key="chart_category_volume")
            else:
                st.info("Bar chart could not be generated for this column.")
        else:
            st.info("Add categorical columns to generate the bar chart.")

with tabs[4]:
    st.subheader("Category Relationship Heatmap")
    controls, chart = st.columns([1, 2])

    with controls:
        if categorical_cols:
            cat_a = st.selectbox("Category A", options=categorical_cols, index=0, key="cat_a")
            b_index = 1 if len(categorical_cols) > 1 else 0
            cat_b = st.selectbox("Category B", options=categorical_cols, index=b_index, key="cat_b")
        else:
            cat_a = None
            cat_b = None
            st.info("No categorical columns found for a heatmap.")

    _, visuals, _, _ = build_visuals(
        df,
        "Overview",
        {
            "primary_numeric": None,
            "scatter_x": None,
            "scatter_y": None,
            "category_volume": None,
            "category_a": cat_a,
            "category_b": cat_b,
            "radial_category_col": None,
            "radial_categories": [],
            "radial_mode": "count",
            "radial_value_col": None,
        },
        int(st.session_state.get("max_categories_main", 20)),
    )

    with chart:
        if cat_a and cat_b:
            fig = get_fig(visuals, "category_heatmap")
            if fig is not None:
                fig = enforce_y_axis_horizontal(force_theme(fig, theme))
                st.plotly_chart(fig, use_container_width=True, key="chart_heatmap")
            else:
                st.info("Heatmap could not be generated for these columns.")
        else:
            st.info("Add categorical columns to generate the heatmap.")

with tabs[5]:
    st.markdown("<div id='export'></div>", unsafe_allow_html=True)
    st.subheader("Export")
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False),
        file_name="report_data.csv",
        mime="text/csv",
    )

st.markdown("<div style='height: 6rem;'></div>", unsafe_allow_html=True)
