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
# CSS
# ---------------------------

def apply_css(bg_css: str, palette: dict, text: str, muted: str, sidebar_icon_uri: str | None, dark_mode: bool):
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

    sidebar_bg = "rgba(2, 6, 23, 0.78)" if dark_mode else "rgba(255, 255, 255, 0.92)"
    sidebar_border = palette["border"]
    sidebar_widget_bg = "rgba(255,255,255,0.10)" if dark_mode else "rgba(15,23,42,0.06)"
    sidebar_hover = "rgba(148, 163, 184, 0.22)" if dark_mode else "rgba(15, 23, 42, 0.10)"

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

        h1 {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.08 !important;
        }}
        .title-desc-tight p {{
            margin: 0.12rem 0 0 0 !important;
            padding: 0 !important;
        }}

        /* Main widgets */
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
            background: {palette["hover
