"""PDF financial data extraction and standardization.

Handles two formats:
1. PSE-style board reports (multi-column P&L with MTD/YTD/FY, amounts in $000s)
2. Simple income statements (single-column with line item labels)
"""

import os
import re

import pdfplumber

# --- PSE Board Report Extraction ---

PSE_LINE_ITEMS = [
    "revenues", "grants & incentives", "total revenues",
    "opex", "total operations", "internal margin",
    "payroll", "overhead", "total g&a", "total ebitda",
]

PSE_COL_MAP = {
    "mtd_actual": 1,
    "mtd_budget": 2,
    "mtd_variance": 3,
    "ytd_actual": 4,
    "ytd_budget": 5,
    "ytd_variance": 6,
    "fy_forecast": 7,
    "fy_budget": 8,
    "fy_variance": 9,
}


def _parse_number(text: str) -> float | None:
    if not text:
        return None
    text = text.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = re.sub(r"[$€£,]", "", text)
    text = text.rstrip("%").rstrip("*").strip()
    if text in ("", "-", "—", "–", "n/a", "N/A"):
        return None
    try:
        value = float(text)
        return -value if negative else value
    except ValueError:
        return None


def _detect_pse_format(pdf) -> bool:
    """Check if this PDF is a PSE-style board report."""
    for page in pdf.pages[:3]:
        text = (page.extract_text() or "").lower()
        if "monthly business report" in text or "pse monthly report" in text:
            return True
        if "amount ($000s)" in text and "total ebitda" in text:
            return True
    return False


def _find_financial_table(pdf):
    """Find the P&L table in a PSE report."""
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 5:
                continue
            for row in table[:3]:
                if row and row[0] and "amount ($000s)" in str(row[0]).lower():
                    return table
    return None


def _parse_period_from_title(pdf) -> str:
    """Extract the report period from the title page."""
    for page in pdf.pages[:2]:
        text = page.extract_text() or ""
        match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text, re.IGNORECASE)
        if match:
            month_map = {
                "january": "01", "february": "02", "march": "03", "april": "04",
                "may": "05", "june": "06", "july": "07", "august": "08",
                "september": "09", "october": "10", "november": "11", "december": "12",
            }
            month = month_map[match.group(1).lower()]
            year = match.group(2)
            return f"{year}-{month}"
    return "Unknown"


def _extract_pse_report(pdf, pdf_path: str) -> list[dict]:
    """Extract financial data from a PSE-style board report."""
    table = _find_financial_table(pdf)
    if not table:
        return []

    period = _parse_period_from_title(pdf)

    # Find the header row to determine column positions
    header_idx = None
    for i, row in enumerate(table):
        if row and row[0] and "amount ($000s)" in str(row[0]).lower():
            header_idx = i
            break

    if header_idx is None:
        return []

    # Parse each data row
    line_data = {}
    for row in table[header_idx + 1:]:
        if not row or not row[0]:
            continue
        label = str(row[0]).strip().lower().rstrip("*")
        if label in PSE_LINE_ITEMS:
            values = {}
            for col_name, col_idx in PSE_COL_MAP.items():
                if col_idx < len(row):
                    values[col_name] = _parse_number(str(row[col_idx]) if row[col_idx] else "")
            line_data[label] = values

    if not line_data:
        return []

    # Build a record with both MTD and YTD views
    base = {
        "company": "PSE",
        "period": period,
        "source_file": os.path.basename(pdf_path),
        "unit": "$000s",
    }

    record = {**base}
    for line_item in PSE_LINE_ITEMS:
        safe_key = line_item.replace(" & ", "_").replace(" ", "_")
        vals = line_data.get(line_item, {})
        record[f"{safe_key}_mtd_actual"] = vals.get("mtd_actual")
        record[f"{safe_key}_mtd_budget"] = vals.get("mtd_budget")
        record[f"{safe_key}_ytd_actual"] = vals.get("ytd_actual")
        record[f"{safe_key}_ytd_budget"] = vals.get("ytd_budget")
        record[f"{safe_key}_fy_forecast"] = vals.get("fy_forecast")
        record[f"{safe_key}_fy_budget"] = vals.get("fy_budget")

    # Top-level KPI fields for easy access
    rev = line_data.get("revenues", {})
    ebitda = line_data.get("total ebitda", {})
    total_rev = line_data.get("total revenues", {})
    opex = line_data.get("opex", {})
    ga = line_data.get("total g&a", {})

    record["revenue"] = rev.get("mtd_actual")
    record["revenue_budget"] = rev.get("mtd_budget")
    record["total_revenue"] = total_rev.get("mtd_actual")
    record["total_revenue_budget"] = total_rev.get("mtd_budget")
    record["opex"] = opex.get("mtd_actual")
    record["opex_budget"] = opex.get("mtd_budget")
    record["total_ga"] = ga.get("mtd_actual")
    record["total_ga_budget"] = ga.get("mtd_budget")
    record["ebitda"] = ebitda.get("mtd_actual")
    record["ebitda_budget"] = ebitda.get("mtd_budget")

    record["revenue_ytd"] = rev.get("ytd_actual")
    record["revenue_ytd_budget"] = rev.get("ytd_budget")
    record["total_revenue_ytd"] = total_rev.get("ytd_actual")
    record["total_revenue_ytd_budget"] = total_rev.get("ytd_budget")
    record["opex_ytd"] = opex.get("ytd_actual")
    record["opex_ytd_budget"] = opex.get("ytd_budget")
    record["total_ga_ytd"] = ga.get("ytd_actual")
    record["total_ga_ytd_budget"] = ga.get("ytd_budget")
    record["ebitda_ytd"] = ebitda.get("ytd_actual")
    record["ebitda_ytd_budget"] = ebitda.get("ytd_budget")

    record["revenue_fy_forecast"] = rev.get("fy_forecast")
    record["revenue_fy_budget"] = rev.get("fy_budget")
    record["ebitda_fy_forecast"] = ebitda.get("fy_forecast")
    record["ebitda_fy_budget"] = ebitda.get("fy_budget")

    return [record]


# --- Simple Income Statement Extraction (original format) ---

LABEL_MAP = {
    "revenue": ["revenue", "net revenue", "total revenue", "net sales", "total sales", "sales"],
    "cogs": ["cost of goods sold", "cogs", "cost of sales", "cost of revenue"],
    "gross_profit": ["gross profit", "gross margin"],
    "opex": ["operating expenses", "total operating expenses", "sg&a", "selling general and administrative"],
    "depreciation_amortization": ["depreciation", "amortization", "d&a", "depreciation and amortization"],
    "ebit": ["operating income", "ebit", "income from operations", "operating profit"],
    "interest_expense": ["interest expense", "interest cost", "finance cost", "finance costs"],
    "tax_expense": ["income tax", "tax expense", "provision for income tax", "income tax expense"],
    "net_income": ["net income", "net profit", "net earnings", "profit after tax"],
    "ebitda": ["ebitda"],
    "total_debt_service": ["debt service", "total debt service"],
}


def _match_label(text: str) -> str | None:
    if not text:
        return None
    normalized = re.sub(r"^[\d\.\-\•\s]+", "", text.strip().lower()).strip()
    for field, synonyms in LABEL_MAP.items():
        for synonym in synonyms:
            if synonym in normalized:
                return field
    return None


def _parse_company_period(filename: str) -> tuple[str, str]:
    base = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^(.+?)[\s_]+(\d{4}[\s_\-]?Q?\d{1,2})$", base, re.IGNORECASE)
    if match:
        company = match.group(1).replace("_", " ").strip()
        period = match.group(2).replace(" ", "").replace("_", "")
        return company, period
    return base.replace("_", " ").strip(), "Unknown"


def _extract_simple_report(pdf, pdf_path: str) -> list[dict]:
    """Extract from a simple income statement format."""
    data = {}

    # Try tables first
    for page in pdf.pages:
        for table in (page.extract_tables() or []):
            if not table:
                continue
            for row in table:
                if not row or not row[0]:
                    continue
                field = _match_label(str(row[0]))
                if field and field not in data:
                    for cell in reversed(row[1:]):
                        value = _parse_number(str(cell) if cell else "")
                        if value is not None:
                            data[field] = value
                            break

    # Fallback to text
    if not data:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                field = _match_label(line)
                if field and field not in data:
                    numbers = re.findall(r"[\$]?[\(]?[\d,]+\.?\d*[\)]?", line)
                    for num_str in reversed(numbers):
                        value = _parse_number(num_str)
                        if value is not None:
                            data[field] = value
                            break

    if not data:
        return []

    company, period = _parse_company_period(pdf_path)
    record = {"company": company, "period": period, "source_file": os.path.basename(pdf_path), "unit": "$"}
    for field in LABEL_MAP:
        record[field] = data.get(field)
    return [record]


# --- Public API ---

def extract_financials(pdf_path: str) -> list[dict]:
    """Extract standardized financial data from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        if _detect_pse_format(pdf):
            return _extract_pse_report(pdf, pdf_path)
        return _extract_simple_report(pdf, pdf_path)
