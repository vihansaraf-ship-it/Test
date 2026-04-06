#!/usr/bin/env python3
"""PE Portfolio KPI Tracker - Ingest PDF reports, calculate KPIs, output dashboard + Excel."""

import argparse
import glob
import os
import sys

import pandas as pd

from extractor import extract_financials
from kpi import calculate_kpis
from dashboard import render_html
from excel_output import write_excel


def main():
    parser = argparse.ArgumentParser(description="PE Portfolio KPI Tracker")
    parser.add_argument("--input-dir", required=True, help="Directory containing portfolio company PDF reports")
    parser.add_argument("--output-dir", default="./output", help="Output directory (default: ./output)")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)

    pdf_files = sorted(glob.glob(os.path.join(args.input_dir, "*.pdf")))
    if not pdf_files:
        print(f"No PDF files found in '{args.input_dir}'.")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF file(s). Processing...")

    # Extract financials from each PDF
    all_records = []
    for pdf_path in pdf_files:
        print(f"  Extracting: {os.path.basename(pdf_path)}")
        records = extract_financials(pdf_path)
        all_records.extend(records)

    if not all_records:
        print("No financial data could be extracted from the PDFs.")
        sys.exit(1)

    df = pd.DataFrame(all_records)
    print(f"  Extracted {len(df)} record(s) from {len(pdf_files)} file(s).")

    # Calculate KPIs
    df = calculate_kpis(df)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate outputs
    html_path = os.path.join(args.output_dir, "dashboard.html")
    render_html(df, html_path)
    print(f"  Dashboard: {html_path}")

    excel_path = os.path.join(args.output_dir, "report.xlsx")
    write_excel(df, excel_path)
    print(f"  Excel:     {excel_path}")

    # Print summary
    print("\n--- KPI Summary ---")
    summary_cols = ["company", "period", "revenue", "ebitda", "dscr"]
    existing_cols = [c for c in summary_cols if c in df.columns]
    print(df[existing_cols].to_string(index=False))
    print("\nDone.")


if __name__ == "__main__":
    main()
