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

def safe_float(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

def numeric_stats(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    if not numeric_cols:
        return pd.DataFrame(columns=["metric"] + numeric_cols)

    desc = df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc = desc.rename(columns={"50%": "median"})

    # Keep only the most useful columns for a report
    keep = ["count", "mean", "std", "min", "25%", "median", "75%", "max"]
    keep = [c for c in keep if c in desc.columns]
    desc = desc[keep]

    desc = desc.reset_index().rename(columns={"index": "column"})
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

def build_report_summary(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str]):
    summary = {}

    if numeric_cols:
        # Use the first numeric column for headline KPIs
        primary = numeric_cols[0]
        series = df[primary]

        summary["primary_numeric_column"] = primary
        summary["primary_mean"] = safe_float(series.mean())
        summary["primary_median"] = safe_float(series.median())
        summary["primary_min"] = safe_float(series.min())
        summary["primary_max"] = safe_float(series.max())

        # Optional second numeric column KPI if available
        if len(numeric_cols) >= 2:
            secondary = numeric_cols[1]
            s2 = df[secondary]
            summary["secondary_numeric_column"] = secondary
            summary["secondary_mean"] = safe_float(s2.mean())
        else:
            summary["secondary_numeric_column"] = None
            summary["secondary_mean"] = None
    else:
        summary["primary_numeric_column"] = None
        summary["primary_mean"] = None
        summary["primary_median"] = None
        summary["primary_min"] = None
        summary["primary_max"] = None
        summary["secondary_numeric_column"] = None
        summary["secondary_mean"] = None

    if cat_cols:
        primary_cat = cat_cols[0]
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

    total_missing = int(df.isna().sum().sum())
    summary["total_missing_cells"] = total_missing

    return summary

def build_visuals(df: pd.DataFrame, report_type: str, max_categories: int = 20):
    numeric_cols = pick_numeric_columns(df)
    non_numeric_cols_all = pick_non_numeric_columns(df)

    # Separate true categorical from long text
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

    report_summary = build_report_summary(df, numeric_cols, cat_cols)

    visuals = []

    # Missing values by column
    if quality_df["missing"].sum() > 0:
        miss = quality_df.sort_values("missing", ascending=False).head(25)
        fig = px.bar(miss, x="column", y="missing", title="Missing values by column")
        visuals.append(("missing_values", fig))

    # Numeric visuals
    if numeric_cols:
        primary = numeric_cols[0]
        fig = px.histogram(df, x=primary, title=f"Distribution of {primary}")
        visuals.append(("numeric_distribution", fig))

        if len(numeric_cols) >= 2:
            xcol = numeric_cols[0]
            ycol = numeric_cols[1]
            fig = px.scatter(df, x=xcol, y=ycol, title=f"{ycol} vs {xcol}")
            visuals.append(("numeric_scatter", fig))

    # Categorical volume charts
    for col in cat_cols[:3]:
        fig = categorical_volume_chart(df, col, max_categories=max_categories)
        visuals.append((f"category_volume_{col}", fig))

    # Categorical relationship heatmap
    if len(cat_cols) >= 2:
        fig = categorical_relationship_heatmap(
            df,
            cat_cols[0],
            cat_cols[1],
            max_categories=min(max_categories, 15),
        )
        visuals.append(("category_relationship_heatmap", fig))

    # Text length distribution if you have text like columns
    if text_like_cols:
        fig = text_length_chart(df, text_like_cols[0])
        visuals.append((f"text_length_{text_like_cols[0]}", fig))

    return report_summary, visuals, quality_df, numeric_df, categorical_df
