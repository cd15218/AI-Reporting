import streamlit as st
import pandas as pd
from charts import generate_charts
from report_ai import generate_report
from export import export_pdf, export_docx

st.set_page_config(page_title="AI Report Generator", layout="wide")

st.title("📊 AI Reporting Tool")

uploaded_file = st.file_uploader("Upload Excel or CSV", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith("csv") else pd.read_excel(uploaded_file)

    st.subheader("Data Preview")
    st.dataframe(df.head())

    report_type = st.selectbox(
        "Select Report Type",
        ["Sales", "Marketing", "Operations", "Finance"]
    )

    if st.button("Generate Report"):
        charts = generate_charts(df)
        report_text = generate_report(df, report_type)

        st.subheader("Executive Summary")
        st.write(report_text)

        for fig in charts:
            st.plotly_chart(fig, use_container_width=True)

        if st.button("Download PDF"):
            export_pdf(report_text, charts)

        if st.button("Download DOCX"):
            export_docx(report_text, charts)
