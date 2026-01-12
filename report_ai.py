import pandas as pd
import plotly.express as px

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

    primary_numeric = user_choices.get("primary_numeric")
    if primary_numeric and primary_numeric in numeric_cols:
        s = df[primary_numeric]
        summary.update(
            {
                "primary_numeric_column": primary_numeric,
                "mean": round(s.mean(), 2),
                "median": round(s.median(), 2),
                "min": round(s.min(), 2),
                "max": round(s.max(), 2),
            }
        )

        fig = px.histogram(
            df,
            x=primary_numeric,
            title=f"Distribution of {primary_numeric}",
            labels={primary_numeric: primary_numeric, "count": "Frequency"},
        )
        visuals.append(("numeric_distribution", fig))

    # ---------- NUMERIC COMPARISON ----------
    x = user_choices.get("scatter_x")
    y = user_choices.get("scatter_y")

    if x and y and x in numeric_cols and y in numeric_cols and x != y:
        fig = px.scatter(
            df,
            x=x,
            y=y,
            title=f"{y} vs {x}",
            labels={x: x, y: y},
        )
        visuals.append(("numeric_scatter", fig))

    # ---------- CATEGORY VOLUME ----------
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
            title=f"Category volume: {cat_vol}",
            labels={cat_vol: cat_vol, "Count": "Records"},
        )
        visuals.append(("category_volume", fig))

    # ---------- CATEGORY COMPARISON ----------
    a = user_choices.get("category_a")
    b = user_choices.get("category_b")

    if a and b and a in categorical_cols and b in categorical_cols and a != b:
        ct = pd.crosstab(
            df[a].astype("string").fillna("Missing"),
            df[b].astype("string").fillna("Missing"),
        ).iloc[:max_categories, :max_categories]

        fig = px.imshow(
            ct,
            title=f"Category relationship: {a} vs {b}",
            labels=dict(x=b, y=a, color="Count"),
        )
        visuals.append(("category_heatmap", fig))

    # ---------- TABLES ----------
    numeric_df = df[numeric_cols].describe().round(2).T if numeric_cols else pd.DataFrame()

    categorical_rows = []
    for col in categorical_cols:
        vc = df[col].astype("string").fillna("Missing").value_counts()
        categorical_rows.append(
            {
                "column": col,
                "unique_values": vc.shape[0],
                "top_value": vc.index[0] if not vc.empty else None,
                "top_count": int(vc.iloc[0]) if not vc.empty else 0,
            }
        )

    categorical_df = pd.DataFrame(categorical_rows)

    return summary, visuals, numeric_df, categorical_df
