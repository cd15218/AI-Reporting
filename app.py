import streamlit as st
import pandas as pd
from report_ai import build_visuals

st.set_page_config(page_title="AI Reporting", layout="wide")

st.title("AI Reporting")
st.write("Upload a CSV or Excel file to generate key statistics and visualizations.")

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

def get_fig(visuals, key: str):
    for name, fig in visuals:
        if name == key:
            return fig
    return None

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

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

st.subheader("Data preview")
st.dataframe(df.head(max_preview_rows), use_container_width=True)

st.divider()

# ---------------- KEY STATISTICS ----------------
st.subheader("Key statistics")

left, right = st.columns([1, 2])

with left:
    primary_numeric = st.selectbox(
        "Primary numeric column (KPIs)",
        options=["None"] + numeric_cols,
        key="kpi_primary_numeric"
    )

user_choices = {
    "primary_numeric": None if primary_numeric == "None" else primary_numeric,
    "scatter_x": None,
    "scatter_y": None,
    "category_volume": None,
    "category_a": None,
    "category_b": None,
}

summary, visuals, numeric_df, categorical_df = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

with right:
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

# Optional numeric distribution chart tied to KPIs
if summary["primary_numeric_column"]:
    st.subheader("Numeric distribution")
    fig = get_fig(visuals, "numeric_distribution")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- NUMERIC COMPARISON SCATTER ----------------
st.subheader("Numeric comparison chart")

controls, chart = st.columns([1, 2])

with controls:
    scatter_x = st.selectbox(
        "X axis (numeric)",
        options=["None"] + numeric_cols,
        key="scatter_x"
    )
    scatter_y = st.selectbox(
        "Y axis (numeric)",
        options=["None"] + numeric_cols,
        key="scatter_y"
    )

user_choices = {
    "primary_numeric": None,
    "scatter_x": None if scatter_x == "None" else scatter_x,
    "scatter_y": None if scatter_y == "None" else scatter_y,
    "category_volume": None,
    "category_a": None,
    "category_b": None,
}

_, visuals_scatter, _, _ = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

with chart:
    fig = get_fig(visuals_scatter, "numeric_scatter")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select two different numeric columns to generate the scatter chart.")

st.divider()

# ---------------- CATEGORICAL VOLUME ----------------
st.subheader("Categorical volume chart")

controls, chart = st.columns([1, 2])

with controls:
    category_volume_col = st.selectbox(
        "Category column",
        options=["None"] + categorical_cols,
        key="cat_volume_col"
    )

user_choices = {
    "primary_numeric": None,
    "scatter_x": None,
    "scatter_y": None,
    "category_volume": None if category_volume_col == "None" else category_volume_col,
    "category_a": None,
    "category_b": None,
}

_, visuals_cat_vol, _, _ = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

with chart:
    fig = get_fig(visuals_cat_vol, "category_volume")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select a categorical column to generate a category volume chart.")

st.divider()

# ---------------- CATEGORICAL COMPARISON HEATMAP ----------------
st.subheader("Categorical comparison chart")

controls, chart = st.columns([1, 2])

with controls:
    category_a = st.selectbox(
        "Category A",
        options=["None"] + categorical_cols,
        key="cat_a"
    )
    category_b = st.selectbox(
        "Category B",
        options=["None"] + categorical_cols,
        key="cat_b"
    )

user_choices = {
    "primary_numeric": None,
    "scatter_x": None,
    "scatter_y": None,
    "category_volume": None,
    "category_a": None if category_a == "None" else category_a,
    "category_b": None if category_b == "None" else category_b,
}

_, visuals_heatmap, _, _ = build_visuals(
    df=df,
    report_type=report_type,
    user_choices=user_choices,
    max_categories=max_categories
)

with chart:
    fig = get_fig(visuals_heatmap, "category_heatmap")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select two different categorical columns to generate a comparison heatmap.")

st.divider()

# ---------------- EXPORT ----------------
st.subheader("Export")
st.write("Download your cleaned dataset for use in GraphMaker.ai or other visualization tools.")

st.download_button(
    label="Download CSV",
    data=df.to_csv(index=False),
    file_name="report_data.csv",
    mime="text/csv"
)
