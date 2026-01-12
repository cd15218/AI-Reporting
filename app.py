# app.py
import streamlit as st
import pandas as pd
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate quick visuals, then export a clean CSV for GraphMaker.ai.")

def load_file_to_df(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()
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

summary, visuals = build_visuals(df, report_type)

# ---------- HORIZONTAL SUMMARY UI ----------
st.subheader("Dataset summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Rows", summary["rows"])
col2.metric("Columns", summary["columns"])
col3.metric("Numeric columns", len(summary["numeric_columns"]))
col4.metric("Categorical columns", len(summary["categorical_columns"]))

with st.expander("View column details"):
    st.write("Numeric columns")
    st.write(summary["numeric_columns"])
    st.write("Categorical columns")
    st.write(summary["categorical_columns"])

# ---------- CHARTS ----------
st.subheader("Charts")
if visuals:
    for chart_type, fig in visuals:
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No charts available. Try a dataset with at least one numeric column.")

# ---------- EXPORT ----------
st.subheader("Export for GraphMaker.ai")
st.write("Download your cleaned CSV and upload it to GraphMaker.ai for the most visually polished charts.")

csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv_bytes,
    file_name="report_data.csv",
    mime="text/csv",
)
