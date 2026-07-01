"""HTML dashboard generation with Chart.js visualizations.

Handles both PSE board reports and simple income statements.
"""

import json

import pandas as pd
from jinja2 import Template


def _fmt(val, unit="$000s", decimals=0):
    if pd.isna(val) or val is None:
        return "N/A"
    if unit == "$000s":
        if abs(val) >= 1000:
            return f"${val / 1000:,.1f}M"
        return f"${val:,.{decimals}f}K"
    return f"${val:,.{decimals}f}"


def _fmt_pct(val):
    if pd.isna(val) or val is None:
        return "N/A"
    return f"{val:+.1f}%"


def _var_class(val):
    if pd.isna(val) or val is None:
        return "neutral"
    return "positive" if val >= 0 else "negative"


PSE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PSE Portfolio KPI Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #2d3436; padding: 2rem; }
        h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
        .subtitle { color: #636e72; margin-bottom: 2rem; font-size: 0.95rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: #fff; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card h2 { font-size: 1.05rem; margin-bottom: 1rem; color: #636e72; font-weight: 600; }
        .kpi-big { font-size: 2rem; font-weight: 700; color: #2d3436; }
        .kpi-label { font-size: 0.8rem; color: #b2bec3; margin-top: 0.2rem; }
        .kpi-sub { font-size: 0.9rem; margin-top: 0.4rem; }
        .positive { color: #00b894; }
        .negative { color: #d63031; }
        .neutral { color: #636e72; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th { background: #f8f9fa; text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #dee2e6; font-weight: 600; color: #636e72; }
        td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; }
        .number { text-align: right; font-variant-numeric: tabular-nums; }
        .chart-container { position: relative; height: 280px; }
        .period-tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .period-tab { padding: 0.4rem 1rem; border-radius: 6px; background: #dfe6e9; font-size: 0.85rem; font-weight: 600; cursor: default; }
        .period-tab.active { background: #0984e3; color: #fff; }
        .section-title { font-size: 1.2rem; font-weight: 700; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #dfe6e9; }
    </style>
</head>
<body>
    <h1>PSE Monthly Financial Dashboard</h1>
    <p class="subtitle">Data from {{ report_count }} monthly report(s) | Amounts in $000s</p>

    <div class="period-tabs">
    {% for p in periods %}
        <div class="period-tab{% if loop.last %} active{% endif %}">{{ p }}</div>
    {% endfor %}
    </div>

    <!-- KPI Cards -->
    <div class="grid">
        <div class="card">
            <h2>Revenue (MTD)</h2>
            <div class="kpi-big">{{ latest.revenue_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.revenue_budget_fmt }}</div>
            <div class="kpi-sub {{ latest.revenue_var_class }}">{{ latest.revenue_var_fmt }} vs budget</div>
        </div>
        <div class="card">
            <h2>Total Revenue (MTD)</h2>
            <div class="kpi-big">{{ latest.total_revenue_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.total_revenue_budget_fmt }}</div>
            <div class="kpi-sub {{ latest.total_revenue_var_class }}">{{ latest.total_revenue_var_fmt }} vs budget</div>
        </div>
        <div class="card">
            <h2>EBITDA (MTD)</h2>
            <div class="kpi-big">{{ latest.ebitda_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.ebitda_budget_fmt }}</div>
            <div class="kpi-sub {{ latest.ebitda_var_class }}">{{ latest.ebitda_var_fmt }} vs budget</div>
        </div>
        <div class="card">
            <h2>EBITDA Margin (MTD)</h2>
            <div class="kpi-big">{{ latest.ebitda_margin_fmt }}</div>
            <div class="kpi-label">EBITDA / Total Revenue</div>
        </div>
    </div>

    <!-- YTD KPI Cards -->
    <div class="section-title">Year-to-Date</div>
    <div class="grid">
        <div class="card">
            <h2>Revenue (YTD)</h2>
            <div class="kpi-big">{{ latest.revenue_ytd_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.revenue_ytd_budget_fmt }}</div>
        </div>
        <div class="card">
            <h2>Total Revenue (YTD)</h2>
            <div class="kpi-big">{{ latest.total_revenue_ytd_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.total_revenue_ytd_budget_fmt }}</div>
        </div>
        <div class="card">
            <h2>EBITDA (YTD)</h2>
            <div class="kpi-big">{{ latest.ebitda_ytd_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.ebitda_ytd_budget_fmt }}</div>
        </div>
        <div class="card">
            <h2>EBITDA Margin (YTD)</h2>
            <div class="kpi-big">{{ latest.ebitda_margin_ytd_fmt }}</div>
            <div class="kpi-label">EBITDA / Total Revenue</div>
        </div>
    </div>

    <!-- Full Year Outlook -->
    <div class="section-title">Full Year 2026 Outlook</div>
    <div class="grid">
        <div class="card">
            <h2>Revenue Forecast</h2>
            <div class="kpi-big">{{ latest.revenue_fy_forecast_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.revenue_fy_budget_fmt }}</div>
        </div>
        <div class="card">
            <h2>EBITDA Forecast</h2>
            <div class="kpi-big">{{ latest.ebitda_fy_forecast_fmt }}</div>
            <div class="kpi-label">Budget: {{ latest.ebitda_fy_budget_fmt }}</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="section-title">Trend Analysis</div>
    <div class="grid">
        <div class="card">
            <h2>Revenue: Actual vs Budget (MTD)</h2>
            <div class="chart-container">
                <canvas id="revenueChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h2>EBITDA: Actual vs Budget (MTD)</h2>
            <div class="chart-container">
                <canvas id="ebitdaChart"></canvas>
            </div>
        </div>
    </div>

    <!-- P&L Detail Table -->
    <div class="section-title">P&L Detail (All Periods)</div>
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Period</th>
                    <th class="number">Revenue</th>
                    <th class="number">Rev Budget</th>
                    <th class="number">Total Rev</th>
                    <th class="number">OPEX</th>
                    <th class="number">G&A</th>
                    <th class="number">EBITDA</th>
                    <th class="number">EBITDA Budget</th>
                    <th class="number">EBITDA Margin</th>
                </tr>
            </thead>
            <tbody>
            {% for row in table_rows %}
                <tr>
                    <td>{{ row.period }}</td>
                    <td class="number">{{ row.revenue }}</td>
                    <td class="number">{{ row.revenue_budget }}</td>
                    <td class="number">{{ row.total_revenue }}</td>
                    <td class="number">{{ row.opex }}</td>
                    <td class="number">{{ row.total_ga }}</td>
                    <td class="number {{ row.ebitda_class }}">{{ row.ebitda }}</td>
                    <td class="number">{{ row.ebitda_budget }}</td>
                    <td class="number">{{ row.ebitda_margin }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        const PERIODS = {{ periods_json | safe }};
        const COLORS = { actual: '#0984e3', budget: '#dfe6e9' };

        new Chart(document.getElementById('revenueChart'), {
            type: 'bar',
            data: {
                labels: PERIODS,
                datasets: [
                    { label: 'Actual', data: {{ rev_actual | safe }}, backgroundColor: '#0984e3', borderRadius: 4 },
                    { label: 'Budget', data: {{ rev_budget | safe }}, backgroundColor: '#dfe6e9', borderRadius: 4 },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: { y: { beginAtZero: true } }
            }
        });

        new Chart(document.getElementById('ebitdaChart'), {
            type: 'bar',
            data: {
                labels: PERIODS,
                datasets: [
                    { label: 'Actual', data: {{ ebitda_actual | safe }}, backgroundColor: '#00b894', borderRadius: 4 },
                    { label: 'Budget', data: {{ ebitda_budget | safe }}, backgroundColor: '#dfe6e9', borderRadius: 4 },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: { y: { beginAtZero: false } }
            }
        });
    </script>
</body>
</html>"""


SIMPLE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PE Portfolio KPI Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #2d3436; padding: 2rem; }
        h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .subtitle { color: #636e72; margin-bottom: 2rem; font-size: 0.95rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: #fff; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #2d3436; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th { background: #f8f9fa; text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #dee2e6; }
        td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; }
        .dscr-green { background: #d4edda; color: #155724; font-weight: 600; border-radius: 4px; padding: 2px 8px; }
        .dscr-yellow { background: #fff3cd; color: #856404; font-weight: 600; border-radius: 4px; padding: 2px 8px; }
        .dscr-red { background: #f8d7da; color: #721c24; font-weight: 600; border-radius: 4px; padding: 2px 8px; }
        .dscr-na { color: #adb5bd; }
        .number { text-align: right; font-variant-numeric: tabular-nums; }
        .chart-container { position: relative; height: 300px; }
        .kpi-boxes { display: flex; gap: 1rem; flex-wrap: wrap; }
        .kpi-box { flex: 1; min-width: 120px; text-align: center; padding: 1rem; border-radius: 8px; }
        .kpi-box .label { font-size: 0.8rem; color: #636e72; }
        .kpi-box .value { font-size: 1.4rem; font-weight: 700; margin-top: 0.3rem; }
    </style>
</head>
<body>
    <h1>PE Portfolio KPI Dashboard</h1>
    <p class="subtitle">{{ record_count }} record(s) from {{ company_count }} portfolio company/companies</p>
    <div class="card" style="margin-bottom: 1.5rem;">
        <h2>DSCR by Company (Latest Period)</h2>
        <div class="kpi-boxes">
        {% for item in dscr_summary %}
            <div class="kpi-box" style="background: {{ item.bg }};">
                <div class="label">{{ item.company }}</div>
                <div class="value" style="color: {{ item.fg }};">{{ item.display }}</div>
            </div>
        {% endfor %}
        </div>
    </div>
    <div class="card" style="margin-bottom: 1.5rem;">
        <h2>Financial Summary</h2>
        <table>
            <thead><tr><th>Company</th><th>Period</th><th class="number">Revenue</th><th class="number">EBITDA</th><th>DSCR</th></tr></thead>
            <tbody>
            {% for row in records %}
                <tr>
                    <td>{{ row.company }}</td><td>{{ row.period }}</td>
                    <td class="number">{{ row.revenue_fmt }}</td><td class="number">{{ row.ebitda_fmt }}</td>
                    <td><span class="{{ row.dscr_class }}">{{ row.dscr_fmt }}</span></td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    <div class="grid">
        <div class="card"><h2>Revenue by Company</h2><div class="chart-container"><canvas id="revenueChart"></canvas></div></div>
        <div class="card"><h2>EBITDA by Company</h2><div class="chart-container"><canvas id="ebitdaChart"></canvas></div></div>
    </div>
    <script>
        const COLORS = ['#0984e3','#00b894','#6c5ce7','#fdcb6e','#e17055','#00cec9','#d63031','#e84393'];
        new Chart(document.getElementById('revenueChart'), {
            type: 'bar', data: { labels: {{ chart_labels | safe }}, datasets: [{ label: 'Revenue', data: {{ revenue_values | safe }}, backgroundColor: COLORS.slice(0, {{ company_count }}), borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
        new Chart(document.getElementById('ebitdaChart'), {
            type: 'bar', data: { labels: {{ chart_labels | safe }}, datasets: [{ label: 'EBITDA', data: {{ ebitda_values | safe }}, backgroundColor: COLORS.slice(0, {{ company_count }}), borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    </script>
</body>
</html>"""


def _dscr_class(val):
    if pd.isna(val) or val is None:
        return "dscr-na"
    return "dscr-green" if val >= 1.5 else ("dscr-yellow" if val >= 1.2 else "dscr-red")


def _dscr_colors(val):
    if pd.isna(val) or val is None:
        return "#f8f9fa", "#adb5bd"
    if val >= 1.5:
        return "#d4edda", "#155724"
    if val >= 1.2:
        return "#fff3cd", "#856404"
    return "#f8d7da", "#721c24"


def render_html(df: pd.DataFrame, output_path: str) -> None:
    is_pse = "ebitda_ytd" in df.columns

    if is_pse:
        _render_pse(df, output_path)
    else:
        _render_simple(df, output_path)


def _render_pse(df: pd.DataFrame, output_path: str):
    df = df.sort_values("period")
    latest = df.iloc[-1]
    periods = df["period"].tolist()

    def f(val):
        return _fmt(val, "$000s")

    def fpct(val):
        if pd.isna(val) or val is None:
            return "N/A"
        return f"{val:.1f}%"

    latest_data = {
        "revenue_fmt": f(latest.get("revenue")),
        "revenue_budget_fmt": f(latest.get("revenue_budget")),
        "revenue_var_fmt": _fmt_pct(latest.get("revenue_variance_pct")),
        "revenue_var_class": _var_class(latest.get("revenue_variance_pct")),
        "total_revenue_fmt": f(latest.get("total_revenue")),
        "total_revenue_budget_fmt": f(latest.get("total_revenue_budget")),
        "total_revenue_var_fmt": _fmt_pct(latest.get("total_revenue_variance_pct")),
        "total_revenue_var_class": _var_class(latest.get("total_revenue_variance_pct")),
        "ebitda_fmt": f(latest.get("ebitda")),
        "ebitda_budget_fmt": f(latest.get("ebitda_budget")),
        "ebitda_var_fmt": _fmt_pct(latest.get("ebitda_variance_pct")),
        "ebitda_var_class": _var_class(latest.get("ebitda_variance_pct")),
        "ebitda_margin_fmt": fpct(latest.get("ebitda_margin_pct")),
        "revenue_ytd_fmt": f(latest.get("revenue_ytd")),
        "revenue_ytd_budget_fmt": f(latest.get("revenue_ytd_budget")),
        "total_revenue_ytd_fmt": f(latest.get("total_revenue_ytd")),
        "total_revenue_ytd_budget_fmt": f(latest.get("total_revenue_ytd_budget")),
        "ebitda_ytd_fmt": f(latest.get("ebitda_ytd")),
        "ebitda_ytd_budget_fmt": f(latest.get("ebitda_ytd_budget")),
        "ebitda_margin_ytd_fmt": fpct(latest.get("ebitda_margin_ytd_pct")),
        "revenue_fy_forecast_fmt": f(latest.get("revenue_fy_forecast")),
        "revenue_fy_budget_fmt": f(latest.get("revenue_fy_budget")),
        "ebitda_fy_forecast_fmt": f(latest.get("ebitda_fy_forecast")),
        "ebitda_fy_budget_fmt": f(latest.get("ebitda_fy_budget")),
    }

    table_rows = []
    for _, row in df.iterrows():
        table_rows.append({
            "period": row["period"],
            "revenue": f(row.get("revenue")),
            "revenue_budget": f(row.get("revenue_budget")),
            "total_revenue": f(row.get("total_revenue")),
            "opex": f(row.get("opex")),
            "total_ga": f(row.get("total_ga")),
            "ebitda": f(row.get("ebitda")),
            "ebitda_budget": f(row.get("ebitda_budget")),
            "ebitda_margin": fpct(row.get("ebitda_margin_pct")),
            "ebitda_class": _var_class(row.get("ebitda")),
        })

    rev_actual = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in df["revenue"]])
    rev_budget = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in df["revenue_budget"]])
    ebitda_actual = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in df["ebitda"]])
    ebitda_budget = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in df["ebitda_budget"]])

    template = Template(PSE_TEMPLATE)
    html = template.render(
        latest=latest_data,
        periods=periods,
        periods_json=json.dumps(periods),
        table_rows=table_rows,
        rev_actual=rev_actual,
        rev_budget=rev_budget,
        ebitda_actual=ebitda_actual,
        ebitda_budget=ebitda_budget,
        report_count=len(df),
    )

    with open(output_path, "w") as file:
        file.write(html)


def _render_simple(df: pd.DataFrame, output_path: str):
    records = []
    for _, row in df.iterrows():
        records.append({
            "company": row.get("company", ""),
            "period": row.get("period", ""),
            "revenue_fmt": _fmt(row.get("revenue"), row.get("unit", "$")),
            "ebitda_fmt": _fmt(row.get("ebitda"), row.get("unit", "$")),
            "dscr_fmt": f'{row["dscr"]:.2f}x' if pd.notna(row.get("dscr")) else "N/A",
            "dscr_class": _dscr_class(row.get("dscr")),
        })

    latest = df.sort_values("period").groupby("company").last().reset_index()
    dscr_summary = []
    for _, row in latest.iterrows():
        bg, fg = _dscr_colors(row.get("dscr"))
        dscr_summary.append({
            "company": row["company"],
            "display": f'{row["dscr"]:.2f}x' if pd.notna(row.get("dscr")) else "N/A",
            "bg": bg, "fg": fg,
        })

    chart_labels = json.dumps(latest["company"].tolist())
    revenue_values = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in latest["revenue"]])
    ebitda_values = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in latest["ebitda"]])

    template = Template(SIMPLE_TEMPLATE)
    html = template.render(
        records=records, dscr_summary=dscr_summary,
        chart_labels=chart_labels, revenue_values=revenue_values, ebitda_values=ebitda_values,
        record_count=len(df), company_count=latest.shape[0],
    )

    with open(output_path, "w") as file:
        file.write(html)
