# report_ai.py
import pandas as pd
import plotly.express as px

def pick_numeric_columns(df: pd.DataFrame):
    return df.select_dtypes(include="number").columns.tolist()

def pick_non_numeric_columns(df: pd.DataFrame):
    return df.select_dtypes(exclude="number").columns.tolist()

def is_text_like(series: pd.Series) -> bool:
    s = series.dropna().astype("string")
    if s.empty:
        return False
    avg_len = s.str.len().mean()
    return avg_len is not None and avg_len >= 30

def safe_number(x):
    try:
        if pd.isna(x):
            return None
        x = float(x)
        # format a bit for Streamlit metric display
        if abs(x) >= 1000:
            return f"{x:,.2f}"
        return f"{x:.2f}"
    except Exception:
        return None

def numeric_stats(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    if not numeric_cols:
        return pd.DataFrame()

    desc = df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc = desc.rename(columns={"50%": "median"})
    keep = ["count", "mean", "std", "min", "25%", "median", "75%", "max"]
    keep = [c for c in keep if c in desc.columns]
    desc = desc[keep].reset_index().rename(columns={"index": "column"})
    return desc

def categorical_stats(df: pd.DataFrame, cat_cols: list[str], top_n: int = 5) -> pd.DataFrame:
    rows = []
    for col in cat_cols:
        s = df[col].astype("string").fillna("Missing")
        vc = s.value_counts()

        unique = int(vc.shape[0])
        top_value = str(vc.index[0]) if not vc.empty else None
        top_count = int(vc.iloc[0]) if not vc.empty else 0

        top_items = vc.head(top_n)
        top_pairs = [{"value": str(idx), "count": int(cnt)} for idx, cnt in top_items.items()]

        rows.append(
            {
                "column": str(col),
                "unique_values": unique,
                "top_value": top_value,
                "top_count": top_count,
                "top_values": top_pairs,
            }
        )

    return pd.DataFrame(rows)

def column_quality_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_rows = len(df)
    details = []

    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))

        vc = series.value_counts(dropna=True)
        top_value = None
        top_count = 0
        if not vc.empty:
            top_value = str(vc.index[0])
            top_count = int(vc.iloc[0])

        details.append(
            {
                "column": str(col),
                "missing": missing,
                "missing_percent": round((missing / total_rows) * 100, 2) if total_rows else 0.0,
                "unique": unique,
                "top_value": top_value,
                "top_count": top_count,
            }
        )

    quality_df = pd.DataFrame(details)
    return quality_df.sort_values(["missing", "unique"], ascending=[False, False])

def categorical_volume_chart(df: pd.DataFrame, col: str, max_categories: int):
    s = df[col].astype("string").fillna("Missing")
    vc = s.value_counts().head(max_categories)

    vc_df = vc.reset_index()
    vc_df.columns = [col, "count"]

    fig = px.bar(vc_df, x=col, y="count", title=f"Category volume: {col}")
    return fig

def categorical_relationship_heatmap(df: pd.DataFrame, col_a: str, col_b: str, max_categories: int):
    a = df[col_a].astype("string").fillna("Missing")
    b = df[col_b].astype("string").fillna("Missing")

    top_a = a.value_counts().head(max_categories).index
    top_b = b.value_counts().head(max_categories).index

    a_filtered = a.where(a.isin(top_a), other="Other")
    b_filtered = b.where(b.isin(top_b), other="Other")

    ct = pd.crosstab(a_filtered, b_filtered)
    fig = px.imshow(ct, title=f"Category relationship: {col_a} vs {col_b}")
    return fig

def text_length_chart(df: pd.DataFrame, col: str):
    s = df[col].astype("string").fillna("")
    lengths = s.str.len()
    temp = pd.DataFrame({"length": lengths})
    fig = px.histogram(temp, x="length", title=f"Text length distribution: {col}")
    return fig

def pick_primary_numeric(numeric_cols: list[str], user_choice: str | None, instructions: str):
    if user_choice and user_choice in numeric_cols:
        return user_choice

    lowered = (instructions or "").lower()
    for c in numeric_cols:
        if c.lower() in lowered:
            return c

    return numeric_cols[0] if numeric_cols else None

def pick_primary_category(cat_cols: list[str], user_choice: str | None, instructions: str):
    if user_choice and user_choice in cat_cols:
        return user_choice

    lowered = (instructions or "").lower()
    for c in cat_cols:
        if c.lower() in lowered:
            return c

    return cat_cols[0] if cat_cols else None

def build_report_summary(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str], primary_numeric: str | None, primary_cat: str | None):
    summary = {}

    if primary_numeric:
        series = df[primary_numeric]
        summary["primary_numeric_column"] = primary_numeric
        summary["primary_mean"] = safe_number(series.mean())
        summary["primary_median"] = safe_number(series.median())
        summary["primary_min"] = safe_number(series.min())
        summary["primary_max"] = safe_number(series.max())
    else:
        summary["primary_numeric_column"] = None
        summary["primary_mean"] = None
        summary["primary_median"] = None
        summary["primary_min"] = None
        summary["primary_max"] = None

    if primary_cat:
        s = df[primary_cat].astype("string").fillna("Missing")
        vc = s.value_counts()
        top_label = str(vc.index[0]) if not vc.empty else None
        top_count = int(vc.iloc[0]) if not vc.empty else 0

        summary["primary_categorical_column"] = primary_cat
        summary["top_category_label"] = top_label
        summary["top_category_count"] = top_count
    else:
        summary["primary_categorical_column"] = None
        summary["top_category_label"] = None
        summary["top_category_count"] = None

    summary["total_missing_cells"] = int(df.isna().sum().sum())
    return summary

def build_visuals(
    df: pd.DataFrame,
    report_type: str,
    instructions: str,
    user_choices: dict,
    max_categories: int = 20
):
    numeric_cols = pick_numeric_columns(df)
    non_numeric_cols_all = pick_non_numeric_columns(df)

    # Split categorical vs text like
    cat_cols = []
    text_like_cols = []
    for col in non_numeric_cols_all:
        if is_text_like(df[col]):
            text_like_cols.append(col)
        else:
            cat_cols.append(col)

    quality_df = column_quality_summary(df)
    numeric_df = numeric_stats(df, numeric_cols)
    categorical_df = categorical_stats(df, cat_cols, top_n=5)

    primary_numeric = pick_primary_numeric(numeric_cols, user_choices.get("primary_numeric"), instructions)
    primary_cat = pick_primary_category(cat_cols, user_choices.get("category_volume_col"), instructions)

    report_summary = build_report_summary(df, numeric_cols, cat_cols, primary_numeric, primary_cat)

    visuals = []

    # Missing values chart
    if quality_df["missing"].sum() > 0:
        miss = quality_df.sort_values("missing", ascending=False).head(25)
        fig = px.bar(miss, x="column", y="missing", title="Missing values by column")
        visuals.append(("missing_values", fig))

    # Numeric compare charts based on user choices
    x_num = user_choices.get("compare_numeric_x")
    y_num = user_choices.get("compare_numeric_y")

    if primary_numeric:
        fig = px.histogram(df, x=primary_numeric, title=f"Distribution of {primary_numeric}")
        visuals.append(("numeric_distribution", fig))

    if x_num and y_num and x_num in numeric_cols and y_num in numeric_cols and x_num != y_num:
        fig = px.scatter(df, x=x_num, y=y_num, title=f"{y_num} vs {x_num}")
        visuals.append(("numeric_comparison_scatter", fig))

    # Category volume chart based on your chosen or inferred column
    if primary_cat:
        fig = categorical_volume_chart(df, primary_cat, max_categories=max_categories)
        visuals.append((f"category_volume_{primary_cat}", fig))
    else:
        # Fallback: show up to 2 category volume charts automatically
        for col in cat_cols[:2]:
            fig = categorical_volume_chart(df, col, max_categories=max_categories)
            visuals.append((f"category_volume_{col}", fig))

    # Category vs category comparison if you selected two
    a = user_choices.get("compare_category_a")
    b = user_choices.get("compare_category_b")

    if a and b and a in cat_cols and b in cat_cols and a != b:
        fig = categorical_relationship_heatmap(df, a, b, max_categories=min(max_categories, 15))
        visuals.append(("category_relationship_heatmap", fig))
    elif len(cat_cols) >= 2:
        # Fallback heatmap
        fig = categorical_relationship_heatmap(df, cat_cols[0], cat_cols[1], max_categories=min(max_categories, 15))
        visuals.append(("category_relationship_heatmap", fig))

    # Text length chart if text columns exist
    if text_like_cols:
        fig = text_length_chart(df, text_like_cols[0])
        visuals.append((f"text_length_{text_like_cols[0]}", fig))

    return report_summary, visuals, quality_df, numeric_df, categorical_df
