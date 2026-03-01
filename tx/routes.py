from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
import pandas as pd
import os
import math
import json
from datetime import datetime
import matplotlib.pyplot as plt

from auth import requires_permission

tx_bp = Blueprint(
           "tx",
            __name__,
            url_prefix="/tx"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

TX_CSV = os.path.join(DATA_DIR, "tx.csv")

def load_data():
    """
    Robust CSV loader for tx.csv that tolerates:
    - inconsistent column counts
    - bad lines
    - missing values
    """

#    if not TX_CSV.exists():
#        current_app.logger.warning(f"{TX_CSV} not found")
#        return pd.DataFrame()

    try:
        df = pd.read_csv(
            TX_CSV,
            engine="python",
            on_bad_lines="skip"
        )
    except Exception as e:
        current_app.logger.exception(f"Failed reading {TX_CSV}: {e}", e)
        return pd.DataFrame()

    # Standardise column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Ensure required columns exist
    required = ["date", "supplier", "amount", "expense_area"]
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Clean values
    df["supplier"] = df["supplier"].astype(str).str.upper().str.strip()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Keep only suppliers of interest
    df = df[df["supplier"].isin([
        "CAPITA PENSION SOLUTIONS LTD",
        "MYCSP LTD"
    ])]

    return df


@tx_bp.route("/dashboard", methods=['POST','GET'])
@login_required
@requires_permission()
def dashboard():
    # --- 1. Read your CSV ---
    df = load_data()

    # --- 2. Ensure numeric 'amount' and valid dates ---
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date", "supplier"])

    # --- 3. Uppercase supplier for consistency ---
    df["supplier"] = df["supplier"].str.upper().str.strip()

    # --- 4. Extract month (YYYY-MM) ---
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # --- 5. Get all suppliers and all months ---
    suppliers = df["supplier"].unique()
    all_months = pd.period_range(df["date"].min(), df["date"].max(), freq="M").astype(str)

    # --- 6. Aggregate monthly sums ---
#    monthly = df.groupby(["month", "supplier"], as_index=False)["amount"].sum()

    monthly = (
       df.groupby(["month", "supplier"], as_index=False)
         .agg(amount=("amount", "sum"), transaction_count=("amount", "count"))
    )


    # --- 7. Fill missing month × supplier combinations ---
    full_index = pd.MultiIndex.from_product([all_months, suppliers], names=["month", "supplier"])
    monthly_full = monthly.set_index(["month", "supplier"]).reindex(full_index, fill_value=0).reset_index()

    # --- 8. Pivot for chart (month x supplier) ---
    df_pivot = monthly_full.pivot(index="month", columns="supplier", values="amount")

    # --- 9. Prepare Chart.js data ---
    chart_labels = df_pivot.index.astype(str).tolist()  # months as strings
    chart_datasets = [
        {"label": s, "data": df_pivot[s].astype(float).tolist()}  # convert Series to list of floats
        for s in df_pivot.columns
    ]

    # --- 10. Prepare monthly table for template ---
    monthly_table = monthly_full.to_dict(orient="records")

    # --- 11. Prepare summary card per supplier ---
    supplier_summary = {}
    for supplier, sdf in df.groupby("supplier"):
        supplier_summary[supplier] = {
            "total_amount": float(sdf["amount"].sum()),
            "transaction_count": int(len(sdf)),
            "min_date": sdf["date"].min().strftime("%Y-%m-%d"),
            "max_date": sdf["date"].max().strftime("%Y-%m-%d"),
        }

    # --- 12. Example: top expense areas ---
    top_expense_areas = (
        df.groupby("expense_area")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .to_dict(orient="records")
    )

    # --- 13. Supplier colors (optional) ---
    supplier_colors = {s: f"hsl({i * 60 % 360}, 70%, 50%)" for i, s in enumerate(suppliers)}

    # --- 14. Render template ---
    return render_template(
        "tx/tx_dashboard.html",
        page_title="Dashboard: transactions",
        chart_labels=chart_labels,
        chart_datasets=chart_datasets,
        supplier_colors=supplier_colors,
        suppliers=list(suppliers),
        supplier_summary=supplier_summary,
        monthly_table=monthly_table,
        top_expense_areas=top_expense_areas,
        last_updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

