"""
Publication-Grade PDF Audit Certificate Generator for Debt Detox using ReportLab.
Dynamically extracts values from ACTIVE_LOAN with zero hardcoded numbers.
"""

import io
from typing import Dict, Any, List
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

def generate_pdf_audit_report(active_loan: Dict[str, Any]) -> bytes:
    """
    Generates a PDF Audit Certificate from active_loan data and returns raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom color palette matching Debt Detox theme
    PRIMARY = colors.HexColor("#0F1E33")
    SECONDARY = colors.HexColor("#38BDF8")
    ACCENT_GREEN = colors.HexColor("#10B981")
    ACCENT_RED = colors.HexColor("#EF4444")
    TEXT_DARK = colors.HexColor("#1E293B")
    TEXT_MUTED = colors.HexColor("#64748B")
    BG_LIGHT = colors.HexColor("#F8FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Typography styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED
    )
    style_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=6
    )
    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK
    )
    style_body_bold = ParagraphStyle(
        'BodyDarkBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK
    )
    style_badge_green = ParagraphStyle(
        'BadgeGreen',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=ACCENT_GREEN,
        alignment=2 # Right
    )

    story = []

    # Extract dynamic data
    doc_name = active_loan.get("doc_name", "Loan Agreement")
    doc_type = active_loan.get("doc_type", "pdf").upper()
    total_pages = active_loan.get("total_pages", 1)
    audit_status = active_loan.get("audit_status", "VERIFIED")
    metrics = active_loan.get("metrics", {})
    charges = active_loan.get("charges", [])
    alerts = active_loan.get("compliance_alerts", [])
    transparency = active_loan.get("transparency", {})
    score = transparency.get("score", 100)

    principal = metrics.get("loan_amount", 0.0)
    stated_rate = metrics.get("interest_rate_annual", 0.0)
    real_apr = metrics.get("real_apr", 0.0)
    tenure = metrics.get("tenure_months", 0)
    emi = metrics.get("emi", 0.0)
    upfront_fees = metrics.get("upfront_fees", 0.0)
    net_disbursed = metrics.get("net_disbursed_amount", 0.0)
    total_scheduled = metrics.get("total_scheduled_cost", 0.0)
    total_interest = metrics.get("total_interest", 0.0)

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>DEBT DETOX</b> — Financial Audit Certificate", style_title),
            Paragraph(f"<b>STATUS: {audit_status}</b>", style_badge_green)
        ],
        [
            Paragraph(f"Document: <b>{doc_name}</b> ({doc_type}, {total_pages} Pages) &nbsp;|&nbsp; Audit Date: {datetime.now().strftime('%Y-%m-%d')}", style_subtitle),
            Paragraph(f"Verification Ref: DEBT-{hash(doc_name) & 0xFFFFFF:06X}", ParagraphStyle('RightSub', parent=style_subtitle, alignment=2))
        ]
    ]
    header_table = Table(header_data, colWidths=[370, 170])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SECONDARY, spaceBefore=0, spaceAfter=12))

    # 2. Executive Summary / Truth vs Marketing Delta Table
    story.append(Paragraph("1. Executive Cost Audit (Truth vs. Marketing)", style_heading))

    apr_markup = real_apr - stated_rate
    delta_data = [
        [Paragraph("<b>Metric</b>", style_body_bold), Paragraph("<b>Stated Terms (Bank)</b>", style_body_bold), Paragraph("<b>Audit Findings (Real Cost)</b>", style_body_bold), Paragraph("<b>Impact / Markup Delta</b>", style_body_bold)],
        [Paragraph("Interest Rate", style_body), Paragraph(f"{stated_rate:.2f}% p.a.", style_body), Paragraph(f"<b>{real_apr:.2f}% Effective APR</b>", style_body), Paragraph(f"<font color='#EF4444'><b>+{apr_markup:.2f}% Hidden Markup</b></font>", style_body)],
        [Paragraph("Disbursement Cash", style_body), Paragraph(f"₹{principal:,.2f} Principal", style_body), Paragraph(f"<b>₹{net_disbursed:,.2f} Cash In Hand</b>", style_body), Paragraph(f"<font color='#EF4444'><b>-₹{upfront_fees:,.2f} Deducted Upfront</b></font>", style_body)],
        [Paragraph("Total Debt Service", style_body), Paragraph(f"₹{principal:,.2f}", style_body), Paragraph(f"<b>₹{total_scheduled:,.2f} Total Repayment</b>", style_body), Paragraph(f"₹{total_interest:,.2f} Total Interest ({tenure} Mths)", style_body)],
        [Paragraph("Transparency Score", style_body), Paragraph("100/100 Benchmark", style_body), Paragraph(f"<b>{score:.0f} / 100 Score</b>", style_body), Paragraph(f"{transparency.get('rating', 'AUDITED')}", style_body)]
    ]

    delta_table = Table(delta_data, colWidths=[120, 140, 140, 140])
    delta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(delta_table)
    story.append(Spacer(1, 14))

    # 3. Itemized Charges Audit Table
    story.append(Paragraph("2. Itemized Fee & Clause Audit", style_heading))
    if charges:
        charge_headers = [Paragraph("<b>Charge Name</b>", style_body_bold), Paragraph("<b>Basis</b>", style_body_bold), Paragraph("<b>Value</b>", style_body_bold), Paragraph("<b>Pg #</b>", style_body_bold), Paragraph("<b>Evidence Snippet</b>", style_body_bold)]
        charge_rows = [charge_headers]
        for c in charges:
            c_name = c.get("canonical_name", "").replace("_", " ").title()
            basis = c.get("basis", "").replace("_", " ").title()
            val = c.get("value")
            unit = c.get("unit", "")
            val_str = f"₹{val:,.2f}" if isinstance(val, (int, float)) and unit != "percent" else f"{val}%"
            page = str(c.get("page", 1))
            evidence = c.get("evidence", "")
            if len(evidence) > 90:
                evidence = evidence[:87] + "..."

            charge_rows.append([
                Paragraph(c_name, style_body),
                Paragraph(basis, style_body),
                Paragraph(f"<b>{val_str}</b>", style_body),
                Paragraph(page, style_body),
                Paragraph(f"<i>\"{evidence}\"</i>", style_body)
            ])

        charge_table = Table(charge_rows, colWidths=[110, 80, 75, 35, 240])
        charge_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(charge_table)
    else:
        story.append(Paragraph("No additional mandatory or conditional fees detected in the contract.", style_body))

    story.append(Spacer(1, 14))

    # 4. Regulatory Compliance & Usury Alerts
    story.append(Paragraph("3. Regulatory & Consumer Protection Audit", style_heading))
    if alerts:
        alert_rows = [[Paragraph("<b>Severity</b>", style_body_bold), Paragraph("<b>Compliance Concern</b>", style_body_bold), Paragraph("<b>Impact & Reference Standard</b>", style_body_bold)]]
        for alert in alerts:
            sev = alert.get("severity", "WARNING")
            color_hex = "#EF4444" if sev == "CRITICAL" else "#F59E0B"
            alert_rows.append([
                Paragraph(f"<font color='{color_hex}'><b>{sev}</b></font>", style_body),
                Paragraph(f"<b>{alert.get('title')}</b><br/>{alert.get('description')}", style_body),
                Paragraph(f"{alert.get('impact')}<br/><i>Ref: {alert.get('law_reference')}</i>", style_body)
            ])
        alert_table = Table(alert_rows, colWidths=[70, 230, 240])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(alert_table)
    else:
        story.append(Paragraph("✓ No regulatory violations or high-risk usury thresholds triggered.", style_body))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph("<i>This report was generated automatically by Debt Detox Financial Intelligence Engine. All math calculations are deterministic.</i>", ParagraphStyle('FooterText', parent=style_subtitle, fontSize=8, alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
