import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Milestone Completeness Checker", layout="wide")

st.title("📦 Milestone Completeness & Data Quality")

st.write(
    """
Upload your **raw Data Quality Excel file** and this app will:
1. Add a **Tracking Status** column based on milestone availability  
2. Create a **summary table by Pickup Country**  
3. Allow you to download a processed Excel with all results.
"""
)

# File uploader
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# ✅ UPDATED milestone column names
MILESTONE_COLS = [
    "Pickup Departure Milestone",
    "Pickup Arrival Milestone",
    "Dropoff Departure Milestone",
    "Dropoff Arrival Milestone",
]

PICKUP_COUNTRY_COL = "Pickup Country"


def compute_tracking_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'Tracking Status' column:
    - Fully Tracked: all 4 milestones present
    - Untracked: no milestones present
    - Partially Tracked: everything else
    """
    missing_cols = [c for c in MILESTONE_COLS if c not in df.columns]
    if missing_cols:
        raise KeyError(
            f"Missing required milestone columns: {missing_cols}"
        )

    def determine_status(row: pd.Series) -> str:
        milestones = row[MILESTONE_COLS]
        if milestones.isna().all():
            return "Untracked"
        elif milestones.notna().all():
            return "Fully Tracked"
        else:
            return "Partially Tracked"

    df = df.copy()
    df["Tracking Status"] = df.apply(determine_status, axis=1)
    return df


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds summary table by Pickup Country
    """
    if PICKUP_COUNTRY_COL not in df.columns:
        raise KeyError(
            f"Required column '{PICKUP_COUNTRY_COL}' is missing."
        )

    summary = (
        df.groupby(PICKUP_COUNTRY_COL)["Tracking Status"]
        .value_counts()
        .unstack(fill_value=0)
    )

    # Ensure all columns exist
    for col in ["Fully Tracked", "Partially Tracked", "Untracked"]:
        if col not in summary.columns:
            summary[col] = 0

    summary = summary[
        ["Fully Tracked", "Partially Tracked", "Untracked"]
    ]

    summary["Grand Total"] = summary.sum(axis=1)

    summary["Fully Tracked %"] = (
        summary["Fully Tracked"] / summary["Grand Total"]
    ) * 100

    summary["Data Availability %"] = (
        (summary["Fully Tracked"] + summary["Partially Tracked"])
        / summary["Grand Total"]
    ) * 100

    summary = summary.reset_index().sort_values(
        "Grand Total", ascending=False
    )

    return summary


def create_excel_output(df_enriched, summary_df) -> bytes:
    """
    Creates Excel with:
    - Enriched Data
    - Summary
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_enriched.to_excel(writer, sheet_name="Enriched Data", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
    buffer.seek(0)
    return buffer.getvalue()


if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)

        st.subheader("🔍 Raw Data Preview")
        st.dataframe(df_raw.head())

        df_enriched = compute_tracking_status(df_raw)

        st.subheader("✅ Enriched Data (Tracking Status Added)")
        st.dataframe(df_enriched.head())

        summary_df = build_summary(df_enriched)

        st.subheader("📊 Summary by Pickup Country")
        st.dataframe(summary_df)

        excel_file = create_excel_output(df_enriched, summary_df)

        st.download_button(
            label="⬇️ Download Processed Excel",
            data=excel_file,
            file_name="processed_data_quality.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("👆 Upload an Excel file to start")

