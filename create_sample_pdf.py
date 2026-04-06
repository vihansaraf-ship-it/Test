#!/usr/bin/env python3
"""Generate sample portfolio company PDF reports for testing."""

import os

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import pdfplumber
    from io import BytesIO
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def create_with_reportlab(output_dir: str):
    """Create sample PDFs using reportlab."""
    os.makedirs(output_dir, exist_ok=True)
    styles = getSampleStyleSheet()

    companies = [
        {
            "filename": "AcmeCorp_2025Q4.pdf",
            "title": "Acme Corporation - Q4 2025 Financial Report",
            "data": [
                ["Line Item", "Amount ($)"],
                ["Revenue", "12,500,000"],
                ["Cost of Goods Sold", "7,500,000"],
                ["Gross Profit", "5,000,000"],
                ["Operating Expenses", "2,200,000"],
                ["Depreciation and Amortization", "800,000"],
                ["Operating Income", "2,000,000"],
                ["Interest Expense", "450,000"],
                ["Income Tax Expense", "387,500"],
                ["Net Income", "1,162,500"],
                ["Total Debt Service", "1,200,000"],
            ],
        },
        {
            "filename": "BetaTech_2025Q4.pdf",
            "title": "Beta Technologies - Q4 2025 Financial Report",
            "data": [
                ["Line Item", "Amount ($)"],
                ["Net Sales", "8,200,000"],
                ["Cost of Revenue", "3,600,000"],
                ["Gross Profit", "4,600,000"],
                ["SG&A", "1,800,000"],
                ["D&A", "500,000"],
                ["EBIT", "2,300,000"],
                ["Interest Expense", "320,000"],
                ["Income Tax", "495,000"],
                ["Net Profit", "1,485,000"],
                ["Debt Service", "900,000"],
            ],
        },
        {
            "filename": "GammaHealth_2025Q4.pdf",
            "title": "Gamma Healthcare - Q4 2025 Financial Report",
            "data": [
                ["Line Item", "Amount ($)"],
                ["Total Revenue", "20,100,000"],
                ["Cost of Sales", "12,800,000"],
                ["Gross Margin", "7,300,000"],
                ["Total Operating Expenses", "4,500,000"],
                ["Depreciation", "1,200,000"],
                ["Income from Operations", "1,600,000"],
                ["Finance Costs", "800,000"],
                ["Provision for Income Tax", "200,000"],
                ["Net Earnings", "600,000"],
                ["Total Debt Service", "2,500,000"],
            ],
        },
    ]

    for co in companies:
        path = os.path.join(output_dir, co["filename"])
        doc = SimpleDocTemplate(path, pagesize=letter)
        elements = []

        elements.append(Paragraph(co["title"], styles["Title"]))
        elements.append(Spacer(1, 20))

        table = Table(co["data"], colWidths=[280, 150])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3436")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        doc.build(elements)
        print(f"  Created: {path}")


def create_simple_text_pdf(output_dir: str):
    """Create minimal text-based PDFs without reportlab (using pdfplumber-compatible format).

    This is a fallback that creates the simplest possible valid PDF files.
    """
    os.makedirs(output_dir, exist_ok=True)

    companies = [
        {
            "filename": "AcmeCorp_2025Q4.pdf",
            "lines": [
                "Acme Corporation - Q4 2025 Financial Report",
                "",
                "Revenue                         12,500,000",
                "Cost of Goods Sold               7,500,000",
                "Gross Profit                     5,000,000",
                "Operating Expenses               2,200,000",
                "Depreciation and Amortization      800,000",
                "Operating Income                 2,000,000",
                "Interest Expense                   450,000",
                "Income Tax Expense                 387,500",
                "Net Income                       1,162,500",
                "Total Debt Service               1,200,000",
            ],
        },
        {
            "filename": "BetaTech_2025Q4.pdf",
            "lines": [
                "Beta Technologies - Q4 2025 Financial Report",
                "",
                "Net Sales                        8,200,000",
                "Cost of Revenue                  3,600,000",
                "Gross Profit                     4,600,000",
                "SG&A                             1,800,000",
                "D&A                                500,000",
                "EBIT                             2,300,000",
                "Interest Expense                   320,000",
                "Income Tax                         495,000",
                "Net Profit                       1,485,000",
                "Debt Service                       900,000",
            ],
        },
        {
            "filename": "GammaHealth_2025Q4.pdf",
            "lines": [
                "Gamma Healthcare - Q4 2025 Financial Report",
                "",
                "Total Revenue                   20,100,000",
                "Cost of Sales                   12,800,000",
                "Gross Margin                     7,300,000",
                "Total Operating Expenses         4,500,000",
                "Depreciation                     1,200,000",
                "Income from Operations           1,600,000",
                "Finance Costs                      800,000",
                "Provision for Income Tax           200,000",
                "Net Earnings                       600,000",
                "Total Debt Service               2,500,000",
            ],
        },
    ]

    for co in companies:
        path = os.path.join(output_dir, co["filename"])
        _write_minimal_pdf(path, co["lines"])
        print(f"  Created: {path}")


def _write_minimal_pdf(path: str, lines: list[str]):
    """Write a minimal valid PDF with text content."""
    text_lines = "\n".join(lines)

    # Build a minimal PDF manually
    stream_content = f"BT\n/F1 10 Tf\n1 0 0 1 50 750 Tm\n12 TL\n"
    for line in lines:
        # Escape special PDF chars
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({escaped}) '\n"
    stream_content += "ET"
    stream_bytes = stream_content.encode("latin-1")

    objects = []

    # Object 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    # Object 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
    # Object 3: Page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj"
    )
    # Object 4: Stream
    stream_obj = (
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream\nendobj"
    )
    objects.append(stream_obj)
    # Object 5: Font
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj"
    )

    # Build PDF
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"

    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()

    pdf += b"trailer\n"
    pdf += f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_offset}\n".encode()
    pdf += b"%%EOF\n"

    with open(path, "wb") as f:
        f.write(pdf)


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    print("Creating sample PDF reports...")
    if HAS_REPORTLAB:
        print("  Using reportlab for formatted PDFs.")
        create_with_reportlab(output_dir)
    else:
        print("  reportlab not available, creating minimal text PDFs.")
        create_simple_text_pdf(output_dir)
    print("Done.")
