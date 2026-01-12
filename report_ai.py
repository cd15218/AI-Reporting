# report_ai.py
import pandas as pd
import plotly.express as px

def pick_numeric_columns(df: pd.DataFrame):
    return df.select_dtypes(include="number").columns.tolist()

def pick_categorical_columns(df: pd.DataFrame):
    cols = df.select_dtypes(exclude="number").columns.tolist()
    return cols

def build_visuals(df: pd.DataFrame, report_type: str):
    numeric_cols = pick_numeric_columns(df)
    cat_cols = pick_categorical_columns(df)

    visuals = []

    # 1) Summary KPIs
    summary = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
    }

    # 2) Default chart: distribution of the first numeric column
    if numeric_cols:
        col = numeric_cols[0]
        fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        visuals.append(("histogram", fig))

    # 3) If you have at least one categorical and one numeric: bar chart by category
    if cat_cols and numeric_cols:
        cat = cat_cols[0]
        val = numeric_cols[0]
        grouped = df.groupby(cat, dropna=False)[val].mean().reset_index()
        grouped = grouped.sort_values(val, ascending=False).head(20)

        fig = px.bar(grouped, x=cat, y=val, title=f"Average {val} by {cat}")
        visuals.append(("bar", fig))

    # 4) If you have two numeric columns: scatter plot
    if len(numeric_cols) >= 2:
        xcol = numeric_cols[0]
        ycol = numeric_cols[1]
        fig = px.scatter(df, x=xcol, y=ycol, title=f"{ycol} vs {xcol}")
        visuals.append(("scatter", fig))

    return summary, visuals
