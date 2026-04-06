"""Excel report generation with formatted sheets."""

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, numbers
from openpyxl.utils import get_column_letter


# Conditional fills for DSCR
FILL_GREEN = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
FILL_YELLOW = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
FILL_RED = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
HEADER_FONT = Font(bold=True)
HEADER_FILL = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")


def _auto_width(ws):
    """Auto-fit column widths based on content."""
    for col_idx, col_cells in enumerate(ws.columns, 1):
        max_len = 0
        for cell in col_cells:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 3, 30)


def _style_headers(ws):
    """Bold and shade the header row."""
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")


def _apply_dscr_formatting(ws, dscr_col_idx):
    """Color DSCR cells based on value thresholds."""
    for row in ws.iter_rows(min_row=2, min_col=dscr_col_idx, max_col=dscr_col_idx):
        cell = row[0]
        if cell.value is None:
            continue
        try:
            val = float(cell.value)
        except (ValueError, TypeError):
            continue
        if val >= 1.5:
            cell.fill = FILL_GREEN
        elif val >= 1.2:
            cell.fill = FILL_YELLOW
        else:
            cell.fill = FILL_RED


def write_excel(df: pd.DataFrame, output_path: str) -> None:
    """Write the KPI data to a formatted Excel workbook."""
    # Prepare summary: latest period per company
    summary_df = df.sort_values("period").groupby("company").last().reset_index()
    summary_cols = ["company", "period", "revenue", "ebitda", "dscr"]
    summary_cols = [c for c in summary_cols if c in summary_df.columns]
    summary_df = summary_df[summary_cols]

    # Prepare detail: all records
    detail_cols = [
        "company", "period", "source_file", "revenue", "cogs", "gross_profit",
        "opex", "depreciation_amortization", "ebit", "interest_expense",
        "tax_expense", "net_income", "ebitda", "total_debt_service", "dscr",
    ]
    detail_cols = [c for c in detail_cols if c in df.columns]
    detail_df = df[detail_cols]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Sheet 1: Summary
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        ws_summary = writer.sheets["Summary"]
        _style_headers(ws_summary)

        # Format currency columns
        for row in ws_summary.iter_rows(min_row=2):
            for cell in row:
                col_header = ws_summary.cell(row=1, column=cell.column).value
                if col_header in ("revenue", "ebitda") and cell.value is not None:
                    cell.number_format = '#,##0'
                elif col_header == "dscr" and cell.value is not None:
                    cell.number_format = '0.00"x"'

        # DSCR conditional formatting
        if "dscr" in summary_cols:
            dscr_idx = summary_cols.index("dscr") + 1
            _apply_dscr_formatting(ws_summary, dscr_idx)

        _auto_width(ws_summary)

        # Sheet 2: Detail
        detail_df.to_excel(writer, sheet_name="Detail", index=False)
        ws_detail = writer.sheets["Detail"]
        _style_headers(ws_detail)

        # Format numeric columns in detail
        currency_cols = {
            "revenue", "cogs", "gross_profit", "opex",
            "depreciation_amortization", "ebit", "interest_expense",
            "tax_expense", "net_income", "ebitda", "total_debt_service",
        }
        for row in ws_detail.iter_rows(min_row=2):
            for cell in row:
                col_header = ws_detail.cell(row=1, column=cell.column).value
                if col_header in currency_cols and cell.value is not None:
                    cell.number_format = '#,##0'
                elif col_header == "dscr" and cell.value is not None:
                    cell.number_format = '0.00"x"'

        if "dscr" in detail_cols:
            dscr_idx = detail_cols.index("dscr") + 1
            _apply_dscr_formatting(ws_detail, dscr_idx)

        _auto_width(ws_detail)
