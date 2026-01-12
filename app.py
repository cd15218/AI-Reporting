import streamlit as st
import pandas as pd
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate a report summary and visualizations.")

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

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"]
    )

    report_type = st.selectbox(
        "Report type",
        ["Overview", "Trends", "Quality Check", "Executive Summary"],
        index=0
    )

    max_preview_rows = st.slider(
        "Preview rows",
        5, 100, 25
    )

    max_categories = st.slider(
        "Max categories per chart",
        5, 50, 20
    )

if not uploaded_file:
    st.info("Upload a file to get started.")
    st.stop()

try:
    df = load_file_to_df(uploaded_file)
except Exception as e:
    st.error(f"Could not read the file. {e}")
    st.stop()

df = basic_clean(df)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

with st.sidebar:
    st.header("Chart controls")

    primary_numeric = st.selectbox(
        "Primary numeric column (KPIs)",
        options=["None"] + numeric_cols
    )

    scatter_x = st.selectbox(
        "Scatter X axis",
        options=["None"] + numeric_cols
    )

    scatter_y = st.selectbox(
        "Scatter Y axis",
        options=["None"] + numeric_cols
    )

    category_volume_col = st.selectbox(
        "Category volume column",
        options=["None"] + categorical_cols
    )

    category_compare_a = st.selectbox(
        "Category comparison A",
        options=["None"] + categorical_cols
    )

    category_compare_b = st.selectbox(
        "Category comparison B",
        options=["None"] + categorical_cols
    )

st.subheader("Data preview")
st.dataframe(df.head(max_preview_rows), use_container_width=True)

user_choices = {
    "primary_numeric": None if primary_numeric == "None" else primary_numeric,
    "scatter_x": None if scatter_x == "None" else scatter_x,
    "scatter_y": None if scatter_y == "None" else scatter_y,
    "category_volume": None if category_volume_col == "None" else category_volume_col,
    "category_a": None if category_compare_a == "None" else category_compare_a,
    "category_b": None if category_compare_b == "None" else category_compare_b,
}

summary, visuals, numeric_df, categorical_df = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

# ---------- REPORT SUMMARY ----------
st.subheader("Key statistics")

k1, k2, k3, k4 = st.columns(4)

if summary["primary_numeric_column"]:
    col = summary["primary_numeric_column"]
    k1.metric(f"Average {col}", summary["mean"])
    k2.metric(f"Median {col}", summary["median"])
    k3.metric(f"Minimum {col}", summary["min"])
    k4.metric(f"Maximum {col}", summary["max"])
else:
    k1.metric("Average", "N/A")
    k2.metric("Median", "N/A")
    k3.metric("Minimum", "N/A")
    k4.metric("Maximum", "N/A")

k5, k6, k7, k8 = st.columns(4)

k5.metric("Total rows", summary["rows"])
k6.metric("Numeric columns", summary["numeric_count"])
k7.metric("Categorical columns", summary["categorical_count"])
k8.metric("Missing cells", summary["missing_cells"])

with st.expander("Numeric statistics table"):
    st.dataframe(numeric_df, use_container_width=True)

with st.expander("Categorical statistics table"):
    st.dataframe(categorical_df, use_container_width=True)

# ---------- CHARTS ----------
st.subheader("Visualizations")

if visuals:
    for name, fig in visuals:
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No charts generated. Select columns in the sidebar.")

# ---------- EXPORT ----------
st.subheader("Export")
st.write("Download your cleaned dataset for use in GraphMaker.ai or other visualization tools.")

st.download_button(
    label="Download CSV",
    data=df.to_csv(index=False),
    file_name="report_data.csv",
    mime="text/csv"
)
