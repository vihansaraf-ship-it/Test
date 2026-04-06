"""PDF financial data extraction and standardization."""

import os
import re

import pdfplumber

# Map standardized field names to common label variations found in financial statements
LABEL_MAP = {
    "revenue": ["revenue", "net revenue", "total revenue", "net sales", "total sales", "sales"],
    "cogs": ["cost of goods sold", "cogs", "cost of sales", "cost of revenue"],
    "gross_profit": ["gross profit", "gross margin"],
    "opex": [
        "operating expenses", "total operating expenses", "sg&a",
        "selling general and administrative", "selling general & administrative",
    ],
    "depreciation_amortization": [
        "depreciation", "amortization", "d&a",
        "depreciation and amortization", "depreciation & amortization",
    ],
    "ebit": ["operating income", "ebit", "income from operations", "operating profit"],
    "interest_expense": ["interest expense", "interest cost", "finance cost", "finance costs"],
    "tax_expense": ["income tax", "tax expense", "provision for income tax", "income tax expense"],
    "net_income": ["net income", "net profit", "net earnings", "profit after tax", "net profit after tax"],
    "ebitda": ["ebitda"],
    "total_debt_service": ["debt service", "total debt service"],
}


def _parse_number(text: str) -> float | None:
    """Parse a numeric string, handling $, commas, parentheses for negatives."""
    if not text:
        return None
    text = text.strip()
    # Check for parentheses (negative)
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    # Remove currency symbols and commas
    text = re.sub(r"[$€£,]", "", text)
    # Remove trailing % if present
    text = text.rstrip("%").strip()
    # Handle dash or empty as None
    if text in ("", "-", "—", "–", "n/a", "N/A"):
        return None
    try:
        value = float(text)
        return -value if negative else value
    except ValueError:
        return None


def _match_label(text: str) -> str | None:
    """Match a row label to a standardized field name."""
    if not text:
        return None
    normalized = text.strip().lower()
    # Remove leading bullet points, numbers, etc.
    normalized = re.sub(r"^[\d\.\-\•\s]+", "", normalized).strip()
    for field, synonyms in LABEL_MAP.items():
        for synonym in synonyms:
            if synonym in normalized:
                return field
    return None


def _parse_company_period(filename: str) -> tuple[str, str]:
    """Extract company name and period from filename.

    Expected formats:
        CompanyName_2025Q4.pdf
        Company Name_2025-12.pdf
        CompanyName_2025_Q4.pdf
    Falls back to filename as company name and 'Unknown' as period.
    """
    base = os.path.splitext(os.path.basename(filename))[0]

    # Try pattern: Name_YearQN or Name_Year-MM or Name_Year_QN
    match = re.match(r"^(.+?)[\s_]+(\d{4}[\s_\-]?Q?\d{1,2})$", base, re.IGNORECASE)
    if match:
        company = match.group(1).replace("_", " ").strip()
        period = match.group(2).replace(" ", "").replace("_", "")
        return company, period

    return base.replace("_", " ").strip(), "Unknown"


def _extract_from_tables(pdf) -> dict[str, float | None]:
    """Extract financial data from PDF tables."""
    data = {}
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row or not row[0]:
                    continue
                field = _match_label(str(row[0]))
                if field and field not in data:
                    # Take the last non-empty numeric cell in the row
                    for cell in reversed(row[1:]):
                        value = _parse_number(str(cell) if cell else "")
                        if value is not None:
                            data[field] = value
                            break
    return data


def _extract_from_text(pdf) -> dict[str, float | None]:
    """Fallback: extract financial data from raw text using line-by-line matching."""
    data = {}
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split("\n"):
            field = _match_label(line)
            if field and field not in data:
                # Find all numbers in the line, take the last one
                numbers = re.findall(r"[\$]?[\(]?[\d,]+\.?\d*[\)]?", line)
                for num_str in reversed(numbers):
                    value = _parse_number(num_str)
                    if value is not None:
                        data[field] = value
                        break
    return data


def extract_financials(pdf_path: str) -> list[dict]:
    """Extract standardized financial data from a PDF file.

    Returns a list of dicts (one per period found). Each dict contains
    the standardized field names and their numeric values.
    """
    company, period = _parse_company_period(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        # Try table extraction first
        data = _extract_from_tables(pdf)
        # Fall back to text extraction if tables yielded nothing
        if not data:
            data = _extract_from_text(pdf)

    if not data:
        return []

    # Build the standardized record
    record = {
        "company": company,
        "period": period,
        "source_file": os.path.basename(pdf_path),
    }
    # Fill all fields, defaulting to None
    for field in LABEL_MAP:
        record[field] = data.get(field)

    return [record]
