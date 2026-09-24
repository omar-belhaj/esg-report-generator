"""
export_pdf.py
===============
Génère un rapport PDF à partir du rapport JSON final
(data/processed/rapport_final.json), via reportlab.

Usage :
    python app/export/export_pdf.py --in data/processed/rapport_final.json --out rapport_esg.pdf
"""

import argparse
import json
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


def construire_pdf(rapport: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("TitreRapport", parent=styles["Title"], fontSize=20, spaceAfter=6)
    style_note = ParagraphStyle("Note", parent=styles["Normal"], fontSize=8, textColor=colors.grey, spaceAfter=20)
    style_statut_ok = ParagraphStyle("StatutOK", parent=styles["Normal"], textColor=colors.HexColor("#155724"), fontName="Helvetica-Bold")
    style_statut_ko = ParagraphStyle("StatutKO", parent=styles["Normal"], textColor=colors.HexColor("#856404"), fontName="Helvetica-Bold")

    elements = []
    elements.append(Paragraph("Rapport de durabilité — NordTech Industries", style_titre))
    elements.append(Paragraph(f"Exercice {rapport['annee']} — aligné sur la taxonomie ESRS", styles["Normal"]))
    elements.append(Paragraph(
        "Document généré automatiquement à partir de données ESG fictives, à des fins de "
        "démonstration (projet portfolio). Chaque chiffre cité a fait l'objet d'un contrôle "
        "automatisé de correspondance avec les données source.",
        style_note,
    ))

    for section in rapport["sections"]:
        elements.append(Paragraph(section["esrs_section"], styles["Heading1"]))

        statut = section["statut_final"]
        if statut == "verifie":
            elements.append(Paragraph("✅ Vérifié", style_statut_ok))
        else:
            elements.append(Paragraph("⚠️ À corriger — revue humaine requise", style_statut_ko))

        elements.append(Spacer(1, 6))
        elements.append(Paragraph(section["texte_final"], styles["Normal"]))
        elements.append(Spacer(1, 10))

        kpis = section.get("kpis_utilises", [])
        if kpis:
            data = [["Indicateur", "Valeur", "Unité", "Variation YoY", "Statut"]]
            for kpi in kpis:
                variation = kpi.get("variation_pct")
                variation_str = f"{variation:+.2f}%" if isinstance(variation, (int, float)) else "n/a"
                data.append([
                    str(kpi.get("nom_indicateur", "")),
                    str(kpi.get("valeur", "")),
                    str(kpi.get("unite", "")),
                    variation_str,
                    str(kpi.get("statut_vs_objectif", "")),
                ])
            table = Table(data, hAlign="LEFT", colWidths=[5.5 * cm, 2 * cm, 2.5 * cm, 2.7 * cm, 2.5 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
            ]))
            elements.append(table)

        elements.append(Spacer(1, 20))

    doc.build(elements)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input_path",
                         default=os.path.join("data", "processed", "rapport_final.json"))
    parser.add_argument("--out", dest="output_path",
                         default=os.path.join("data", "processed", "rapport_esg.pdf"))
    args = parser.parse_args()

    with open(args.input_path, encoding="utf-8") as f:
        rapport = json.load(f)

    construire_pdf(rapport, args.output_path)
    print(f"[OK] Rapport PDF généré : {args.output_path}")


if __name__ == "__main__":
    main()
