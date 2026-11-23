"""Immutable PDF snapshot of model output and doctor-entered review."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.storage import protected_path


def generate_report(path, patient, doctor, analysis, image, storage):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle", fontSize=24, leading=28, textColor=colors.HexColor("#10152D"), spaceAfter=12))
    styles.add(ParagraphStyle("Notice", parent=styles["BodyText"], textColor=colors.HexColor("#6D28D9"), backColor=colors.HexColor("#F3E8FF"), borderPadding=9, spaceAfter=12))
    body = styles["BodyText"]
    body.leading, body.spaceAfter = 14, 7
    def paragraph(text, style=body):
        return Paragraph(escape(str(text or "Not recorded")).replace("\n", "<br/>"), style)
    result = analysis.result
    story = [paragraph("PULSAR / RESEARCH REPORT", styles["ReportTitle"]),
             paragraph("Research decision support, not a confirmed medical diagnosis. Interpretation requires qualified doctor review.", styles["Notice"]),
             paragraph(f"Patient identifier: {patient.id}"), paragraph(f"Doctor: {doctor.name} ({doctor.email})"),
             paragraph(f"Analysis date (UTC): {analysis.created_at}"), paragraph(f"Image reference: {image.id}"),
             paragraph(f"Architecture: ResNet18 | Model version: {result['model_version']}"),
             paragraph(f"Model SHA-256: {result['model_sha256']}"),
             paragraph(f"Validation scope: {result['model_metadata']['validation_scope']}"),
             paragraph(f"Model classification: {result['predicted_class']}", styles["Heading2"])]
    table = Table([[paragraph("Verified class label"), paragraph("Model probability")]] +
                  [[paragraph(name), paragraph(f"{probability:.2%}")] for name, probability in result["probabilities"].items()], colWidths=[112 * mm, 58 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDE9FE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), .5, colors.HexColor("#D8D3E8"))]))
    story.extend([table, Spacer(1, 8 * mm)])
    visuals = []
    for key, title in [(image.storage_key, "Original image"), (analysis.heatmap_key, "ResNet18 Grad-CAM")]:
        file = protected_path(storage, key)
        if file.is_file():
            visual = Image(str(file), width=72 * mm, height=62 * mm, kind="proportional")
            visuals.append([paragraph(title), visual])
    if visuals:
        story.append(Table([[v[0] for v in visuals], [v[1] for v in visuals]], colWidths=[85 * mm] * len(visuals)))
    story.extend([paragraph("Doctor observations", styles["Heading2"]), paragraph(analysis.observations),
                  paragraph("Doctor-entered follow-up recommendations", styles["Heading2"]), paragraph(analysis.follow_up),
                  paragraph("Probabilities are model outputs and are not calibrated clinical risk scores. Grad-CAM highlights model-associated regions and does not establish causality or tumor localization.", styles["Notice"])])
    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#625E76"))
        canvas.drawString(20 * mm, 12 * mm, f"PULSAR research / {patient.id}")
        canvas.drawRightString(190 * mm, 12 * mm, f"Page {document.page}")
    document = SimpleDocTemplate(str(Path(path)), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=22 * mm, title="Patient research analysis", author="PULSAR Research")
    document.build(story, onFirstPage=footer, onLaterPages=footer)
