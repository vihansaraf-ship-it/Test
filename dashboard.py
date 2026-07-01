"""HTML dashboard generation focused on budget risk and solar-shaped forecasting."""

import json

import pandas as pd
from jinja2 import Template

from forecast import build_forecast


def _fmt(val, decimals=0):
    if pd.isna(val) or val is None:
        return "N/A"
    if abs(val) >= 1000:
        return f"${val / 1000:,.1f}M"
    return f"${val:,.{decimals}f}K"


def _fmt_pct(val):
    if pd.isna(val) or val is None:
        return "N/A"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PSE Budget Risk Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        :root { --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a; --text: #e4e4e7; --muted: #71717a; --accent: #3b82f6; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Menlo, monospace; background: var(--bg); color: var(--text); padding: 2rem; }
        h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.3rem; }
        .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-bottom: 1.5rem; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.2rem; margin-bottom: 1.5rem; }
        .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1.2rem; margin-bottom: 1.5rem; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.3rem; }
        .card-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .card-value { font-size: 1.8rem; font-weight: 700; font-variant-numeric: tabular-nums; }
        .card-sub { font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; }
        .positive { color: #22c55e; }
        .negative { color: #ef4444; }
        .warning { color: #eab308; }
        .risk-badge { display: inline-block; padding: 0.3rem 1rem; border-radius: 6px; font-weight: 700; font-size: 1rem; letter-spacing: 0.08em; }
        .hero { text-align: center; padding: 2rem; margin-bottom: 1.5rem; }
        .hero .card-value { font-size: 3rem; }
        .hero .card-sub { font-size: 1rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; font-variant-numeric: tabular-nums; }
        th { text-align: left; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border); color: var(--muted); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
        td { padding: 0.5rem 0.7rem; border-bottom: 1px solid rgba(255,255,255,0.04); }
        .r { text-align: right; }
        .chart-container { position: relative; height: 300px; }
        .section { margin-top: 2rem; margin-bottom: 1rem; }
        .section-title { font-size: 1rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); margin-bottom: 1.2rem; }
        .shape-bar { display: inline-block; height: 6px; border-radius: 3px; background: var(--accent); opacity: 0.5; vertical-align: middle; margin-left: 0.5rem; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
        .tag-actual { background: rgba(59,130,246,0.15); color: #60a5fa; }
        .tag-projected { background: rgba(234,179,8,0.15); color: #eab308; }
    </style>
</head>
<body>

<h1>PSE 2026 Budget Risk Dashboard</h1>
<p class="subtitle">Revenue forecast through solar-shaped projection | Data through {{ latest_month_name }} 2026 | Amounts in $000s</p>

<!-- HERO: Risk Rating -->
<div class="card hero">
    <div class="card-label">2026 Revenue Budget Risk</div>
    <div style="margin-bottom: 1rem;">
        <span class="risk-badge" style="background: {{ risk_color }}20; color: {{ risk_color }};">{{ risk }}</span>
    </div>
    <div class="card-value" style="color: {{ risk_color }};">{{ base_shortfall_fmt }}</div>
    <div class="card-sub">Projected {{ base_shortfall_pct }} vs FY budget of {{ fy_budget_fmt }}</div>
</div>

<!-- KPI Row -->
<div class="grid-4">
    <div class="card">
        <div class="card-label">YTD Revenue</div>
        <div class="card-value">{{ ytd_actual_fmt }}</div>
        <div class="card-sub">{{ ytd_attainment_pct }}% of YTD budget</div>
    </div>
    <div class="card">
        <div class="card-label">Capture Ratio (Avg)</div>
        <div class="card-value {% if avg_capture < 0.9 %}negative{% elif avg_capture < 0.95 %}warning{% else %}positive{% endif %}">{{ avg_capture_fmt }}</div>
        <div class="card-sub">Actual / Budget revenue</div>
    </div>
    <div class="card">
        <div class="card-label">Required Capture (Jun-Dec)</div>
        <div class="card-value {% if req_capture > 1.0 %}negative{% elif req_capture > 0.95 %}warning{% else %}positive{% endif %}">{{ req_capture_fmt }}</div>
        <div class="card-sub">Needed to hit FY budget</div>
    </div>
    <div class="card">
        <div class="card-label">Mgmt FY Forecast</div>
        <div class="card-value">{{ mgmt_forecast_fmt }}</div>
        <div class="card-sub">{{ mgmt_forecast_gap }}</div>
    </div>
</div>

<!-- EBITDA Risk -->
{% if ebitda_risk %}
<div class="grid-3">
    <div class="card">
        <div class="card-label">EBITDA YTD</div>
        <div class="card-value">{{ ebitda_ytd_fmt }}</div>
        <div class="card-sub">vs Budget: {{ ebitda_budget_fmt }}</div>
    </div>
    <div class="card">
        <div class="card-label">EBITDA FY Forecast</div>
        <div class="card-value">{{ ebitda_forecast_fmt }}</div>
        <div class="card-sub">Budget: {{ ebitda_budget_fy_fmt }}</div>
    </div>
    <div class="card">
        <div class="card-label">EBITDA Shortfall</div>
        <div class="card-value {{ 'negative' if ebitda_shortfall < 0 else 'positive' }}">{{ ebitda_shortfall_fmt }}</div>
        <div class="card-sub">{{ ebitda_shortfall_pct }} vs budget</div>
    </div>
</div>
{% endif %}

<!-- Charts -->
<div class="section">
    <div class="section-title">Monthly Revenue: Actual + Projected vs Budget</div>
</div>
<div class="card" style="margin-bottom: 1.5rem;">
    <div class="chart-container" style="height: 350px;">
        <canvas id="mainChart"></canvas>
    </div>
</div>

<!-- Scenario Comparison -->
<div class="section">
    <div class="section-title">Scenario Analysis</div>
</div>
<div class="card" style="margin-bottom: 1.5rem;">
    <table>
        <thead>
            <tr>
                <th>Scenario</th>
                <th class="r">Capture Ratio</th>
                <th class="r">Projected FY Revenue</th>
                <th class="r">vs Budget</th>
                <th class="r">Shortfall %</th>
            </tr>
        </thead>
        <tbody>
        {% for s in scenarios %}
            <tr>
                <td><strong>{{ s.label }}</strong></td>
                <td class="r">{{ s.capture_fmt }}</td>
                <td class="r">{{ s.fy_fmt }}</td>
                <td class="r {{ s.class }}">{{ s.shortfall_fmt }}</td>
                <td class="r {{ s.class }}">{{ s.pct_fmt }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>

<!-- Solar Shape + Monthly Detail -->
<div class="section">
    <div class="section-title">Monthly Detail (Solar-Shaped Budget Allocation)</div>
</div>
<div class="card">
    <table>
        <thead>
            <tr>
                <th>Month</th>
                <th class="r">Solar Weight</th>
                <th class="r">Budget</th>
                <th class="r">Actual / Projected</th>
                <th class="r">Capture</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
        {% for m in monthly %}
            <tr style="{% if not m.is_actual %}opacity: 0.7;{% endif %}">
                <td>{{ m.name }}</td>
                <td class="r">{{ m.shape }}%<span class="shape-bar" style="width: {{ m.shape_width }}px;"></span></td>
                <td class="r">{{ m.budget_fmt }}</td>
                <td class="r">{{ m.value_fmt }}</td>
                <td class="r {{ m.capture_class }}">{{ m.capture_fmt }}</td>
                <td>{% if m.is_actual %}<span class="tag tag-actual">Actual</span>{% else %}<span class="tag tag-projected">Projected</span>{% endif %}</td>
            </tr>
        {% endfor %}
            <tr style="font-weight: 700; border-top: 2px solid var(--border);">
                <td>Full Year</td>
                <td class="r">100%</td>
                <td class="r">{{ fy_budget_fmt }}</td>
                <td class="r">{{ fy_projected_fmt }}</td>
                <td class="r {{ fy_capture_class }}">{{ fy_capture_fmt }}</td>
                <td></td>
            </tr>
        </tbody>
    </table>
</div>

<script>
Chart.defaults.color = '#71717a';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';

const months = {{ months_json | safe }};
const budget = {{ budget_json | safe }};
const actuals = {{ actuals_json | safe }};
const projBase = {{ proj_base_json | safe }};
const projBull = {{ proj_bull_json | safe }};
const projBear = {{ proj_bear_json | safe }};

new Chart(document.getElementById('mainChart'), {
    type: 'bar',
    data: {
        labels: months,
        datasets: [
            {
                label: 'Actual',
                data: actuals,
                backgroundColor: '#3b82f6',
                borderRadius: 4,
                order: 2,
            },
            {
                label: 'Projected (Base)',
                data: projBase,
                backgroundColor: 'rgba(234,179,8,0.6)',
                borderRadius: 4,
                order: 3,
            },
            {
                label: 'Budget',
                data: budget,
                type: 'line',
                borderColor: '#ef4444',
                borderWidth: 2,
                borderDash: [6, 3],
                pointRadius: 3,
                pointBackgroundColor: '#ef4444',
                fill: false,
                order: 1,
            },
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { position: 'top', labels: { usePointStyle: true, padding: 20 } },
            tooltip: {
                callbacks: {
                    label: function(ctx) {
                        return ctx.dataset.label + ': $' + (ctx.parsed.y || 0).toLocaleString() + 'K';
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: { callback: v => '$' + v.toLocaleString() + 'K' }
            }
        }
    }
});
</script>

</body>
</html>"""


def render_html(df: pd.DataFrame, output_path: str) -> None:
    is_pse = "ebitda_ytd" in df.columns

    if is_pse:
        forecast = build_forecast(df)
        if forecast:
            _render_risk_dashboard(df, forecast, output_path)
            return

    _render_simple(df, output_path)


def _render_risk_dashboard(df: pd.DataFrame, fc: dict, output_path: str):
    month_names_full = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }

    base = fc["scenarios"]["base"]
    req = fc["scenarios"]["budget_required"]

    # Monthly table data
    monthly = []
    for m in fc["monthly_chart"]:
        is_actual = m.get("is_actual", False)
        budget = m.get("budget", 0)
        if is_actual:
            value = m.get("actual", 0)
        else:
            value = m.get("projected_base", 0)

        capture = value / budget if budget and budget > 0 else None
        capture_class = ""
        if capture is not None:
            if capture >= 0.95:
                capture_class = "positive"
            elif capture >= 0.80:
                capture_class = "warning"
            else:
                capture_class = "negative"

        monthly.append({
            "name": m["name"],
            "shape": f"{m['shape_pct']:.1f}",
            "shape_width": int(m["shape_pct"] * 6),
            "budget_fmt": _fmt(budget),
            "value_fmt": _fmt(value),
            "capture_fmt": f"{capture:.0%}" if capture is not None else "N/A",
            "capture_class": capture_class,
            "is_actual": is_actual,
        })

    # Scenario table
    scenario_order = ["bull", "base", "bear", "budget_required"]
    scenarios_table = []
    for key in scenario_order:
        s = fc["scenarios"][key]
        is_neg = s["shortfall"] < 0 if key != "budget_required" else False
        scenarios_table.append({
            "label": s["label"],
            "capture_fmt": f"{s['capture_ratio']:.1%}",
            "fy_fmt": _fmt(s["projected_fy"]),
            "shortfall_fmt": _fmt(s["shortfall"]) if key != "budget_required" else "--",
            "pct_fmt": _fmt_pct(s["shortfall_pct"]) if key != "budget_required" else "--",
            "class": "negative" if is_neg else "positive" if s["shortfall"] > 0 else "",
        })

    # Chart data
    months_json = json.dumps([m["name"] for m in fc["monthly_chart"]])
    budget_json = json.dumps([m.get("budget", 0) for m in fc["monthly_chart"]])
    actuals_json = json.dumps([
        m.get("actual", 0) if m.get("is_actual") else None
        for m in fc["monthly_chart"]
    ])
    proj_base_json = json.dumps([
        m.get("projected_base", 0) if not m.get("is_actual") else None
        for m in fc["monthly_chart"]
    ])
    proj_bull_json = json.dumps([
        m.get("projected_bull", 0) if not m.get("is_actual") else None
        for m in fc["monthly_chart"]
    ])
    proj_bear_json = json.dumps([
        m.get("projected_bear", 0) if not m.get("is_actual") else None
        for m in fc["monthly_chart"]
    ])

    # FY totals for table footer
    fy_projected = base["projected_fy"]
    fy_capture = fy_projected / fc["fy_budget"] if fc["fy_budget"] else 0

    # EBITDA risk
    er = fc.get("ebitda_risk")

    template = Template(DASHBOARD_HTML)
    html = template.render(
        latest_month_name=month_names_full.get(fc["latest_month"], ""),
        risk=fc["risk"],
        risk_color=fc["risk_color"],
        base_shortfall_fmt=_fmt(base["shortfall"]),
        base_shortfall_pct=_fmt_pct(base["shortfall_pct"]),
        fy_budget_fmt=_fmt(fc["fy_budget"]),
        ytd_actual_fmt=_fmt(fc["latest_ytd_actual"]),
        ytd_attainment_pct=fc["ytd_attainment_pct"],
        avg_capture=fc["avg_capture_ratio"],
        avg_capture_fmt=f"{fc['avg_capture_ratio']:.1%}",
        req_capture=req["capture_ratio"],
        req_capture_fmt=f"{req['capture_ratio']:.1%}",
        mgmt_forecast_fmt=_fmt(fc["fy_forecast_mgmt"]),
        mgmt_forecast_gap=f"{_fmt_pct(round((fc['fy_forecast_mgmt'] - fc['fy_budget']) / fc['fy_budget'] * 100, 1))} vs budget" if fc["fy_forecast_mgmt"] else "N/A",
        ebitda_risk=er,
        ebitda_ytd_fmt=_fmt(er["ytd_actual"]) if er else "",
        ebitda_budget_fmt=_fmt(er["fy_budget"]) if er else "",
        ebitda_forecast_fmt=_fmt(er["fy_forecast"]) if er else "",
        ebitda_budget_fy_fmt=_fmt(er["fy_budget"]) if er else "",
        ebitda_shortfall=er["projected_shortfall"] if er else 0,
        ebitda_shortfall_fmt=_fmt(er["projected_shortfall"]) if er else "",
        ebitda_shortfall_pct=_fmt_pct(er["projected_shortfall_pct"]) if er else "",
        scenarios=scenarios_table,
        monthly=monthly,
        fy_projected_fmt=_fmt(fy_projected),
        fy_capture_fmt=f"{fy_capture:.1%}",
        fy_capture_class="negative" if fy_capture < 0.95 else ("warning" if fy_capture < 1.0 else "positive"),
        months_json=months_json,
        budget_json=budget_json,
        actuals_json=actuals_json,
        proj_base_json=proj_base_json,
        proj_bull_json=proj_bull_json,
        proj_bear_json=proj_bear_json,
    )

    with open(output_path, "w") as f:
        f.write(html)


def _render_simple(df: pd.DataFrame, output_path: str):
    """Fallback for non-PSE simple income statement format."""
    records = []
    for _, row in df.iterrows():
        records.append({
            "company": row.get("company", ""),
            "period": row.get("period", ""),
            "revenue_fmt": _fmt(row.get("revenue")),
            "ebitda_fmt": _fmt(row.get("ebitda")),
            "dscr_fmt": f'{row["dscr"]:.2f}x' if pd.notna(row.get("dscr")) else "N/A",
            "dscr_class": "dscr-green" if pd.notna(row.get("dscr")) and row["dscr"] >= 1.5 else (
                "dscr-yellow" if pd.notna(row.get("dscr")) and row["dscr"] >= 1.2 else "dscr-red"
            ),
        })
    latest = df.sort_values("period").groupby("company").last().reset_index()
    chart_labels = json.dumps(latest["company"].tolist())
    revenue_values = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in latest["revenue"]])
    ebitda_values = json.dumps([round(v, 0) if pd.notna(v) else 0 for v in latest["ebitda"]])

    simple_html = """<!DOCTYPE html>
<html><head><title>KPI Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>body{font-family:sans-serif;padding:2rem;background:#f5f6fa;}table{width:100%;border-collapse:collapse;}th,td{padding:0.5rem;border-bottom:1px solid #eee;text-align:left;}.r{text-align:right;}
.card{background:#fff;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.08);}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;}.chart-container{height:300px;position:relative;}</style></head>
<body><h1>Portfolio KPI Dashboard</h1>
<div class="card"><table><thead><tr><th>Company</th><th>Period</th><th class="r">Revenue</th><th class="r">EBITDA</th><th>DSCR</th></tr></thead>
<tbody>""" + "".join(f'<tr><td>{r["company"]}</td><td>{r["period"]}</td><td class="r">{r["revenue_fmt"]}</td><td class="r">{r["ebitda_fmt"]}</td><td>{r["dscr_fmt"]}</td></tr>' for r in records) + """</tbody></table></div>
<div class="grid"><div class="card"><div class="chart-container"><canvas id="rc"></canvas></div></div><div class="card"><div class="chart-container"><canvas id="ec"></canvas></div></div></div>
<script>
new Chart(document.getElementById('rc'),{type:'bar',data:{labels:""" + chart_labels + """,datasets:[{label:'Revenue',data:""" + revenue_values + """,backgroundColor:'#0984e3',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false}});
new Chart(document.getElementById('ec'),{type:'bar',data:{labels:""" + chart_labels + """,datasets:[{label:'EBITDA',data:""" + ebitda_values + """,backgroundColor:'#00b894',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false}});
</script></body></html>"""

    with open(output_path, "w") as f:
        f.write(simple_html)
