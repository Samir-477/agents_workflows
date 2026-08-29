from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from seo_audit.models import AuditReport


INK = colors.HexColor("#171820")
MUTED = colors.HexColor("#686871")
INDIGO = colors.HexColor("#5549DD")
ORANGE = colors.HexColor("#FF5738")
LINE = colors.HexColor("#E2E0DC")
PAPER = colors.HexColor("#F8F7F4")


def build_report_pdf(report: AuditReport) -> bytes:
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Stellar SEO Audit Report",
        author="Stellar",
    )
    styles = _styles()
    story: list[object] = []

    story.append(Paragraph("STELLAR / SEO AUDIT", styles["eyebrow"]))
    story.append(Paragraph("Search health report", styles["title"]))
    story.append(Paragraph(_escape(report.requested_url), styles["url"]))
    story.append(Spacer(1, 8 * mm))

    score = "-" if report.site_score is None else str(report.site_score)
    counts = report.severity_counts
    overview = Table(
        [
            [
                Paragraph(f"<b>{score}</b><br/><font size='8'>SITE SCORE / 100</font>", styles["score"]),
                Paragraph(f"<b>{report.pages_crawled}</b><br/><font size='8'>PAGES</font>", styles["metric"]),
                Paragraph(f"<b>{counts.get('critical', 0)}</b><br/><font size='8'>CRITICAL</font>", styles["metric"]),
                Paragraph(f"<b>{counts.get('important', 0)}</b><br/><font size='8'>IMPORTANT</font>", styles["metric"]),
                Paragraph(f"<b>{counts.get('minor', 0)}</b><br/><font size='8'>MINOR</font>", styles["metric"]),
            ]
        ],
        colWidths=[35 * mm, 31 * mm, 31 * mm, 31 * mm, 31 * mm],
        rowHeights=[24 * mm],
    )
    overview.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), INK),
        ("BACKGROUND", (1, 0), (-1, 0), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(overview)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Executive summary", styles["heading"]))
    story.append(Paragraph(_escape(report.executive_summary), styles["body"]))
    story.append(Spacer(1, 7 * mm))

    if report.quick_wins:
        story.append(Paragraph("Quick wins", styles["heading"]))
        for index, item in enumerate(report.quick_wins, start=1):
            story.append(Paragraph(f"<b>{index}.</b> {_escape(item)}", styles["bullet"]))
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Prioritized findings", styles["heading"]))
    for index, finding in enumerate(report.findings, start=1):
        block = [
            Paragraph(
                f"<font color='#5549DD'>{index:02d}</font> &nbsp; {_escape(finding.title)}",
                styles["finding_title"],
            ),
            Paragraph(
                f"<b>{finding.severity.upper()}</b> &nbsp; {finding.confidence.upper()} CONFIDENCE &nbsp; PRIORITY {round(finding.score)}",
                styles["meta"],
            ),
            Paragraph(f"<b>Why it matters</b><br/>{_escape(finding.why_it_matters)}", styles["body"]),
            Paragraph(f"<b>Suggested fix</b><br/>{_escape(finding.recommendation)}", styles["fix"]),
            Paragraph(f"<b>Evidence</b><br/>{_escape(finding.evidence)}", styles["evidence"]),
            Paragraph(f"Affected pages: {len(finding.affected_urls)}", styles["meta"]),
            Spacer(1, 5 * mm),
        ]
        story.append(KeepTogether(block))

    if report.limitations:
        story.append(PageBreak())
        story.append(Paragraph("Coverage and limitations", styles["heading"]))
        for item in report.limitations:
            story.append(Paragraph(f"- {_escape(item)}", styles["bullet"]))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return stream.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle("Eyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=INDIGO, spaceAfter=5, letterSpacing=1.4),
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=INK, alignment=0, spaceAfter=5),
        "url": ParagraphStyle("URL", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED),
        "heading": ParagraphStyle("Heading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=INK, spaceBefore=2, spaceAfter=7),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=15, textColor=MUTED, spaceAfter=6),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, leftIndent=4 * mm, firstLineIndent=-4 * mm, textColor=MUTED, spaceAfter=4),
        "score": ParagraphStyle("Score", parent=base["Normal"], fontName="Helvetica", fontSize=23, leading=18, textColor=colors.white, alignment=TA_CENTER),
        "metric": ParagraphStyle("Metric", parent=base["Normal"], fontName="Helvetica", fontSize=15, leading=15, textColor=INK, alignment=TA_CENTER),
        "finding_title": ParagraphStyle("FindingTitle", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK, spaceAfter=4),
        "meta": ParagraphStyle("Meta", parent=base["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=5),
        "fix": ParagraphStyle("Fix", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=colors.HexColor("#4D4862"), backColor=colors.HexColor("#F5F3FF"), borderPadding=7, spaceAfter=5),
        "evidence": ParagraphStyle("Evidence", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=13, textColor=MUTED, backColor=PAPER, borderPadding=6, spaceAfter=5),
    }


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.5 * mm, "Generated by Stellar - read-only SEO audit")
    canvas.drawRightString(A4[0] - 18 * mm, 8.5 * mm, f"Page {document.page}")
    canvas.restoreState()


def _escape(value: str) -> str:
    safe = (
        value.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2026", "...")
    )
    return safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
