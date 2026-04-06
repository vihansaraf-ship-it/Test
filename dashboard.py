"""HTML dashboard generation with Chart.js visualizations."""

import json

import pandas as pd
from jinja2 import Template

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
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
        .chart-container { position: relative; height: 300px; }
        .kpi-boxes { display: flex; gap: 1rem; flex-wrap: wrap; }
        .kpi-box { flex: 1; min-width: 120px; text-align: center; padding: 1rem; border-radius: 8px; }
        .kpi-box .label { font-size: 0.8rem; color: #636e72; }
        .kpi-box .value { font-size: 1.4rem; font-weight: 700; margin-top: 0.3rem; }
        .number { text-align: right; font-variant-numeric: tabular-nums; }
    </style>
</head>
<body>
    <h1>PE Portfolio KPI Dashboard</h1>
    <p class="subtitle">{{ record_count }} record(s) from {{ company_count }} portfolio company/companies</p>

    <!-- DSCR Indicators -->
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

    <!-- Summary Table -->
    <div class="card" style="margin-bottom: 1.5rem;">
        <h2>Financial Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Period</th>
                    <th class="number">Revenue</th>
                    <th class="number">EBITDA</th>
                    <th>DSCR</th>
                </tr>
            </thead>
            <tbody>
            {% for row in records %}
                <tr>
                    <td>{{ row.company }}</td>
                    <td>{{ row.period }}</td>
                    <td class="number">{{ row.revenue_fmt }}</td>
                    <td class="number">{{ row.ebitda_fmt }}</td>
                    <td><span class="{{ row.dscr_class }}">{{ row.dscr_fmt }}</span></td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Charts -->
    <div class="grid">
        <div class="card">
            <h2>Revenue by Company</h2>
            <div class="chart-container">
                <canvas id="revenueChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h2>EBITDA by Company</h2>
            <div class="chart-container">
                <canvas id="ebitdaChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const COLORS = ['#0984e3','#00b894','#6c5ce7','#fdcb6e','#e17055','#00cec9','#d63031','#e84393'];

        // Revenue bar chart
        new Chart(document.getElementById('revenueChart'), {
            type: 'bar',
            data: {
                labels: {{ chart_labels | safe }},
                datasets: [{
                    label: 'Revenue',
                    data: {{ revenue_values | safe }},
                    backgroundColor: COLORS.slice(0, {{ company_count }}),
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });

        // EBITDA bar chart
        new Chart(document.getElementById('ebitdaChart'), {
            type: 'bar',
            data: {
                labels: {{ chart_labels | safe }},
                datasets: [{
                    label: 'EBITDA',
                    data: {{ ebitda_values | safe }},
                    backgroundColor: COLORS.slice(0, {{ company_count }}),
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    </script>
</body>
</html>"""


def _fmt_number(val, prefix="$") -> str:
    if pd.isna(val) or val is None:
        return "N/A"
    return f"{prefix}{val:,.0f}"


def _dscr_class(val) -> str:
    if pd.isna(val) or val is None:
        return "dscr-na"
    if val >= 1.5:
        return "dscr-green"
    if val >= 1.2:
        return "dscr-yellow"
    return "dscr-red"


def _dscr_colors(val):
    if pd.isna(val) or val is None:
        return "#f8f9fa", "#adb5bd"
    if val >= 1.5:
        return "#d4edda", "#155724"
    if val >= 1.2:
        return "#fff3cd", "#856404"
    return "#f8d7da", "#721c24"


def render_html(df: pd.DataFrame, output_path: str) -> None:
    """Render the KPI dashboard as a static HTML file."""
    # Build table records
    records = []
    for _, row in df.iterrows():
        records.append({
            "company": row.get("company", ""),
            "period": row.get("period", ""),
            "revenue_fmt": _fmt_number(row.get("revenue")),
            "ebitda_fmt": _fmt_number(row.get("ebitda")),
            "dscr_fmt": f'{row["dscr"]:.2f}x' if pd.notna(row.get("dscr")) else "N/A",
            "dscr_class": _dscr_class(row.get("dscr")),
        })

    # Latest period per company for DSCR summary
    latest = df.sort_values("period").groupby("company").last().reset_index()
    dscr_summary = []
    for _, row in latest.iterrows():
        bg, fg = _dscr_colors(row.get("dscr"))
        dscr_summary.append({
            "company": row["company"],
            "display": f'{row["dscr"]:.2f}x' if pd.notna(row.get("dscr")) else "N/A",
            "bg": bg,
            "fg": fg,
        })

    # Chart data (latest period per company)
    chart_labels = json.dumps(latest["company"].tolist())
    revenue_values = json.dumps([
        round(v, 0) if pd.notna(v) else 0 for v in latest["revenue"]
    ])
    ebitda_values = json.dumps([
        round(v, 0) if pd.notna(v) else 0 for v in latest["ebitda"]
    ])

    template = Template(DASHBOARD_TEMPLATE)
    html = template.render(
        records=records,
        dscr_summary=dscr_summary,
        chart_labels=chart_labels,
        revenue_values=revenue_values,
        ebitda_values=ebitda_values,
        record_count=len(df),
        company_count=latest.shape[0],
    )

    with open(output_path, "w") as f:
        f.write(html)
