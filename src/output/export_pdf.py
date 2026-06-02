"""
src/output/export_pdf.py
==========================
Executive PDF Report Generator

Produces a timestamped, board-ready PDF from model outputs.
Uses reportlab for PDF generation.

Design rules:
  - Pure function: generate_pdf(report_data) → filepath
  - No financial calculations — receives pre-computed data
  - Timestamped filename: NVIDIA_FPA_Report_YYYYMMDD_HHMMSS.pdf
  - Output saved to outputs/ directory

Sections:
  1. Cover page (company, scenario, date)
  2. Executive KPI summary (key metrics with traffic lights)
  3. Income Statement (5-year projection table)
  4. DCF Valuation summary
  5. Scenario comparison (if multiple scenarios run)
"""

from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs"


def generate_pdf(
    report_data: dict,
    output_dir: str = OUTPUT_DIR,
    filename: Optional[str] = None,
) -> str:
    """
    Generate a board-ready PDF report from model outputs.

    Args:
        report_data: dict containing:
            - income_statement: pd.DataFrame
            - dcf_valuation:    dict
            - kpis:             dict (optional)
            - scenario:         str
            - run_timestamp:    str (optional)
        output_dir:  Directory to save the PDF
        filename:    Optional custom filename (without extension)

    Returns:
        Absolute filepath of generated PDF

    Raises:
        ImportError: If reportlab is not installed
        OSError: If output directory cannot be created
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
            PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        raise ImportError(
            "reportlab is required for PDF export. "
            "Install with: pip install reportlab"
        )

    os.makedirs(output_dir, exist_ok=True)

    # ── Filename ───────────────────────────────────────────────────────────
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    scenario = report_data.get("scenario", "base")
    if filename is None:
        filename = f"NVIDIA_FPA_Report_{scenario.upper()}_{timestamp}"
    filepath = os.path.join(output_dir, f"{filename}.pdf")

    # ── Styles ─────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.HexColor("#1B3A6B"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    style_h1 = ParagraphStyle(
        "CustomH1",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1B3A6B"),
        spaceBefore=16,
        spaceAfter=8,
    )
    style_h2 = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#444444"),
        spaceBefore=12,
        spaceAfter=6,
    )
    style_body = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#444444"),
        spaceAfter=6,
    )
    style_small = ParagraphStyle(
        "CustomSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
    )

    # ── Table styles ───────────────────────────────────────────────────────
    header_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A6B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F5F5F5")],
            ),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )

    # ── Build document elements ────────────────────────────────────────────
    elements = []

    # Cover page
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("NVIDIA Corporation", style_title))
    elements.append(Paragraph("FP&A Performance Dashboard", style_h1))
    elements.append(
        Paragraph(
            f"Scenario: <b>{scenario.upper()}</b>  |  Generated: {timestamp}  |  Currency: USD millions",
            style_body,
        )
    )
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1B3A6B"))
    )
    elements.append(Spacer(1, 0.5 * inch))

    # ── DCF Summary ────────────────────────────────────────────────────────
    dcf = report_data.get("dcf_valuation", {})
    if dcf:
        elements.append(Paragraph("Valuation Summary", style_h1))
        dcf_rows = [
            ["Metric", "Value"],
            ["Implied Share Price", f"${dcf.get('implied_share_price_usd', 0):.2f}"],
            ["Market Price", f"${dcf.get('market_price_usd', 0):.2f}"],
            ["Upside / (Downside)", f"{dcf.get('upside_downside_pct', 0)*100:.1f}%"],
            ["Enterprise Value", f"${dcf.get('enterprise_value_usdm', 0):,.0f}M"],
            ["Equity Value", f"${dcf.get('equity_value_usdm', 0):,.0f}M"],
            ["WACC Used", f"{dcf.get('wacc_used', 0)*100:.2f}%"],
            ["Terminal Growth Rate", f"{dcf.get('terminal_growth_rate', 0)*100:.1f}%"],
        ]
        dcf_table = Table(dcf_rows, colWidths=[3 * inch, 3 * inch])
        dcf_table.setStyle(header_style)
        elements.append(dcf_table)
        elements.append(Spacer(1, 0.3 * inch))

    # ── KPI Summary ────────────────────────────────────────────────────────
    kpis = report_data.get("kpis", {})
    if kpis:
        elements.append(Paragraph("Key Performance Indicators", style_h1))
        kpi_rows = [["KPI", "Value"]]
        kpi_display = [
            ("Gross Margin", "gross_margin", "{:.1%}"),
            ("EBITDA Margin", "ebitda_margin", "{:.1%}"),
            ("FCF Margin", "fcf_margin", "{:.1%}"),
            ("Revenue Growth", "revenue_growth", "{:.1%}"),
            ("AR Days (DSO)", "ar_days", "{:.1f} days"),
            ("AP Days (DPO)", "ap_days", "{:.1f} days"),
            ("Current Ratio", "current_ratio", "{:.2f}x"),
        ]
        for label, key, fmt in kpi_display:
            val = kpis.get(key)
            if val is not None:
                kpi_rows.append([label, fmt.format(val)])
        kpi_table = Table(kpi_rows, colWidths=[3 * inch, 3 * inch])
        kpi_table.setStyle(header_style)
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.3 * inch))

    # ── Income Statement ───────────────────────────────────────────────────
    is_df = report_data.get("income_statement")
    if is_df is not None and not is_df.empty:
        elements.append(PageBreak())
        elements.append(Paragraph("Income Statement (USD millions)", style_h1))

        is_display_cols = [
            "fiscal_year",
            "revenue_usdm",
            "cogs_usdm",
            "gross_profit_usdm",
            "total_opex_usdm",
            "ebit_usdm",
            "ebitda_usdm",
            "net_income_usdm",
            "gross_margin_pct",
            "ebitda_margin_pct",
        ]
        is_display_labels = [
            "FY",
            "Revenue",
            "COGS",
            "Gross Profit",
            "Total OpEx",
            "EBIT",
            "EBITDA",
            "Net Income",
            "Gross Margin",
            "EBITDA Margin",
        ]

        available_cols = [c for c in is_display_cols if c in is_df.columns]
        available_labels = [
            is_display_labels[is_display_cols.index(c)] for c in available_cols
        ]

        def _fmt_is(val, col):
            if val is None:
                return "—"
            if "pct" in col or "margin" in col:
                return f"{val*100:.1f}%"
            return f"{val:,.0f}"

        is_rows = [available_labels]
        for _, row in is_df.iterrows():
            is_rows.append([_fmt_is(row.get(c), c) for c in available_cols])

        col_w = 6.5 / len(available_cols)
        is_table = Table(is_rows, colWidths=[col_w * inch] * len(available_cols))
        is_table.setStyle(header_style)
        elements.append(is_table)

    # ── Footer note ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC"))
    )
    elements.append(
        Paragraph(
            f"Generated by NVIDIA FP&A Platform v1.0 | {timestamp} UTC | "
            f"Confidential — For internal use only",
            style_small,
        )
    )

    # ── Build PDF ──────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(elements)

    logger.info("[export_pdf] PDF generated: %s", filepath)
    return filepath
