import io
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

from app.models.project import Project
from app.logger import get_logger

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# WHY ReportLab?
#
# ReportLab builds PDFs programmatically — you place elements at coordinates
# or use their "platypus" (Page Layout and Typography Using Scripts) system
# which flows content like a word processor.
#
# We use Platypus here: SimpleDocTemplate manages pages, Paragraph handles
# text, Table handles grids, Spacer adds whitespace. All elements go into
# a list called `story` and ReportLab renders them top to bottom.
# -----------------------------------------------------------------------------

# Brand colours — keeping it clean and professional
DARK = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#4f8ef7")
LIGHT_GREY = colors.HexColor("#f5f6fa")
MID_GREY = colors.HexColor("#888888")
WHITE = colors.white


def generate_invoice_pdf(project: Project, owner_name: str) -> bytes:
    """
    Generate a PDF invoice for a project and return it as bytes.

    Returns bytes so the caller can stream it directly in the HTTP response
    without writing to disk. io.BytesIO is an in-memory file — ReportLab
    writes to it exactly like a real file, but it lives in RAM only.

    Args:
        project: The Project ORM object with time_logs already loaded
                 (they load via selectin automatically)
        owner_name: The freelancer's full name for the invoice header
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # -------------------------------------------------------------------------
    # STYLES
    # -------------------------------------------------------------------------
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontSize=28,
        textColor=DARK,
        fontName="Helvetica-Bold",
        spaceAfter=0,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=MID_GREY,
        fontName="Helvetica",
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Normal"],
        fontSize=13,
        textColor=DARK,
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=3,
    )
    normal_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        leading=16,
    )
    small_grey = ParagraphStyle(
        "SmallGrey",
        parent=styles["Normal"],
        fontSize=9,
        textColor=MID_GREY,
        fontName="Helvetica",
    )
    right_style = ParagraphStyle(
        "Right",
        parent=styles["Normal"],
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        alignment=TA_RIGHT,
    )
    total_style = ParagraphStyle(
        "Total",
        parent=styles["Normal"],
        fontSize=13,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_RIGHT,
    )

    # -------------------------------------------------------------------------
    # HEADER — Invoice title + meta on the right
    # -------------------------------------------------------------------------
    invoice_number = f"INV-{str(project.id)[:8].upper()}"
    issue_date = date.today().strftime("%d %b %Y")

    header_data = [
        [
            Paragraph("INVOICE", title_style),
            Paragraph(
                f"<b>{invoice_number}</b><br/>"
                f"<font color='#888888'>Issued: {issue_date}</font>",
                right_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=["60%", "40%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=10))

    # -------------------------------------------------------------------------
    # FROM / TO — Two column layout
    # -------------------------------------------------------------------------
    client_display = project.client_name or "Client not specified"
    from_to_data = [
        [
            Paragraph("<b>FROM</b>", small_grey),
            Paragraph("<b>TO</b>", small_grey),
        ],
        [
            Paragraph(owner_name, heading_style),
            Paragraph(client_display, heading_style),
        ],
        [
            Paragraph("Freelancer", normal_style),
            Paragraph("", normal_style),
        ],
    ]
    from_to_table = Table(from_to_data, colWidths=["50%", "50%"])
    from_to_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(from_to_table)
    story.append(Spacer(1, 10 * mm))

    # -------------------------------------------------------------------------
    # PROJECT SUMMARY BOX
    # -------------------------------------------------------------------------
    story.append(Paragraph("Project Summary", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY, spaceAfter=6))

    summary_data = [
        ["Project", project.name],
        ["Status", project.status.value.replace("_", " ").title()],
        ["Hourly Rate", f"₹{float(project.hourly_rate):,.2f}"],
        ["Total Hours Logged", f"{project.total_hours:.2f} hrs"],
    ]
    if project.description:
        summary_data.insert(1, ["Description", project.description])

    summary_table = Table(summary_data, colWidths=["35%", "65%"])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))

    # -------------------------------------------------------------------------
    # TIME LOG TABLE — line items
    # -------------------------------------------------------------------------
    story.append(Paragraph("Time Log", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY, spaceAfter=6))

    if project.time_logs:
        log_rows = [
            [
                Paragraph("<b>Date</b>", normal_style),
                Paragraph("<b>Description</b>", normal_style),
                Paragraph("<b>Hours</b>", normal_style),
                Paragraph("<b>Amount (₹)</b>", right_style),
            ]
        ]
        for log in sorted(project.time_logs, key=lambda x: x.work_date):
            amount = float(log.hours) * float(project.hourly_rate)
            log_rows.append([
                Paragraph(log.work_date.strftime("%d %b %Y"), normal_style),
                Paragraph(log.description or "—", normal_style),
                Paragraph(f"{float(log.hours):.2f}", normal_style),
                Paragraph(f"₹{amount:,.2f}", right_style),
            ])

        log_table = Table(log_rows, colWidths=["20%", "45%", "15%", "20%"])
        log_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("No time entries logged yet.", small_grey))

    story.append(Spacer(1, 8 * mm))

    # -------------------------------------------------------------------------
    # TOTAL BOX — right aligned, prominent
    # -------------------------------------------------------------------------
    total_data = [
        [
            "",
            Paragraph(
                f"<b>TOTAL DUE</b>",
                ParagraphStyle(
                    "TotalLabel",
                    parent=styles["Normal"],
                    fontSize=13,
                    textColor=WHITE,
                    fontName="Helvetica-Bold",
                ),
            ),
            Paragraph(
                f"₹{project.total_earned:,.2f}",
                ParagraphStyle(
                    "TotalAmount",
                    parent=styles["Normal"],
                    fontSize=16,
                    textColor=WHITE,
                    fontName="Helvetica-Bold",
                    alignment=TA_RIGHT,
                ),
            ),
        ]
    ]
    total_table = Table(total_data, colWidths=["50%", "25%", "25%"])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (-1, 0), ACCENT),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(total_table)

    # -------------------------------------------------------------------------
    # FOOTER
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"Generated by FreelanceTrack • {date.today().strftime('%d %b %Y')}",
        small_grey,
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info("Invoice PDF generated for project: %s (%s)", project.name, invoice_number)
    return pdf_bytes