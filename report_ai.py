# report_ai.py
import pandas as pd
import plotly.express as px

def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def _blend(rgb_a, rgb_b, t: float):
    return (
        int(rgb_a[0] + (rgb_b[0] - rgb_a[0]) * t),
        int(rgb_a[1] + (rgb_b[1] - rgb_a[1]) * t),
        int(rgb_a[2] + (rgb_b[2] - rgb_a[2]) * t),
    )

def generate_shades(base_hex: str, n: int):
    """
    Produce n shades of one base color by blending a light tint to a darker tone.
    """
    base = _hex_to_rgb(base_hex)
    white = (255, 255, 255)
    black = (0, 0, 0)

    light_anchor = _blend(base, white, 0.65)
    dark_anchor = _blend(base, black, 0.35)

    if n <= 1:
        return [_rgb_to_hex(base)]

    shades = []
    for i in range(n):
        t = i / (n - 1)
        rgb = _blend(light_anchor, dark_anchor, t)
        shades.append(_rgb_to_hex(rgb))
    return shades

def _polish_layout(fig, title_text: str):
    """
    Standardize title casing, alignment, sizing, and margins across charts.
    """
    fig.update_layout(
        title={
            "text": title_text,
            "x": 0.02,
            "xanchor": "left",
            "yanchor": "top",
        },
        margin=dict(t=72, l=40, r=40, b=40),
        title_font=dict(size=18),
        legend_title_text="Legend"
    )
    return fig

def build_visuals(
    df: pd.DataFrame,
    report_type: str,
    user_choices: dict,
    max_categories: int = 20
):
    visuals = []

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    # ---------- SUMMARY ----------
    summary = {
        "rows": int(df.shape[0]),
        "numeric_count": len(numeric_cols),
        "categorical_count": len(categorical_cols),
        "missing_cells": int(df.isna().sum().sum()),
        "primary_numeric_column": None,
        "mean": None,
        "median": None,
        "min": None,
        "max": None,
    }

    # ---------- PRIMARY NUMERIC (KPIs + distribution) ----------
    primary_numeric = user_choices.get("primary_numeric")
    if primary_numeric and primary_numeric in numeric_cols:
        s = df[primary_numeric]
        summary.update(
            {
                "primary_numeric_column": primary_numeric,
                "mean": round(float(s.mean()), 2) if pd.notna(s.mean()) else None,
                "median": round(float(s.median()), 2) if pd.notna(s.median()) else None,
                "min": round(float(s.min()), 2) if pd.notna(s.min()) else None,
                "max": round(float(s.max()), 2) if pd.notna(s.max()) else None,
            }
        )

        fig = px.histogram(
            df,
            x=primary_numeric,
            labels={primary_numeric: primary_numeric, "count": "Frequency"},
        )
        fig = _polish_layout(
            fig,
            f"Distribution of {primary_numeric}<br><sup>Frequency of values across the dataset</sup>"
        )
        visuals.append(("numeric_distribution", fig))

    # ---------- NUMERIC COMPARISON (SCATTER) ----------
    x = user_choices.get("scatter_x")
    y = user_choices.get("scatter_y")

    if x and y and x in numeric_cols and y in numeric_cols and x != y:
        fig = px.scatter(
            df,
            x=x,
            y=y,
            labels={x: x, y: y},
        )
        fig = _polish_layout(fig, f"{y} vs. {x}")
        visuals.append(("numeric_scatter", fig))

    # ---------- CATEGORY VOLUME (BAR) ----------
    cat_vol = user_choices.get("category_volume")
    if cat_vol and cat_vol in categorical_cols:
        vc = (
            df[cat_vol]
            .astype("string")
            .fillna("Missing")
            .value_counts()
            .head(max_categories)
            .reset_index()
        )
        vc.columns = [cat_vol, "Count"]

        fig = px.bar(
            vc,
            x=cat_vol,
            y="Count",
            labels={cat_vol: cat_vol, "Count": "Records"},
        )
        fig = _polish_layout(fig, f"Category Distribution: {cat_vol}")
        visuals.append(("category_volume", fig))

    # ---------- CATEGORY COMPARISON (HEATMAP) ----------
    a = user_choices.get("category_a")
    b = user_choices.get("category_b")

    if a and b and a in categorical_cols and b in categorical_cols and a != b:
        ct = pd.crosstab(
            df[a].astype("string").fillna("Missing"),
            df[b].astype("string").fillna("Missing"),
        )

        ct = ct.iloc[:max_categories, :max_categories]

        fig = px.imshow(
            ct,
            labels=dict(x=b, y=a, color="Count"),
        )
        fig = _polish_layout(fig, f"Category Relationship: {a} vs. {b}")
        visuals.append(("category_heatmap", fig))

    # ---------- RADIAL CATEGORY (DONUT) ----------
    radial_col = user_choices.get("radial_category_col")
    radial_categories = user_choices.get("radial_categories") or []
    radial_mode = user_choices.get("radial_mode")  # "count" or "sum"
    radial_value_col = user_choices.get("radial_value_col")  # numeric col if sum

    if radial_col and radial_col in categorical_cols:
        temp = df.copy()
        temp[radial_col] = temp[radial_col].astype("string").fillna("Missing")

        if radial_categories:
            temp = temp[temp[radial_col].isin(radial_categories)]

        if radial_mode == "sum" and radial_value_col and radial_value_col in numeric_cols:
            grouped = temp.groupby(radial_col, dropna=False)[radial_value_col].sum().reset_index()
            grouped = grouped.rename(columns={radial_value_col: "Value"})
            value_label = f"Total {radial_value_col}"
            title = f"Category Breakdown by Total {radial_value_col}"
        else:
            grouped = temp[radial_col].value_counts().reset_index()
            grouped.columns = [radial_col, "Value"]
            value_label = "Count"
            title = f"Category Breakdown: {radial_col}"

        grouped = grouped.sort_values("Value", ascending=False).head(max_categories)

        n = int(grouped.shape[0])
        shades = generate_shades("#2b6cb0", n)

        fig = px.pie(
            grouped,
            names=radial_col,
            values="Value",
            hole=0.55,
            labels={radial_col: radial_col, "Value": value_label},
            color_discrete_sequence=shades,
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent",
            hovertemplate=f"{radial_col}: %{{label}}<br>{value_label}: %{{value}}<extra></extra>",
        )

        fig = _polish_layout(fig, title)
        visuals.append(("radial_donut", fig))

    # ---------- TABLES ----------
    numeric_df = df[numeric_cols].describe().round(2).T if numeric_cols else pd.DataFrame()

    categorical_rows = []
    for col in categorical_cols:
        vc = df[col].astype("string").fillna("Missing").value_counts()
        categorical_rows.append(
            {
                "column": col,
                "unique_values": int(vc.shape[0]),
                "top_value": vc.index[0] if not vc.empty else None,
                "top_count": int(vc.iloc[0]) if not vc.empty else 0,
            }
        )

    categorical_df = pd.DataFrame(categorical_rows)

    return summary, visuals, numeric_df, categorical_df
