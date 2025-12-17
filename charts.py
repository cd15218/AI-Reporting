import plotly.express as px

def generate_charts(df):
    charts = []

    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        fig = px.line(df, y=numeric_cols[0], title="Trend Overview")
        charts.append(fig)

    if len(df.columns) >= 2:
        fig2 = px.bar(df, x=df.columns[0], y=numeric_cols[0], title="Category Breakdown")
        charts.append(fig2)

    return charts
