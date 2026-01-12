# app.py
import streamlit as st
import pandas as pd
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate a report summary and charts, then export a cleaned CSV for GraphMaker.ai.")

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
st.dataframe(df.head(max_preview_rows), use_container_width=True)

report_summary, visuals, quality_df, numeric_df, categorical_df = build_visuals(
    df,
    report_type,
    max_categories=max_categories
)

st.subheader("Report summary")

# Horizontal KPI style summary, focused on key statistics
k1, k2, k3, k4 = st.columns(4)

if report_summary["primary_numeric_column"]:
    k1.metric(
        f"Average {report_summary['primary_numeric_column']}",
        report_summary["primary_mean"] if report_summary["primary_mean"] is not None else "N/A"
    )
    k2.metric(
        f"Median {report_summary['primary_numeric_column']}",
        report_summary["primary_median"] if report_summary["primary_median"] is not None else "N/A"
    )
    k3.metric(
        f"Min {report_summary['primary_numeric_column']}",
        report_summary["primary_min"] if report_summary["primary_min"] is not None else "N/A"
    )
    k4.metric(
        f"Max {report_summary['primary_numeric_column']}",
        report_summary["primary_max"] if report_summary["primary_max"] is not None else "N/A"
    )
else:
    k1.metric("Average", "N/A")
    k2.metric("Median", "N/A")
    k3.metric("Min", "N/A")
    k4.metric("Max", "N/A")

k5, k6, k7, k8 = st.columns(4)

if report_summary["primary_categorical_column"] and report_summary["top_category_label"] is not None:
    k5.metric(
        f"Top {report_summary['primary_categorical_column']}",
        report_summary["top_category_label"]
    )
    k6.metric(
        "Top category count",
        report_summary["top_category_count"]
    )
else:
    k5.metric("Top category", "N/A")
    k6.metric("Top category count", "N/A")

k7.metric("Total missing cells", report_summary["total_missing_cells"])
k8.metric("Report type", report_summary.get("report_type", report_type))

with st.expander("Numeric statistics table"):
    if numeric_df is not None and not numeric_df.empty:
        st.dataframe(numeric_df, use_container_width=True)
    else:
        st.write("No numeric columns found.")

with st.expander("Categorical statistics table"):
    if categorical_df is not None and not categorical_df.empty:
        st.dataframe(categorical_df[["column", "unique_values", "top_value", "top_count"]], use_container_width=True)
        st.write("Top values per categorical column")
        st.write(categorical_df[["column", "top_values"]])
    else:
        st.write("No categorical columns found.")

st.subheader("Column quality report")
st.dataframe(quality_df, use_container_width=True)

st.subheader("Charts")
if visuals:
    for chart_name, fig in visuals:
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No charts were generated.")

st.subheader("Export for GraphMaker.ai")
st.write("Download your cleaned CSV and upload it to GraphMaker.ai for more polished visuals and formatting.")

csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv_bytes,
    file_name="report_data.csv",
    mime="text/csv",
)
