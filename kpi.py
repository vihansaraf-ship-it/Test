"""KPI calculation engine for PE portfolio financials."""

import pandas as pd


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Revenue, EBITDA, and DSCR KPIs.

    - Revenue: extracted directly (no calculation needed)
    - EBITDA: uses extracted value if available, otherwise EBIT + D&A
    - DSCR: EBITDA / Total Debt Service (None if debt service missing/zero)
    """
    df = df.copy()

    # Ensure numeric columns
    numeric_fields = [
        "revenue", "cogs", "gross_profit", "opex",
        "depreciation_amortization", "ebit", "interest_expense",
        "tax_expense", "net_income", "ebitda", "total_debt_service",
    ]
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # EBITDA: prefer extracted value, fall back to EBIT + D&A
    if "ebitda" not in df.columns:
        df["ebitda"] = None
    if "ebit" in df.columns and "depreciation_amortization" in df.columns:
        df["ebitda"] = df["ebitda"].fillna(
            df["ebit"].fillna(0) + df["depreciation_amortization"].fillna(0)
        )
        # Only set EBITDA if at least one component was present
        mask = df["ebit"].isna() & df["depreciation_amortization"].isna()
        df.loc[mask, "ebitda"] = None

    # DSCR: EBITDA / Total Debt Service
    if "total_debt_service" in df.columns:
        df["dscr"] = df.apply(
            lambda row: (
                round(row["ebitda"] / row["total_debt_service"], 2)
                if pd.notna(row.get("ebitda"))
                and pd.notna(row.get("total_debt_service"))
                and row["total_debt_service"] > 0
                else None
            ),
            axis=1,
        )
    else:
        df["dscr"] = None

    return df
