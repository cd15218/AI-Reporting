# app.py
import base64
import pandas as pd
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

from report_ai import build_visuals

st.set_page_config(
    page_title="Dataset Reporting",
    layout="wide",
    initial_sidebar_state="collapsed",
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

def default_two_distinct(items: list[str]) -> tuple[str | None, str | None]:
    if not items:
        return None, None
    if len(items) == 1:
        return items[0], items[0]
    return items[0], items[1]

# ---------------------------
# Palettes
# ---------------------------

SOLID_PALETTES = {
    "Slate": "#0f172a",
    "Midnight": "#050814",
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

_unique_hex_to_name = {}
for nm, hx in SOLID_PALETTES.items():
    hx_norm = str(hx).strip().lower()
    if hx_norm not in _unique_hex_to_name:
        _unique_hex_to_name[hx_norm] = nm
SOLID_PALETTE_OPTIONS = [_unique_hex_to_name[hx] for hx in _unique_hex_to_name]

def _sync_solid_picker():
    choice = st.session_state.get("solid_choice_top", None)
    if choice and choice in SOLID_PALETTES:
        st.session_state["solid_picker_top"] = SOLID_PALETTES[choice]

# ---------------------------
# Icon (SVG -> base64)
# ---------------------------

def build_paint_icon_uri(stroke_hex: str) -> str:
    paint_svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <path d="M12 3c-4.97 0-9 3.58-9 8 0 2.95 1.89 5.52 4.66 6.97.63.33 1.34.03 1.63-.63l.54-1.25c.2-.47.66-.78 1.17-.78h1.77c1.1 0 1.99.89 1.99 1.99v1.55c0 .62.5 1.13 1.12 1.13C20.64 19.99 21 15.4 21 11c0-4.42-4.03-8-9-8Z"
            stroke="{stroke_hex}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M8.4 10.2h.01M11.2 8.6h.01M14.2 10.2h.01M12.8 12.9h.01"
            stroke="{stroke_hex}" stroke-width="3.0" stroke-linecap="round"/>
      <path d="M16.2 14.7l3.1 3.1c.46.46.46 1.2 0 1.66l-.72.72c-.46.46-1.2.46-1.66 0l-3.1-3.1"
            stroke="{stroke_hex}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """.strip()
    return "data:image/svg+xml;base64," + base64.b64encode(paint_svg.encode("utf-8")).decode("utf-8")

# ---------------------------
# CSS + dropdown "sticky selection" JS helper
# ---------------------------

def apply_css(bg_css: str, palette: dict, text: str, muted: str, icon_uri: str):
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

        /* Tight title + description */
        h1 {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.08 !important;
        }}
        .title-desc-tight p {{
            margin: 0.12rem 0 0 0 !important;
            padding: 0 !important;
        }}

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
            border: 1px solid {palette["border"]};
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

        /* --- Appearance control: keep it compact and on same line --- */
        .appearance-row {{
            display: flex;
            justify-content: flex-end;
            align-items: flex-start;
        }}
        [data-testid="stExpander"] {{
            width: auto !important;
        }}

        /* Make expander summary a LARGE borderless icon button */
        [data-testid="stExpander"] details > summary {{
            width: 96px !important;
            height: 96px !important;
            min-height: 96px !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 999px !important;
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        /* Remove caret arrow INSIDE the circle */
        [data-testid="stExpander"] details > summary svg {{
            display: none !important;
        }}
        [data-testid="stExpander"] details > summary p {{
            display: none !important;
        }}

        /* Center the icon perfectly */
        [data-testid="stExpander"] details > summary::before {{
            content: "" !important;
            display: block !important;
            width: 64px !important;
            height: 64px !important;
            background-image: url("{icon_uri}") !important;
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
        }}

        /* Optional subtle hover */
        [data-testid="stExpander"] details > summary:hover {{
            background: rgba(255,255,255,0.06) !important;
        }}

        /* Compact spacing for the filters row */
        .filters-tight [data-testid="stVerticalBlock"] {{
            gap: 0.35rem !important;
        }}

        /* Preview button auto-fit */
        .preview-autofit .stButton>button {{
            width: auto !important;
            padding: 0.35rem 0.7rem !important;
            border-radius: 999px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def inject_dropdown_scroll_to_selected():
    # This makes every selectbox menu jump to the currently selected option when opened.
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

                // Baseweb popover menu container
                const menu =
                  node.querySelector?.('div[data-baseweb="menu"]') ||
                  (node.matches?.('div[data-baseweb="menu"]') ? node : null);

                if (menu) {
                  // allow DOM paint then scroll
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

# ---------------------------
# Defaults
# ---------------------------

if "bg_mode_top" not in st.session_state:
    st.session_state["bg_mode_top"] = "Gradient"
if "solid_choice_top" not in st.session_state:
    st.session_state["solid_choice_top"] = list(SOLID_PALETTES.keys())[0]
if "solid_picker_top" not in st.session_state:
    st.session_state["solid_picker_top"] = SOLID_PALETTES[st.session_state["solid_choice_top"]]
if "grad_a_top" not in st.session_state:
    st.session_state["grad_a_top"] = "#0b1020"
if "grad_b_top" not in st.session_state:
    st.session_state["grad_b_top"] = "#123055"
if "grad_angle_top" not in st.session_state:
    st.session_state["grad_angle_top"] = 135

# ---------------------------
# Title row with appearance on SAME LINE
# ---------------------------

title_col, appearance_col = st.columns([7, 1], vertical_alignment="top")

with title_col:
    st.markdown("# Dataset Reporting")
    st.markdown("<div class='title-desc-tight'>", unsafe_allow_html=True)
    st.markdown("Upload a CSV or Excel file to generate key statistics and charts.")
    st.markdown("</div>", unsafe_allow_html=True)

with appearance_col:
    st.markdown("<div class='appearance-row'>", unsafe_allow_html=True)
    with st.expander(" ", expanded=False):
        bg_mode = st.selectbox("Background Type", ["Solid", "Gradient", "Image"], index=1, key="bg_mode_top")

        if bg_mode == "Solid":
            st.selectbox(
                "Solid Palette",
                list(SOLID_PALETTES.keys()),
                index=0,
                key="solid_choice_top",
                on_change=_sync_solid_picker,
            )
            st.color_picker(
                "Solid Color",
                value=st.session_state.get("solid_picker_top", "#0f172a"),
                key="solid_picker_top",
                label_visibility="collapsed",
            )

        if bg_mode == "Gradient":
            st.caption("Real gradient background.")
            st.color_picker("Color A", value=st.session_state.get("grad_a_top", "#0b1020"), key="grad_a_top")
            st.color_picker("Color B", value=st.session_state.get("grad_b_top", "#123055"), key="grad_b_top")
            st.slider("Angle", 0, 360, st.session_state.get("grad_angle_top", 135), key="grad_angle_top")

        if bg_mode == "Image":
            st.file_uploader(
                "Upload Background Image",
                type=["png", "jpg", "jpeg", "webp"],
                key="bg_image_top",
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Theme construction
# ---------------------------

bg_mode = st.session_state.get("bg_mode_top", "Gradient")
img_upload = st.session_state.get("bg_image_top", None)
solid_choice = st.session_state.get("solid_choice_top", list(SOLID_PALETTES.keys())[0])
solid_picker = st.session_state.get("solid_picker_top", SOLID_PALETTES.get(solid_choice, "#0f172a"))
grad_a = st.session_state.get("grad_a_top", "#0b1020")
grad_b = st.session_state.get("grad_b_top", "#123055")
grad_angle = st.session_state.get("grad_angle_top", 135)

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

icon_uri = build_paint_icon_uri(page_text)
apply_css(bg_css, palette, page_text, page_muted, icon_uri)

# Make dropdowns jump to selected option on open
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
# Filters above upload (compact)
# ---------------------------

st.markdown("<div class='filters-tight'>", unsafe_allow_html=True)
st.markdown("### Filters")

f1, f2, f3, _ = st.columns([2.0, 1.4, 1.4, 5.2], vertical_alignment="center")

with f1:
    report_type = st.selectbox(
        "Report Type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0,
        key="report_type_main",
        label_visibility="collapsed",
        placeholder="Report Type",
    )
    st.caption("Report Type")

with f2:
    max_categories = st.slider(
        "Max Categories",
        5,
        50,
        20,
        key="max_categories_main",
        label_visibility="collapsed",
    )
    st.caption("Max Categories")

with f3:
    max_preview_rows = st.slider(
        "Preview Rows",
        5,
        100,
        25,
        key="max_preview_rows_main",
        label_visibility="collapsed",
    )
    st.caption("Preview Rows")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Upload section (preview underneath)
# ---------------------------

left_upload, _ = st.columns([2, 6], vertical_alignment="top")
with left_upload:
    file_top = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls"], key="data_upload_top")

    try:
        @st.dialog("Dataset Preview")
        def preview_dialog(df_to_show: pd.DataFrame, rows: int):
            st.dataframe(df_to_show.head(rows), use_container_width=True)
            st.caption(f"Showing the first {rows} rows.")
    except Exception:
        preview_dialog = None

if file_top is None:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = read_df(file_top)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

with left_upload:
    st.markdown("<div class='preview-autofit'>", unsafe_allow_html=True)
    preview_clicked = st.button("Preview Dataset", key="preview_dataset_btn_under_upload")
    st.markdown("</div>", unsafe_allow_html=True)
    if preview_dialog is not None and preview_clicked:
        preview_dialog(df, int(st.session_state.get("max_preview_rows_main", 25)))

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

# ---------------------------
# Key Statistics (compact KPI selector on left, defaults not None)
# ---------------------------

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
    report_type=st.session_state.get("report_type_main", "Overview"),
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
# Radial chart (defaults not None)
# ---------------------------

st.markdown("Radial Category Breakdown")
rad_controls, rad_chart = st.columns([1, 2])

with rad_controls:
    if categorical_cols:
        radial_col_kpi = st.selectbox(
            "Category Column",
            options=categorical_cols,
            index=0,
            key="kpi_radial_col",
        )
    else:
        radial_col_kpi = None
        st.info("No categorical columns found for a radial chart.")

    radial_mode_label = st.selectbox(
        "Value Type",
        options=["Count", "Sum of Numeric Column"],
        index=0,
        key="kpi_radial_mode",
    )

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
            report_type=st.session_state.get("report_type_main", "Overview"),
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
        st.session_state.get("report_type_main", "Overview"),
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
        st.session_state.get("report_type_main", "Overview"),
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
        st.session_state.get("report_type_main", "Overview"),
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
    st.subheader("Export")
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False),
        file_name="report_data.csv",
        mime="text/csv",
    )

st.markdown("<div style='height: 6rem;'></div>", unsafe_allow_html=True)
