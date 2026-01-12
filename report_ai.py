# report_ai.py
import pandas as pd
import plotly.express as px

def pick_numeric_columns(df: pd.DataFrame):
    return df.select_dtypes(include="number").columns.tolist()

def pick_non_numeric_columns(df: pd.DataFrame):
    return df.select_dtypes(exclude="number").columns.tolist()

def is_text_like(series: pd.Series) -> bool:
    # Heuristic: treat as text if average string length is fairly large
    s = series.dropna().astype("string")
    if s.empty:
        return False
    avg_len = s.str.len().mean()
    return avg_len is not None and avg_len >= 30

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

    title = f"Category volume: {col}"
    fig = px.bar(vc_df, x=col, y="count", title=title)
    return fig

def categorical_relationship_heatmap(df: pd.DataFrame, col_a: str, col_b: str, max_categories: int):
    a = df[col_a].astype("string").fillna("Missing")
    b = df[col_b].astype("string").fillna("Missing")

    # Limit to top categories in each column to keep heatmap readable
    top_a = a.value_counts().head(max_categories).index
    top_b = b.value_counts().head(max_categories).index

    a_filtered = a.where(a.isin(top_a), other="Other")
    b_filtered = b.where(b.isin(top_b), other="Other")

    ct = pd.crosstab(a_filtered, b_filtered)

    title = f"Category relationship: {col_a} vs {col_b}"
    fig = px.imshow(ct, title=title)
    return fig

def text_length_chart(df: pd.DataFrame, col: str):
    s = df[col].astype("string").fillna("")
    lengths = s.str.len()
    temp = pd.DataFrame({"length": lengths})

    title = f"Text length distribution: {col}"
    fig = px.histogram(temp, x="length", title=title)
    return fig

def build_visuals(df: pd.DataFrame, report_type: str, max_categories: int = 20):
    numeric_cols = pick_numeric_columns(df)
    non_numeric_cols = pick_non_numeric_columns(df)

    summary = {
        "report_type": report_type,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "numeric_columns": numeric_cols,
        "categorical_columns": non_numeric_cols,
    }

    visuals = []
    quality_df = column_quality_summary(df)

    # Missingness chart if there are missing values
    if quality_df["missing"].sum() > 0:
        miss = quality_df.sort_values("missing", ascending=False).head(25)
        fig = px.bar(miss, x="column", y="missing", title="Missing values by column")
        visuals.append(("missing_values", fig))

    # Numeric visuals (optional, still useful if present)
    if numeric_cols:
        first_num = numeric_cols[0]
        fig = px.histogram(df, x=first_num, title=f"Distribution of {first_num}")
        visuals.append(("numeric_distribution", fig))

        if len(numeric_cols) >= 2:
            xcol = numeric_cols[0]
            ycol = numeric_cols[1]
            fig = px.scatter(df, x=xcol, y=ycol, title=f"{ycol} vs {xcol}")
            visuals.append(("numeric_scatter", fig))

    # Non numeric visuals: category volume charts (the main thing you asked for)
    if non_numeric_cols:
        # Prefer true categorical like columns first (avoid long text)
        preferred = []
        text_like = []

        for col in non_numeric_cols:
            if is_text_like(df[col]):
                text_like.append(col)
            else:
                preferred.append(col)

        # Build volume charts for up to 3 categorical columns
        for col in preferred[:3]:
            fig = categorical_volume_chart(df, col, max_categories=max_categories)
            visuals.append((f"category_volume_{col}", fig))

        # Heatmap between first two categorical columns
        if len(preferred) >= 2:
            fig = categorical_relationship_heatmap(
                df,
                preferred[0],
                preferred[1],
                max_categories=min(max_categories, 15),
            )
            visuals.append(("category_relationship_heatmap", fig))

        # If there are text like columns, show length distribution for the first one
        if text_like:
            fig = text_length_chart(df, text_like[0])
            visuals.append((f"text_length_{text_like[0]}", fig))

    return summary, visuals, quality_df
