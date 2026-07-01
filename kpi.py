"""KPI calculation engine for PE portfolio financials.

Handles both PSE board reports and simple income statements.
"""

import pandas as pd


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Coerce all numeric-looking columns
    skip = {"company", "period", "source_file", "unit"}
    for col in df.columns:
        if col not in skip:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    is_pse = "ebitda_ytd" in df.columns

    if is_pse:
        # PSE format: EBITDA is already extracted directly
        # Compute budget variances
        for prefix in ("revenue", "total_revenue", "ebitda"):
            actual = f"{prefix}"
            budget = f"{prefix}_budget"
            var_col = f"{prefix}_variance"
            if actual in df.columns and budget in df.columns:
                df[var_col] = df[actual] - df[budget]
                df[f"{prefix}_variance_pct"] = df.apply(
                    lambda row, a=actual, b=budget: (
                        round((row[a] - row[b]) / abs(row[b]) * 100, 1)
                        if pd.notna(row.get(b)) and row.get(b) != 0
                        else None
                    ),
                    axis=1,
                )

        # EBITDA margin = EBITDA / Total Revenue
        if "ebitda" in df.columns and "total_revenue" in df.columns:
            df["ebitda_margin_pct"] = df.apply(
                lambda row: (
                    round(row["ebitda"] / row["total_revenue"] * 100, 1)
                    if pd.notna(row.get("total_revenue")) and row["total_revenue"] != 0
                    and pd.notna(row.get("ebitda"))
                    else None
                ),
                axis=1,
            )
        if "ebitda_ytd" in df.columns and "total_revenue_ytd" in df.columns:
            df["ebitda_margin_ytd_pct"] = df.apply(
                lambda row: (
                    round(row["ebitda_ytd"] / row["total_revenue_ytd"] * 100, 1)
                    if pd.notna(row.get("total_revenue_ytd")) and row["total_revenue_ytd"] != 0
                    and pd.notna(row.get("ebitda_ytd"))
                    else None
                ),
                axis=1,
            )

        # Opex ratio = |OPEX| / Total Revenue
        if "opex" in df.columns and "total_revenue" in df.columns:
            df["opex_ratio_pct"] = df.apply(
                lambda row: (
                    round(abs(row["opex"]) / row["total_revenue"] * 100, 1)
                    if pd.notna(row.get("total_revenue")) and row["total_revenue"] != 0
                    and pd.notna(row.get("opex"))
                    else None
                ),
                axis=1,
            )

        # G&A ratio = |G&A| / Total Revenue
        if "total_ga" in df.columns and "total_revenue" in df.columns:
            df["ga_ratio_pct"] = df.apply(
                lambda row: (
                    round(abs(row["total_ga"]) / row["total_revenue"] * 100, 1)
                    if pd.notna(row.get("total_revenue")) and row["total_revenue"] != 0
                    and pd.notna(row.get("total_ga"))
                    else None
                ),
                axis=1,
            )

    else:
        # Simple income statement format
        if "ebitda" not in df.columns:
            df["ebitda"] = None
        if "ebit" in df.columns and "depreciation_amortization" in df.columns:
            df["ebitda"] = df["ebitda"].fillna(
                df["ebit"].fillna(0) + df["depreciation_amortization"].fillna(0)
            )
            mask = df["ebit"].isna() & df["depreciation_amortization"].isna()
            df.loc[mask, "ebitda"] = None

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
