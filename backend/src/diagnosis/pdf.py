from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, KeepTogether, LongTable, TableStyle


def urlsplit_label(url):
    path = urlsplit(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1].replace("-", " ").title() or "Open page"


def build_pdf(report):
    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    if "Vera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Vera", str(fonts / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("VeraBd", str(fonts / "VeraBd.ttf")))
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm, title=report["title"], author="Stellar")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Copy", fontName="Vera", fontSize=9.5, leading=14, spaceAfter=7, splitLongWords=True))
    styles.add(ParagraphStyle(name="Evidence", parent=styles["Copy"], fontSize=8, leading=12, textColor=colors.HexColor("#505568"), backColor=colors.HexColor("#F2F3F7"), borderPadding=7, spaceBefore=7, spaceAfter=12))
    styles.add(ParagraphStyle(name="Proof", parent=styles["Copy"], fontSize=9, leading=14, textColor=colors.HexColor("#292438"), backColor=colors.HexColor("#F3F0FA"), borderPadding=9, spaceBefore=5, spaceAfter=6))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["Copy"], fontName="VeraBd", textColor=colors.white))
    styles["Title"].textColor = colors.HexColor("#302774")
    styles["Title"].fontName = "VeraBd"
    for name in ("Heading1", "Heading2", "Heading3"):
        styles[name].textColor = colors.HexColor("#302774")
        styles[name].fontName = "VeraBd"
    story = []
    def p(text, style="Copy"):
        clean = str(text).replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
        story.append(Paragraph(escape(clean).replace("\n", "<br/>"), styles[style]))
    def link(url, label="Open source"):
        safe = escape(url, quote=True)
        story.append(Paragraph(f'<link href="{safe}" color="#4D3CAF">{escape(label)}</link>', styles["Evidence"]))
    p("STELLAR / WEBSITE DIAGNOSIS", "Heading3")
    p(report["title"], "Title")
    p("Management review of one resort", "Heading2")
    link(report["page_url"], "Open inspected resort page")
    identity = report.get("identity", {})
    if identity:
        identity_label = identity.get("branded_query") or identity.get("property_name", "Unknown")
        p("Verified property identity: " + identity_label + " | Confidence: " + identity.get("confidence", "unrated"), "Evidence")
    p("Inspected: " + str(report.get("captured_at") or "Capture unavailable"))
    p("Report version: " + str(report["version"]) + " | Diagnosis: " + report["diagnosis_id"])
    p("Management summary", "Heading1")
    p(report["overview"])
    narrative = report.get("narrative", {})
    if narrative.get("text"):
        p("Model-written introduction - editorial review required", "Heading2")
        p(narrative["text"])
        if narrative.get("evidence_ids"):
            p("Referenced evidence: " + ", ".join(narrative["evidence_ids"]))
    for f in report["findings"]:
        p(f["priority"].upper() + " - " + f["title"], "Heading3")
        p(f["action"])
    if not report["findings"]:
        p("No supported findings were assembled. Review agent coverage before interpreting this as a healthy page.")
    p("Scope and interpretation", "Heading2")
    p(f"{len(report['scope'])} captured page(s). Supporting pages provide context for the selected resort.")
    p("Observed website issues and proposed drafts are presented separately. Different agent scores are not comparable.")
    cases_by_agent = {case["agent"]: case for case in report["cases"]}
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    detailed_cases = [(finding, cases_by_agent[finding["primary_agent"]]) for finding in sorted(report["findings"], key=lambda item: priority_order.get(item["priority"], 9)) if finding["primary_agent"] in cases_by_agent]
    for number, (finding, case) in enumerate(detailed_cases, 1):
        if number == 1:
            story.append(PageBreak())
        urgency = {"critical": ("FIX FIRST", "Immediate technical correction"), "high": ("FIX FIRST", "Validate in the next release"), "medium": ("VALIDATE NEXT", "Confirm with a repeatable check"), "low": ("REVIEW BACKLOG", "Approve after contextual review")}.get(finding["priority"], ("MONITOR", "Retest when evidence changes"))
        header = [Paragraph(f"ACTION CASE {number:02d} | {escape(finding.get('classification_label', finding['classification']))}", styles["Heading3"]), Paragraph(escape(finding["title"]), styles["Title"]),
                  Paragraph(escape(urgency[0] + " | " + urgency[1]), styles["Heading3"])]
        story.append(KeepTogether(header))
        p("Responsible agent: " + case["agent_label"] + " | Contribution: " + (case.get("contribution_label") or "Primary finding owner"))
        supporters = sorted(set(finding.get("supporting_agents", [])))
        if supporters:
            labels = {item["agent"]: item["agent_label"] for item in report["cases"]}
            p("Supporting agents: " + ", ".join(labels.get(agent, agent) for agent in supporters))
        p("Suggested owner: " + finding["owner"])
        source_management = case.get("management", {})
        management = {**source_management, "issue_identified": finding["observation"], "why_management_should_care": finding["business_relevance"],
                      "evidence_ids": finding["evidence_ids"], "recommended_actions": [finding["action"]], "other_findings": []}
        p("Issue identified", "Heading2")
        p(management["issue_identified"])
        explanations = {item["evidence_id"]: item for item in source_management.get("evidence_explanations", []) if item["evidence_id"] in finding["evidence_ids"]}
        if finding["evidence_ids"]:
            p("Evidence explained", "Heading2")
        for eid in management.get("evidence_ids", []):
            e = report["evidence"][eid]
            explanation = explanations.get(eid, {})
            p(e.get("title") or "Observed proof", "Heading3")
            observed = str(e.get("observed_value") or e.get("observed") or "No observed value was retained.")
            normal = lambda value: " ".join(str(value or "").split()).casefold()
            if explanation.get("plain_language") and normal(explanation["plain_language"]) != normal(observed):
                p("WHAT THIS EVIDENCE MEANS\n" + explanation["plain_language"], "Proof")
            p("WHAT WE OBSERVED\n" + observed, "Proof")
            example = explanation.get("example")
            if example and not e.get("excerpt") and normal(example) not in {normal(observed), normal(explanation.get("plain_language"))}:
                p("EXAMPLE FROM THE EVIDENCE\n" + explanation["example"], "Evidence")
            if e.get("excerpt") and normal(e["excerpt"]) not in {normal(observed), normal(example)}:
                excerpt_lines = str(e["excerpt"]).splitlines()
                p("PROOF EXCERPT\n" + "\n".join(excerpt_lines[:6]), "Evidence")
            if e.get("expected_value"):
                p("COMPARISON OR EXPECTED CONDITION\n" + str(e["expected_value"]), "Proof")
            if e.get("fix_example"):
                p((e.get("fix_label") or "SUGGESTED ANSWER - REVIEW BEFORE IMPLEMENTATION") + "\n" + str(e["fix_example"]), "Proof")
            p("WHERE WE FOUND IT\n" + str(e.get("location") or "Selected resort page"), "Proof")
            p("Source: " + str(e.get("source_label") or "Source page"), "Evidence")
            link(e["source_url"], "Open evidence source")
            p(f"Evidence record: {e.get('support_type', 'evidence')} | {e.get('confidence', 'unrated')} confidence | captured {e['captured_at']}", "Evidence")
        p("Why management should care", "Heading2")
        p(management.get("why_management_should_care") or "The available checks did not produce a defensible management finding.")
        if management.get("other_findings"):
            p("Other findings", "Heading2")
            for item in management["other_findings"]:
                p("- " + item)
        action_block = [Paragraph("Recommended management action", styles["Heading2"]),
                        Paragraph(escape("Ask " + finding["owner"] + " to:"), styles["Copy"])]
        action_block.extend(Paragraph(escape("- " + item), styles["Copy"]) for item in management.get("recommended_actions", []))
        story.append(KeepTogether(action_block))
        if finding.get("completion_criteria"):
            p("How we confirm completion", "Heading2")
            p("- " + finding["completion_criteria"])
        p("Limitation: " + str(management.get("limitation") or "The result is limited to the captured evidence."), "Evidence")
    story.append(PageBreak())
    p("Agent coverage", "Title")
    p("Every specialist has a recorded contribution. A completed assessment is not presented as a website fault unless its evidence passed the finding gate.")
    findings_by_agent = {}
    for finding in report["findings"]:
        findings_by_agent.setdefault(finding["primary_agent"], []).append(finding["title"])
        for agent in finding.get("supporting_agents", []):
            findings_by_agent.setdefault(agent, []).append("Supporting evidence: " + finding["title"])
    rows = [[Paragraph("Agent", styles["TableHead"]), Paragraph("Contribution", styles["TableHead"]), Paragraph("Management outcome", styles["TableHead"])]]
    for case in report["cases"]:
        management = case.get("management", {})
        contribution = "; ".join(findings_by_agent.get(case["agent"], [])) or management.get("issue_identified") or "No supported conclusion"
        rows.append([Paragraph(escape(case["agent_label"]), styles["Copy"]),
                     Paragraph(escape(case.get("contribution_label") or case.get("contribution_role", "assessment").replace("_", " ")), styles["Copy"]),
                     Paragraph(escape(contribution), styles["Copy"])])
    table = LongTable(rows, colWidths=[38*mm, 42*mm, 90*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#302774")),
                               ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#DAD7E2")),
                               ("VALIGN", (0,0), (-1,-1), "TOP"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F6F5F9")]),
                               ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6)]))
    story.append(table)
    p("Limitations", "Heading1")
    for item in report["limitations"]:
        p(item)
    p("Inspected page inventory", "Heading2")
    inventory = []
    scope = list(report["scope"])
    for index in range(0, len(scope), 2):
        row = []
        for url in scope[index:index + 2]:
            row.append(Paragraph(f'<link href="{escape(url, quote=True)}" color="#4D3CAF">{escape(urlsplit_label(url))}</link>', styles["Evidence"]))
        while len(row) < 2:
            row.append(Paragraph("", styles["Evidence"]))
        inventory.append(row)
    if inventory:
        inventory_table = LongTable(inventory, colWidths=[85*mm, 85*mm])
        inventory_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0),
                                             ("RIGHTPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 3),
                                             ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
        story.append(inventory_table)
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Vera", 8)
        canvas.setFillColor(colors.HexColor("#666677"))
        canvas.drawString(20*mm, 11*mm, "Stellar | Resort management review")
        canvas.drawRightString(190*mm, 11*mm, str(document.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
