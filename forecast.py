"""Solar-shaped revenue forecast and budget risk assessment.

Uses a standard Northeast US solar generation profile to project
remaining months' revenue based on observed capture ratios.
"""

import pandas as pd

# Northeast US community solar monthly shape (% of annual generation)
# Calibrated for NY/MA/IL portfolio mix
SOLAR_SHAPE = {
    1: 4.5,   # Jan
    2: 5.5,   # Feb
    3: 7.5,   # Mar
    4: 9.0,   # Apr
    5: 10.5,  # May
    6: 11.5,  # Jun
    7: 12.0,  # Jul
    8: 11.0,  # Aug
    9: 9.0,   # Sep
    10: 7.0,  # Oct
    11: 5.0,  # Nov
    12: 3.0,  # Dec
}

# Normalize to sum to 100
_total = sum(SOLAR_SHAPE.values())
SOLAR_SHAPE_NORM = {m: v / _total * 100 for m, v in SOLAR_SHAPE.items()}

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def build_forecast(df: pd.DataFrame) -> dict:
    """Build a solar-shaped revenue forecast with risk assessment.

    Returns a dict with monthly breakdown, scenarios, and risk rating.
    """
    df = df.sort_values("period")
    latest = df.iloc[-1]

    fy_budget = latest.get("revenue_fy_budget")
    fy_forecast_mgmt = latest.get("revenue_fy_forecast")

    if pd.isna(fy_budget) or fy_budget is None or fy_budget == 0:
        return None

    # Derive monthly actuals and budgets from the data we have
    months_data = []
    prev_ytd_actual = 0.0
    prev_ytd_budget = 0.0

    for _, row in df.iterrows():
        period = row["period"]
        month_num = int(period.split("-")[1])

        ytd_actual = row.get("revenue_ytd", 0) or 0
        ytd_budget = row.get("revenue_ytd_budget", 0) or 0
        mtd_actual = row.get("revenue", 0) or 0
        mtd_budget = row.get("revenue_budget", 0) or 0

        months_data.append({
            "month": month_num,
            "name": MONTH_NAMES[month_num],
            "actual": mtd_actual,
            "budget": mtd_budget,
            "ytd_actual": ytd_actual,
            "ytd_budget": ytd_budget,
            "capture_ratio": mtd_actual / mtd_budget if mtd_budget and mtd_budget > 0 else None,
        })

    if not months_data:
        return None

    latest_month = months_data[-1]["month"]
    latest_ytd_actual = months_data[-1]["ytd_actual"]
    latest_ytd_budget = months_data[-1]["ytd_budget"]

    # Infer pre-report months (Jan through first reported month - 1)
    first_reported = months_data[0]["month"]
    if first_reported > 1 and len(months_data) >= 1:
        pre_actual = months_data[0]["ytd_actual"] - months_data[0]["actual"]
        pre_budget = months_data[0]["ytd_budget"] - months_data[0]["budget"]
        pre_shape_total = sum(SOLAR_SHAPE_NORM[m] for m in range(1, first_reported))

        for m in range(1, first_reported):
            month_weight = SOLAR_SHAPE_NORM[m] / pre_shape_total if pre_shape_total > 0 else 0
            m_actual = pre_actual * month_weight
            m_budget = pre_budget * month_weight
            months_data.insert(m - 1, {
                "month": m,
                "name": MONTH_NAMES[m],
                "actual": round(m_actual, 0),
                "budget": round(m_budget, 0),
                "ytd_actual": None,
                "ytd_budget": None,
                "capture_ratio": m_actual / m_budget if m_budget and m_budget > 0 else None,
                "inferred": True,
            })

    months_data.sort(key=lambda x: x["month"])

    # Calculate weighted average capture ratio from observed months
    # Weight by solar shape (summer months matter more)
    total_actual = sum(m["actual"] for m in months_data if m["month"] <= latest_month)
    total_budget = sum(m["budget"] for m in months_data if m["month"] <= latest_month)
    avg_capture = total_actual / total_budget if total_budget > 0 else 0

    # Recent trend (last 2 reported months)
    reported = [m for m in months_data if not m.get("inferred") and m["capture_ratio"] is not None]
    recent_capture = reported[-1]["capture_ratio"] if reported else avg_capture
    if len(reported) >= 2:
        trend = reported[-1]["capture_ratio"] - reported[-2]["capture_ratio"]
    else:
        trend = 0

    # Remaining months budget using solar shape
    remaining_budget = fy_budget - latest_ytd_budget
    remaining_shape_total = sum(SOLAR_SHAPE_NORM[m] for m in range(latest_month + 1, 13))

    projected_months = []
    for m in range(latest_month + 1, 13):
        month_weight = SOLAR_SHAPE_NORM[m] / remaining_shape_total if remaining_shape_total > 0 else 0
        m_budget = remaining_budget * month_weight
        projected_months.append({
            "month": m,
            "name": MONTH_NAMES[m],
            "budget": round(m_budget, 0),
            "shape_pct": SOLAR_SHAPE_NORM[m],
        })

    # Scenario projections
    scenarios = {}
    for name, capture in [
        ("base", avg_capture),
        ("bull", min(avg_capture * 1.15, 1.0)),  # 15% improvement, capped at 100%
        ("bear", avg_capture * 0.85),             # 15% degradation
        ("budget_required", None),                # what's needed to hit budget
    ]:
        if name == "budget_required":
            needed = fy_budget - latest_ytd_actual
            remaining_total = sum(pm["budget"] for pm in projected_months)
            req_capture = needed / remaining_total if remaining_total > 0 else float("inf")
            scenarios[name] = {
                "capture_ratio": round(req_capture, 3),
                "projected_fy": fy_budget,
                "shortfall": 0,
                "shortfall_pct": 0,
                "label": "Required to Hit Budget",
            }
        else:
            projected_remaining = sum(pm["budget"] * capture for pm in projected_months)
            projected_fy = latest_ytd_actual + projected_remaining
            shortfall = projected_fy - fy_budget
            scenarios[name] = {
                "capture_ratio": round(capture, 3),
                "projected_fy": round(projected_fy, 0),
                "shortfall": round(shortfall, 0),
                "shortfall_pct": round(shortfall / fy_budget * 100, 1),
                "label": {"base": "Base Case", "bull": "Upside", "bear": "Downside"}[name],
            }

    # Risk rating
    base_shortfall_pct = scenarios["base"]["shortfall_pct"]
    required_capture = scenarios["budget_required"]["capture_ratio"]

    if base_shortfall_pct >= -2:
        risk = "ON TRACK"
        risk_color = "#00b894"
    elif required_capture <= 1.05:
        risk = "AT RISK"
        risk_color = "#fdcb6e"
    else:
        risk = "LIKELY MISS"
        risk_color = "#d63031"

    # Build full 12-month view for charting
    monthly_chart = []
    for m in range(1, 13):
        entry = {"month": m, "name": MONTH_NAMES[m], "shape_pct": SOLAR_SHAPE_NORM[m]}
        existing = next((md for md in months_data if md["month"] == m), None)
        if existing and m <= latest_month:
            entry["actual"] = existing["actual"]
            entry["budget"] = existing["budget"]
            entry["is_actual"] = True
        else:
            proj = next((pm for pm in projected_months if pm["month"] == m), None)
            if proj:
                entry["budget"] = proj["budget"]
                entry["projected_base"] = round(proj["budget"] * scenarios["base"]["capture_ratio"], 0)
                entry["projected_bull"] = round(proj["budget"] * scenarios["bull"]["capture_ratio"], 0)
                entry["projected_bear"] = round(proj["budget"] * scenarios["bear"]["capture_ratio"], 0)
                entry["is_actual"] = False
        monthly_chart.append(entry)

    # EBITDA risk (same approach)
    ebitda_fy_budget = latest.get("ebitda_fy_budget")
    ebitda_fy_forecast = latest.get("ebitda_fy_forecast")
    ebitda_ytd = latest.get("ebitda_ytd")

    ebitda_risk = None
    if pd.notna(ebitda_fy_budget) and pd.notna(ebitda_ytd) and ebitda_fy_budget != 0:
        ebitda_shortfall = (ebitda_fy_forecast or ebitda_ytd) - ebitda_fy_budget
        ebitda_risk = {
            "fy_budget": ebitda_fy_budget,
            "fy_forecast": ebitda_fy_forecast,
            "ytd_actual": ebitda_ytd,
            "projected_shortfall": round(ebitda_shortfall, 0),
            "projected_shortfall_pct": round(ebitda_shortfall / abs(ebitda_fy_budget) * 100, 1),
        }

    return {
        "fy_budget": fy_budget,
        "fy_forecast_mgmt": fy_forecast_mgmt,
        "latest_month": latest_month,
        "latest_ytd_actual": latest_ytd_actual,
        "latest_ytd_budget": latest_ytd_budget,
        "ytd_attainment_pct": round(latest_ytd_actual / latest_ytd_budget * 100, 1) if latest_ytd_budget else 0,
        "avg_capture_ratio": round(avg_capture, 3),
        "recent_capture": round(recent_capture, 3),
        "trend": round(trend, 3),
        "scenarios": scenarios,
        "risk": risk,
        "risk_color": risk_color,
        "monthly_chart": monthly_chart,
        "ebitda_risk": ebitda_risk,
    }
