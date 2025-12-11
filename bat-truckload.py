import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Milestone Completeness Checker", layout="wide")

st.title("📦 Milestone Completeness & Data Quality")

st.write(
    """
Upload your **Data Quality raw Excel file** and this app will:
1. Add a **Tracking Status** column based on milestone timestamps  
2. Create a **summary table by Pickup Country** with Fully/Partially/Untracked and percentages  
3. Allow you to download the processed Excel with both sheets.
"""
)

# File uploader
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# Column names used for tracking logic
MILESTONE_COLS = [
    "Pickup Arrival Utc Timestamp Raw",
    "Pickup Departure Utc Timestamp Raw",
    "Dropoff Arrival Utc Timestamp Raw",
    "Dropoff Departure Utc Timestamp Raw",
]

PICKUP_COUNTRY_COL = "Pickup Country"


def compute_tracking_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'Tracking Status' column based on milestone columns:
    - Fully Tracked: all 4 non-null
    - Untracked: all 4 null
    - Partially Tracked: everything else
    """
    missing_cols = [c for c in MILESTONE_COLS if c not in df.columns]
    if missing_cols:
        raise KeyError(
            f"These required columns are missing from the file: {missing_cols}"
        )

    def status_row(row: pd.Series) -> str:
        vals = row[MILESTONE_COLS]
        if vals.isna().all():
            return "Untracked"
        elif vals.notna().all():
            return "Fully Tracked"
        else:
            return "Partially Tracked"

    df = df.copy()
    df["Tracking Status"] = df.apply(status_row, axis=1)
    return df


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds summary by Pickup Country:
    - Fully Tracked
    - Partially Tracked
    - Untracked
    - Grand Total
    - Fully Tracked %
    - Data Availability %
    """
    if PICKUP_COUNTRY_COL not in df.columns:
        raise KeyError(
            f"Required column '{PICKUP_COUNTRY_COL}' is missing from the file."
        )

    # Group by Pickup Country & Tracking Status
    summary = (
        df.groupby(PICKUP_COUNTRY_COL)["Tracking Status"]
        .value_counts()
        .unstack(fill_value=0)
    )

    # Ensure all 3 tracking columns exist
    for col in ["Fully Tracked", "Partially Tracked", "Untracked"]:
        if col not in summary.columns:
            summary[col] = 0

    # Reorder columns
    summary = summary[["Fully Tracked", "Partially Tracked", "Untracked"]]

    # Grand Total
    summary["Grand Total"] = summary[
        ["Fully Tracked", "Partially Tracked", "Untracked"]
    ].sum(axis=1)

    # Percentages
    summary["Fully Tracked %"] = summary["Fully Tracked"] / summary["Grand Total"]
    summary["Data Availability %"] = (
        summary["Fully Tracked"] + summary["Partially Tracked"]
    ) / summary["Grand Total"]

    # Sort by Grand Total descending
    summary = summary.sort_values("Grand Total", ascending=False)

    # Optional: format percentages as 0–100 instead of 0–1
    summary["Fully Tracked %"] = summary["Fully Tracked %"] * 100
    summary["Data Availability %"] = summary["Data Availability %"] * 100

    # Reset index for nicer display
    summary = summary.reset_index()

    return summary


def create_output_excel(df_enriched: pd.DataFrame, summary: pd.DataFrame) -> bytes:
    """
    Returns a bytes object containing an Excel file with:
    - Sheet 'Enriched Data'
    - Sheet 'Summary'
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_enriched.to_excel(writer, sheet_name="Enriched Data", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
    output.seek(0)
    return output.getvalue()


if uploaded_file is not None:
    try:
        # Read Excel
        df_raw = pd.read_excel(uploaded_file)

        st.subheader("🔍 Raw Data Preview")
        st.dataframe(df_raw.head())

        # Compute tracking status
        df_enriched = compute_tracking_status(df_raw)

        st.subheader("✅ Enriched Data (with Tracking Status)")
        st.dataframe(df_enriched.head())

        # Build summary
        summary_df = build_summary(df_enriched)

        st.subheader("📊 Summary by Pickup Country")
        st.dataframe(summary_df)

        # Create downloadable Excel
        excel_bytes = create_output_excel(df_enriched, summary_df)

        st.download_button(
            label="⬇️ Download Processed Excel",
            data=excel_bytes,
            file_name="processed_data_quality.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except KeyError as e:
        st.error(f"Column error: {e}")
    except Exception as e:
        st.error(f"Something went wrong while processing the file: {e}")
else:
    st.info("👆 Please upload your Excel file to begin.")
