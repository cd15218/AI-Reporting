# app.py
import streamlit as st
import pandas as pd
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate visuals, then export a cleaned CSV for GraphMaker.ai.")

def load_file_to_df(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Remove completely empty columns and duplicate rows
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    return df

with st.sidebar:
    st.header("Inputs")
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

    report_type = st.selectbox(
        "Report type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0
    )

    max_preview_rows = st.slider("Preview rows", 5, 100, 25)

    max_categories = st.slider("Max categories per chart", 5, 50, 20)

if not uploaded_file:
    st.info("Upload a file to get started.")
    st.stop()

try:
    df = load_file_to_df(uploaded_file)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

df = basic_clean(df)

st.subheader("Data preview")
st.write(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")
st.dataframe(df.head(max_preview_rows), use_container_width=True)

summary, visuals, quality_df = build_visuals(df, report_type, max_categories=max_categories)

# Horizontal summary UI
st.subheader("Dataset summary")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Rows", summary["rows"])
c2.metric("Columns", summary["columns"])
c3.metric("Numeric columns", len(summary["numeric_columns"]))
c4.metric("Categorical columns", len(summary["categorical_columns"]))

with st.expander("View column lists"):
    st.write("Numeric columns")
    st.write(summary["numeric_columns"])
    st.write("Categorical columns")
    st.write(summary["categorical_columns"])

st.subheader("Column quality report")
st.dataframe(quality_df, use_container_width=True)

st.subheader("Charts")
if visuals:
    for chart_name, fig in visuals:
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No charts were generated. Try a dataset with at least one column containing values.")

st.subheader("Export for GraphMaker.ai")
st.write("Download your cleaned CSV and upload it to GraphMaker.ai for more polished visuals and formatting.")

csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv_bytes,
    file_name="report_data.csv",
    mime="text/csv",
)
