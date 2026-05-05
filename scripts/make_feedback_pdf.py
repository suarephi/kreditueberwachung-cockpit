"""Generate feedback-erich-2026-05.pdf — detailed write-up of all changes."""
from __future__ import annotations
import datetime as dt
from pathlib import Path

DE_MONTHS = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]


def de_date(d: dt.date) -> str:
    return f"{d.day}. {DE_MONTHS[d.month]} {d.year}"

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak,
                                 PageTemplate, Paragraph, Spacer, Table, TableStyle)


# -----------------------------------------------------------------------------
# Palette (cream/brown standard, kein Olivebalken — wirkt sonst KI-generiert)
# -----------------------------------------------------------------------------
BG       = colors.HexColor("#F5F0E6")
CARD     = colors.HexColor("#FFFFFF")
TEXT     = colors.HexColor("#2C2417")
MUTED    = colors.HexColor("#8C7E6A")
BORDER   = colors.HexColor("#D6CEBD")
HEADER   = colors.HexColor("#3B3022")
POSITIVE = colors.HexColor("#4A7C2E")
NEGATIVE = colors.HexColor("#B5371B")
WARNING  = colors.HexColor("#C48A1A")


# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------
ss = getSampleStyleSheet()

H_TITLE = ParagraphStyle("HTitle", parent=ss["Title"], fontName="Helvetica-Bold",
                         fontSize=26, leading=32, textColor=colors.white,
                         alignment=TA_LEFT, spaceAfter=4)
H_SUBTITLE = ParagraphStyle("HSubtitle", parent=ss["Title"], fontName="Helvetica",
                            fontSize=12, leading=16, textColor=colors.HexColor("#D6CEBD"),
                            alignment=TA_LEFT, spaceAfter=0)

H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=18, leading=22, textColor=TEXT,
                    spaceBefore=8, spaceAfter=10, alignment=TA_LEFT)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, leading=17, textColor=TEXT,
                    spaceBefore=14, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, leading=14, textColor=HEADER,
                    spaceBefore=10, spaceAfter=4)

BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=10, leading=14, textColor=TEXT,
                      spaceAfter=6, alignment=TA_LEFT)
BODY_MUTED = ParagraphStyle("BodyMuted", parent=BODY, textColor=MUTED, fontSize=9, leading=12)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=3)
CODE = ParagraphStyle("Code", parent=BODY, fontName="Courier", fontSize=9, leading=12,
                      textColor=HEADER, backColor=colors.HexColor("#EFE8DA"),
                      borderPadding=4, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=4)


# -----------------------------------------------------------------------------
# Page background + footer
# -----------------------------------------------------------------------------
def _draw_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(2 * cm, 1.2 * cm,
                      f"Kreditüberwachung Cockpit  ·  Feedback-Antwort an Erich  ·  "
                      f"{de_date(dt.date.today())}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def _draw_cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(HEADER)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def card_table(rows, col_widths, header=True, body_align="LEFT"):
    """Wraps long strings in Paragraphs so they can hyphenate inside the cells."""
    wrapped = []
    for ri, row in enumerate(rows):
        wr = []
        for c in row:
            if isinstance(c, Paragraph):
                wr.append(c)
            else:
                style = (ParagraphStyle("th", parent=BODY, fontName="Helvetica-Bold",
                                          textColor=colors.white, fontSize=9.5)
                         if (header and ri == 0)
                         else ParagraphStyle("td", parent=BODY, fontSize=9.5, leading=12))
                wr.append(Paragraph(str(c), style))
        wrapped.append(wr)

    style_cmds = [
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ALIGN",       (0, 0), (-1, -1), body_align),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",(0, 0), (-1, -1), 7),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LINEBELOW",   (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX",         (0, 0), (-1, -1), 0.6, BORDER),
        ("BACKGROUND",  (0, 1), (-1, -1), CARD),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t = Table(wrapped, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t


def kv_card(items: list[tuple[str, str]]):
    """Two-column key-value card. items = [(label, value), ...]"""
    rows = [[Paragraph(f"<b>{k}</b>", BODY), Paragraph(v, BODY)] for k, v in items]
    t = Table(rows, colWidths=[5.0 * cm, 11.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",(0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("BACKGROUND",  (0, 0), (-1, -1), CARD),
        ("BOX",         (0, 0), (-1, -1), 0.6, BORDER),
        ("LINEBELOW",   (0, 0), (-1, -1), 0.3, BORDER),
    ]))
    return t


def bullets(items: list[str]):
    return [Paragraph("•&nbsp;&nbsp;" + i, BULLET) for i in items]


# -----------------------------------------------------------------------------
# Document
# -----------------------------------------------------------------------------
def build(out_path: Path) -> None:
    doc = BaseDocTemplate(str(out_path), pagesize=A4,
                          leftMargin=2 * cm, rightMargin=2 * cm,
                          topMargin=2 * cm, bottomMargin=2 * cm,
                          title="Feedback-Antwort an Erich",
                          author="Treasury & Risk")
    cover_frame = Frame(0, 0, A4[0], A4[1], leftPadding=2.5 * cm, rightPadding=2.5 * cm,
                        topPadding=4.5 * cm, bottomPadding=2 * cm, id="cover")
    body_frame  = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_draw_cover_bg),
        PageTemplate(id="body",  frames=[body_frame],  onPage=_draw_bg),
    ])

    flow: list = []
    today_str = de_date(dt.date.today())

    # ---------- COVER ----------
    flow.append(Paragraph("Kreditüberwachung Cockpit", H_SUBTITLE))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph("Feedback-Antwort an Erich", H_TITLE))
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "Dokumentation aller Anpassungen am Mock-Datensatz und am Cockpit "
        "auf Basis der Beobachtungen und Wünsche aus dem Mail vom 4. Mai 2026.",
        ParagraphStyle("CoverLead", parent=BODY, textColor=colors.HexColor("#D6CEBD"),
                       fontSize=12, leading=17)))
    flow.append(Spacer(1, 4 * cm))
    flow.append(Paragraph(
        f"<font color='#D6CEBD'>Stand</font>  &nbsp; "
        f"<font color='#FFFFFF'>{today_str}</font>",
        ParagraphStyle("CoverMeta", parent=BODY, fontSize=11, leading=15,
                       textColor=colors.white)))
    flow.append(Paragraph(
        "<font color='#D6CEBD'>Branch</font>  &nbsp; "
        "<font color='#FFFFFF'>feedback-erich-2026-05  ·  5 Commits</font>",
        ParagraphStyle("CoverMeta2", parent=BODY, fontSize=11, leading=15,
                       textColor=colors.white)))
    flow.append(Paragraph(
        "<font color='#D6CEBD'>Datensatz</font>  &nbsp; "
        "<font color='#FFFFFF'>output_demo · 10'000 Kunden · 9'500 Kredite</font>",
        ParagraphStyle("CoverMeta3", parent=BODY, fontSize=11, leading=15,
                       textColor=colors.white)))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ---------- 1. ZUSAMMENFASSUNG ----------
    flow.append(Paragraph("1. Zusammenfassung", H1))
    flow.append(Paragraph(
        "Erichs Mail enthielt vier konkrete Datenqualitäts-Beobachtungen, drei "
        "Verständnisfragen, zwei UX-Schwächen sowie drei Wunschpunkte für "
        "zusätzliche Funktionalität. Alle Punkte sind umgesetzt. Keine Frage "
        "blieb offen.", BODY))

    summary_table = [
        ["Block", "Inhalt", "Commit"],
        ["1. Datenqualität",
         "Loan-Alter vs. Hausalter, Bauland-Felder, MFH/Gewerbe Mietzinsen, SLA-Matrix pro Event-Typ",
         "c80d05b"],
        ["2. Dashboards",
         "Tooltips für SLA-Verletzung und Offene Ereignisse, Aktionszentrum mit Loan-ID und klickbarem Link, SLA-Referenztabelle",
         "a6beea0"],
        ["3. Drill-downs",
         "Auf Portfolio, Überwachung, Risikofälle und Stresstest je Selectbox auf Top-50 Detail-Datensätze",
         "17a29af"],
        ["4. Wertschriftendepots",
         "Neues Schema (portfolio, position), 5 Anlagestrategien, 30 reale Schweizer und internationale ISINs, neue Dashboard-Seite",
         "ddeb218"],
        ["5. Konten und Transaktionen",
         "Neues Schema (account, account_tx), 24 Monate Historie, Lohnzahlungen passend zum Kreditdossier, sechs Material-Change-Typen",
         "b17d551"],
    ]
    flow.append(Spacer(1, 6))
    flow.append(card_table(summary_table, [3.4 * cm, 11 * cm, 2.2 * cm]))

    flow.append(PageBreak())

    # ---------- 2. ERICHS PUNKTE → UMSETZUNG ----------
    flow.append(Paragraph("2. Erichs Punkte und ihre Umsetzung", H1))
    flow.append(Paragraph(
        "Diese Tabelle bildet jeden Punkt aus dem Mail eins zu eins auf die "
        "umgesetzte Antwort ab. Details zu jedem Block folgen in den "
        "Abschnitten 3 bis 7.", BODY))
    flow.append(Spacer(1, 6))
    points = [
        ["Punkt", "Erichs Beobachtung", "Antwort / Umsetzung"],
        ["F1", "Was versteht man unter SLA-Verletzung?",
         "Bearbeitungsfrist überschritten. Frist hängt am Auslöser (regulatorisch oder intern), Severity skaliert sie. Tooltip auf Übersicht plus volle Referenztabelle auf Übersicht und Risikofälle."],
        ["B1", "Kredit kann nicht älter sein als das Haus.",
         "Origination-Date wird auf construction_year + 30 bis 180 Tage geclamped. Für Bauland (kein Gebäude) bleibt der Kredit beliebig alt."],
        ["B2", "Landkredit (Nr. 108) trägt trotzdem Heizung, Zimmer, Baujahr.",
         "Bauland-spezifische Felder (construction_year, last_renovation, living_area_sqm, rooms, bathrooms, heating_type, heating_year, geak_class, building_insurance_value) werden für object_type='Bauland' am Ende der Pipeline auf NULL gesetzt."],
        ["B3", "MFH und Gewerbe: Affordability nutzt Lohnausweis statt Mietzinsen.",
         "Affordability verzweigt jetzt nach Objekttyp: MFH = Mietzinsen minus Vacancy und Opex. Gewerbe rented = analog. Gewerbe owner_occupied = simulierter EBITDA-Proxy aus Marktwert. EFH/ETW/Ferienwohnung = wie bisher Lohnausweis. Neues Feld income_basis im affordability_assessment dokumentiert die Quelle."],
        ["F2", "Wie viele Jahre Amortisation 2. Hypothek?",
         "15 Jahre, linear. Entspricht Selbstregulierung SBVg (1. Hypothek auf 65% LTV, 2. Hypothek voll in max. 15 Jahren)."],
        ["F3", "Was zeigt 'Offene Ereignisse'?",
         "Posteingang der Kreditüberwachung. Events mit Status open / in_progress / escalated, in den letzten 90 Tagen erkannt. Tooltip auf der KPI-Kachel."],
        ["U1", "Aktionszentrum-Spalte heisst Dossier, zeigt aber Kundenname statt Kredit.",
         "Spalte umbenannt in Kredit / Kunde. Loan-ID prominent als K-XXXXXX, Kundenname kleiner darunter. Klick auf die Zeile öffnet das Kreditdossier mit ?loan_id=… als Deep-Link."],
        ["W1", "Drop-down auf unterliegende Daten.",
         "Auf den vier Hauptseiten (Portfolio, Überwachung, Risikofälle, Stresstest) je eine bis zwei Drill-down-Selectboxen, die die Top-50 hinter dem Aggregat zeigen, sortiert nach der dominierenden Kennzahl."],
        ["W2", "Wertschriftendepots für einen Teil der Kunden.",
         "Neues Schema mit 30 realen ISINs (CH-Bonds, Pfandbriefe, UBS/iShares-ETFs, CH-Bluechips, internationale Bluechips). 5 Strategien (konservativ bis 100% Aktien). Verteilung 35/25/20/12/8. Höhere Segmente bekommen mit höherer Wahrscheinlichkeit ein Depot. Neue Page Wertschriften."],
        ["W3", "Kontotransaktionen mit konsistenten Lohnzahlungen und Veränderungen.",
         "Neues Schema mit account und account_tx. 24 Monate Historie. Lohn am 25., 13. im Dezember, Bonus im März, Hypothek am 5., Daueraufträge, Kartenkäufe, ATM, Quartalssteuern, jährliche 3a-Einzahlung. Für 7% der Kunden ein Material-Change-Ereignis (Lohnsprung, Lohnausfall, AG-Wechsel, 3a-Bezug, Erbschaft, Scheidung). Konsistenzcheck: 96% innerhalb +/-10% des Lohnausweises."],
    ]
    flow.append(card_table(points, [1.3 * cm, 5.5 * cm, 9.8 * cm]))

    flow.append(PageBreak())

    # ---------- 3. BLOCK 1 — DATENQUALITÄT ----------
    flow.append(Paragraph("3. Datenqualität (Block 1, Commit c80d05b)", H1))

    flow.append(Paragraph("3.1 Kredit nicht älter als das Haus", H2))
    flow.append(Paragraph(
        "Vorher konnte ein Hypothekarkredit ein Origination-Datum tragen, das "
        "vor dem Baujahr der finanzierten Liegenschaft lag. Das ist domäne-falsch.",
        BODY))
    flow.append(Paragraph("Annahmen:", H3))
    for b in bullets([
        "Loan-Alter wird auf das Baujahr plus 30 bis 180 Tage geclamped (zufällig).",
        "Für Bauland wird nicht geclamped, weil noch kein Gebäude existiert. Solche Kredite sind als product_line='baufinanzierung' markiert.",
        "Verifikation im 500er-Sample und 10k-Demo: 0 Kredite älter als ihr Gebäude.",
    ]): flow.append(b)

    flow.append(Paragraph("3.2 Bauland ohne Heizung, Baujahr und Zimmer", H2))
    flow.append(Paragraph(
        "Beim Landkredit Nr. 108 hatte das Property-Objekt eine Heizung, ein "
        "Baujahr und eine Zimmerzahl. Land hat das alles nicht.", BODY))
    flow.append(Paragraph("Bauland-Felder werden auf NULL gesetzt:", H3))
    for b in bullets([
        "construction_year, last_renovation_year",
        "living_area_sqm, rooms, bathrooms",
        "heating_type, heating_year (neu)",
        "geak_class, building_insurance_value",
    ]): flow.append(b)
    flow.append(Paragraph(
        "Die Nullung erfolgt am Ende der Pipeline, nachdem alle Konsumenten "
        "(Bewertung, Loan-Generator) die Werte für ihre Berechnungen genutzt "
        "haben. Plot-Fläche und Gefahrenkarten bleiben für Bauland erhalten. "
        "Im Kreditdossier wird statt Wohnfläche jetzt die Grundstücksfläche "
        "angezeigt.", BODY))

    flow.append(Paragraph("3.3 MFH und Gewerbe: Mietzinsen statt Lohnausweis", H2))
    flow.append(Paragraph(
        "Vorher wurde die Tragbarkeit für ein Mehrfamilienhaus oder eine "
        "Gewerbeliegenschaft auf Basis des Lohnausweises des Kreditnehmers "
        "berechnet. Das spiegelt die Bankpraxis nicht wider.", BODY))
    flow.append(Paragraph("Neue Logik (in src/.../affordability.py):", H3))
    aff_table = [
        ["Objekttyp", "Cashflow-Basis", "Annahmen"],
        ["MFH",
         "annual_rental_income_chf minus Opex",
         "Bruttorendite 4.0% bis 5.5% auf Marktwert; Vacancy 2% bis 5%; Opex 10% bis 15% des Bruttos"],
        ["Gewerbe (third_party_rented)",
         "annual_rental_income_chf minus Opex",
         "Bruttorendite 5.0% bis 7.0%; Vacancy 5% bis 12%; Opex 10% bis 18%"],
        ["Gewerbe (owner_occupied)",
         "Simulierter EBITDA",
         "8% bis 15% des Marktwerts pro Jahr (vereinfachte Firmenrendite-Annahme)"],
        ["EFH, ETW, Ferienwohnung, Bauland",
         "Lohnausweis Haushalt",
         "Wie bisher: alle Einkommensarten der Haushaltsmitglieder summiert"],
    ]
    flow.append(card_table(aff_table, [3.8 * cm, 4.4 * cm, 8.4 * cm]))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "Neue Felder in der Property-Tabelle: <b>annual_rental_income_chf</b> "
        "(berechnet nach Bewertung), <b>commercial_use</b> (für Gewerbe: "
        "owner_occupied 30%, third_party_rented 60%, mixed 10%). Neue Spalte "
        "<b>income_basis</b> in affordability_assessment macht im Kreditdossier "
        "transparent, welche Cashflow-Quelle für die DSTI-Berechnung verwendet "
        "wurde.", BODY))

    flow.append(PageBreak())

    flow.append(Paragraph("3.4 SLA realistisch pro Event-Typ", H2))
    flow.append(Paragraph(
        "Vorher hing die SLA-Frist nur an der Severity (info 60d, low 45d, "
        "medium 21d, high 10d, critical 3d), unabhängig vom Auslöser. In der "
        "Praxis ist die Frist primär durch den Event-Typ vorgegeben "
        "(regulatorisch oder intern), Severity ist nur ein Modifikator.", BODY))
    flow.append(Paragraph("Neues Modell:", H3))
    for b in bullets([
        "27 Event-Typen, jeder mit einer Standard-SLA in Tagen und einer textuellen Basis (Gesetz / Regulator / interne Quelle)",
        "Severity-Modifikator: critical 0.5x, high 0.75x, medium 1.0x, low 1.5x, info 2.0x",
        "Tatsächliche Frist = Standard-SLA mal Modifikator, gerundet, mind. 1 Tag",
        "Neues Feld event.sla_basis hält die regulatorische / interne Quelle fest und wird im Drill-down auf Überwachung sichtbar",
    ]): flow.append(b)
    flow.append(Paragraph(
        "Resultat im 10k-Demo: 27 unterschiedliche Quellen sichtbar, "
        "Spannweite der Fristen von 1 Tag (Sanktionstreffer, GwG Art. 9) bis "
        "360 Tagen (retirement_upcoming mit Severity info). Die volle Matrix "
        "ist in <b>Anhang A</b>.", BODY))

    flow.append(PageBreak())

    # ---------- 4. BLOCK 2 — DASHBOARDS ----------
    flow.append(Paragraph("4. Dashboards aussagekräftiger (Block 2, Commit a6beea0)", H1))

    flow.append(Paragraph("4.1 Tooltip auf 'Offene Ereignisse'", H2))
    flow.append(Paragraph(
        "Auf der Übersicht trägt die KPI-Kachel jetzt ein dezentes Info-Symbol. "
        "Mouseover zeigt die Definition: <i>Offene Ereignisse = Posteingang der "
        "Kreditüberwachung. Events mit Status open / in_progress / escalated, "
        "in den letzten 90 Tagen erkannt.</i>", BODY))

    flow.append(Paragraph("4.2 Tooltip auf 'SLA-Verletzung' im Aktionszentrum", H2))
    flow.append(Paragraph(
        "Der rote Chip zeigt jetzt im Tooltip: <i>SLA-Verletzung = "
        "Bearbeitungsfrist überschritten. Frist hängt am Auslöser "
        "(regulatorisch oder intern) und wird durch Severity skaliert. "
        "Beispiele: Sanktionstreffer 1 Tag (GwG Art. 9), Zahlungsverzug 30 "
        "Tage (Mahnwesen), KYC-Review 90 Tage (GwG Art. 6). Critical halbiert "
        "die Frist, info verdoppelt sie.</i>", BODY))

    flow.append(Paragraph("4.3 Aktionszentrum: Loan-ID statt Kundenname, Deep-Link aufs Dossier", H2))
    flow.append(Paragraph("Vorher zeigte die Tabellenspalte 'Dossier' nur den "
                          "Kundennamen. Jetzt:", BODY))
    for b in bullets([
        "Spaltenüberschrift umbenannt in 'Kredit / Kunde'.",
        "Loan-ID prominent oben (z.B. K-000142), Kundenname kleiner darunter.",
        "Ganze Zeile inkl. 'Öffnen' verlinkt auf /Kreditdossier?loan_id=&lt;id&gt;",
        "Auth-Token wird im Link mitgeschleppt, damit das Passwort nicht erneut abgefragt wird.",
        "Kreditdossier liest den Query-Parameter und springt direkt auf den Kredit.",
    ]): flow.append(b)

    flow.append(Paragraph("4.4 SLA-Referenztabelle im Cockpit", H2))
    flow.append(Paragraph(
        "Erichs Wunsch ('der severity table ist perfekt, auch noch ins "
        "dashboard natürlich als referenztabelle'): die volle 27-Zeilen-Matrix "
        "plus Severity-Modifikator-Erklärung ist jetzt sichtbar als:", BODY))
    for b in bullets([
        "Expander 'SLA-Referenz' am Ende der Übersicht.",
        "Permanente Sektion am Ende von Risikofälle (dort gehört das Thema fachlich hin).",
        "Quelle: dashboard/sla_reference.py (gespiegelt vom Generator-Modul).",
    ]): flow.append(b)

    flow.append(PageBreak())

    # ---------- 5. BLOCK 3 — DRILL-DOWNS ----------
    flow.append(Paragraph("5. Drill-downs auf Aggregationen (Block 3, Commit 17a29af)", H1))
    flow.append(Paragraph(
        "Erichs Wunsch nach Drop-down auf die unterliegenden Daten ist auf den "
        "vier Hauptseiten umgesetzt. Pro Seite ein bis zwei Drill-down-Boxen, "
        "die nach Auswahl eines Buckets die Top-50 Datensätze darunter zeigen, "
        "sortiert nach der dominierenden Kennzahl.", BODY))

    dd_table = [
        ["Seite", "Drill-down", "Sortierung"],
        ["01 Portfolio", "Kanton-Auswahl → Top 50 Kredite",          "current_outstanding desc"],
        ["01 Portfolio", "Objekttyp-Auswahl → Top 50 Kredite",       "current_outstanding desc"],
        ["02 Überwachung", "Severity-Auswahl → offene Events",        "sla_due_date asc"],
        ["02 Überwachung", "Event-Typ-Auswahl (Top 15) → Events",     "detected_at desc"],
        ["03 Risikofälle", "Risiko-Flag (watchlist / npl / forbearance)", "expected_loss desc"],
        ["03 Risikofälle", "Tragbarkeit (pass / exception / fail)",   "dsti_calculated desc"],
        ["05 Stresstest", "Top 50 Belehnungssprünge mit Kunde / Objekt", "delta LTV desc"],
        ["05 Stresstest", "Kanton-Auswahl unter Szenario",            "stressed_expected_loss desc"],
    ]
    flow.append(card_table(dd_table, [2.7 * cm, 8.5 * cm, 5.5 * cm]))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "Alle Drill-downs sind cached (st.cache_data, ttl 180 Sekunden), damit "
        "wiederholtes Klicken keine neuen DB-Queries auslöst. Wo eine Loan-ID "
        "in der Detailtabelle steht, lässt sie sich später im selben Pattern "
        "wie das Aktionszentrum anklicken (Deep-Link aufs Kreditdossier).", BODY))

    flow.append(PageBreak())

    # ---------- 6. BLOCK 4 — WERTSCHRIFTEN ----------
    flow.append(Paragraph("6. Wertschriftendepots (Block 4, Commit ddeb218)", H1))
    flow.append(Paragraph(
        "Erichs Wunsch nach Cross-Sell-Sicht: ein Teil der Kunden hat neben "
        "der Hypothek ein Wertschriftendepot bei der Bank.", BODY))

    flow.append(Paragraph("6.1 Schema", H2))
    for b in bullets([
        "<b>portfolio</b>: client_id, strategy, benchmark, inception_date, total_value_chf, cash_chf, ytd_return_pct, one_year_return_pct, custodian, fee_model, last_review_date.",
        "<b>position</b>: portfolio_id, ISIN, name, asset_class (bond / etf_bond / equity / etf_equity / cash / alternative), currency, quantity, avg_cost_chf, market_price_chf, market_value_chf, unrealized_pnl_chf, weight_pct, last_price_date.",
        "Spiegel in schema_pg/01_schema.sql für Postgres.",
    ]): flow.append(b)

    flow.append(Paragraph("6.2 Annahmen (alle parametrisierbar)", H2))
    flow.append(kv_card([
        ("Anteil mit Depot", "10% der Kunden (KU_PORTFOLIO_FRAC, default 0.10)"),
        ("Segment-Multiplier",
         "private_banking 4.0x, affluent 2.0x, business 1.5x, retail 0.6x"),
        ("Strategie-Verteilung",
         "konservativ 35%, vorsichtig 25%, mittel 20%, wachstum 12%, aktien 8%"),
        ("Volumen-Verteilung",
         "log-normal pro Segment: private_banking ~1.8 Mio CHF Median, "
         "affluent / business ~440k, retail ~165k. Spanne 20k bis 12 Mio."),
        ("Positionen je Depot", "8 bis 24, abhängig von Strategie"),
        ("Renditen",
         "YTD und 1-Jahres-Rendite strategiegerecht gesamplt mit Noise: "
         "konservativ ~2%, vorsichtig ~5%, mittel ~7%, wachstum ~11%, aktien ~14%"),
    ]))

    flow.append(Paragraph("6.3 Strategie-Allokation", H2))
    strat_table = [
        ["Strategie", "Bonds", "Aktien", "Cash", "Beschreibung"],
        ["konservativ", "85% (Bond + Bond-ETF)", "0%",  "15%", "Reine Anleihen-Allokation, Schwerpunkt CH-Staatsanleihen und Pfandbriefe"],
        ["vorsichtig",  "70%",                   "25%", "5%",  "Defensiv mit kleiner Aktien-Beimischung"],
        ["mittel",      "50%",                   "47%", "3%",  "Klassischer Balanced-Ansatz"],
        ["wachstum",    "25%",                   "72%", "3%",  "Aktiendominiert mit Bond-Cushion"],
        ["aktien",      "0%",                    "97%", "3%",  "Voll investiert in Aktien und Aktien-ETFs"],
    ]
    flow.append(card_table(strat_table, [2.6 * cm, 3.5 * cm, 2.3 * cm, 1.6 * cm, 6.5 * cm]))

    flow.append(Paragraph("6.4 ISIN-Universum", H2))
    flow.append(Paragraph(
        "30 reale ISINs, gemischt aus CH-Staatsanleihen / Pfandbriefen, "
        "Bond- und Aktien-ETFs (UBS, iShares, BlackRock), CH-Bluechips "
        "(Novartis, Roche, Nestlé, UBS Group, Zurich, Swiss Re, ABB, Sika, "
        "Geberit, Cembra) und internationalen Bluechips (Apple, Microsoft, "
        "Alphabet, ASML). Volle Liste in <b>Anhang B</b>.", BODY))

    flow.append(Paragraph("6.5 Dashboard-Seite '09 Wertschriften'", H2))
    for b in bullets([
        "KPIs: Anzahl Depots, verwaltetes Vermögen (AuM), Ø Volumen, Cash-Quote, Ø YTD.",
        "Donut + Tabelle der Strategien mit Volumen.",
        "Asset-Allokations-Bar gesamt nach Asset-Klasse.",
        "Top 50 Depots nach Volumen mit Volumen-Heatmap.",
        "Drill-down: Depot wählen → alle Positionen mit ISIN, Marktwert, Gewicht und unrealisiertem G/V.",
    ]): flow.append(b)

    flow.append(PageBreak())

    # ---------- 7. BLOCK 5 — KONTEN + TX ----------
    flow.append(Paragraph("7. Konten und Transaktionen (Block 5, Commit b17d551)", H1))
    flow.append(Paragraph(
        "Erichs Wunsch: Kontotransaktionen für einen Teil der Kunden, "
        "Lohnzahlungen passend zum Kreditdossier, ein paar Kunden mit "
        "wesentlichen Veränderungen.", BODY))

    flow.append(Paragraph("7.1 Schema", H2))
    for b in bullets([
        "<b>account</b>: client_id, IBAN, account_type (salary / savings / mortgage_servicing / rental / joint), currency, opened_date, current_balance_chf, avg_balance_12m_chf, status.",
        "<b>account_tx</b>: account_id, tx_date, value_date, amount_chf (signed), category, counterparty, description, reference. Indices auf (account_id, tx_date) und category.",
        "Spiegel in schema_pg/01_schema.sql für Postgres.",
    ]): flow.append(b)

    flow.append(Paragraph("7.2 Annahmen Konten", H2))
    flow.append(kv_card([
        ("Anteil mit Konten",
         "5% der Kunden (KU_TX_FRAC default 0.05; Demo ggf. 0.30 via env)"),
        ("Pro Kunde",
         "1 Lohnkonto (immer), 1 Sparkonto (~70%), "
         "1 Hypothekenservicing-Konto (wenn Kredit), "
         "1 Mietzinskonto (wenn MFH/Gewerbe-Eigentümer)"),
        ("Historie", "24 Monate (KU_TX_MONTHS default 24)"),
        ("IBAN", "CH + 2-Stellen-Prüfziffer + 5+12 Stellen, mock-grade"),
    ]))

    flow.append(Paragraph("7.3 Annahmen monatlicher Transaktionsstrom", H2))
    monthly_table = [
        ["Kategorie", "Tag im Monat", "Betrag", "Counterparty"],
        ["salary",            "25.",  "gross_salary / 12 (+/- 1%)", "AG-XXXX"],
        ["salary (13.)",      "20.12.", "Monatslohn", "13. Monatslohn"],
        ["salary (Bonus)",    "15.03.", "bonus_avg_3y", "Bonus"],
        ["mortgage_payment",  "5.",   "outstanding * 2.5% / 12", "Bank intern"],
        ["rental_income",     "2.",   "annual_rental_income / 12 * 0.95-1.0", "Mieter (div.)"],
        ["standing_order",    "3.",   "Versicherung 180-720, Telekom 70-180, KK 310-580", "Helvetia, Swisscom, KK"],
        ["card_purchase",     "div.", "log-normal, 5-1500 CHF", "Migros / Coop / SBB / Apple Pay / Amazon / Restaurant / Tankstelle"],
        ["withdrawal",        "div.", "100 / 200 / 500 CHF", "Bankomat"],
        ["tax",               "15. (3,6,9,12)", "max(800, monthly * 0.6)", "Steueramt"],
        ["3a_contribution",   "20.11.", "max. CHF 7'056", "Säule 3a Stiftung"],
        ["transfer (Spar)",   "28.",  "5%-25% des Monatslohns",  "Eigenes Sparkonto"],
    ]
    flow.append(card_table(monthly_table, [3.5 * cm, 2.3 * cm, 4.5 * cm, 5.7 * cm]))

    flow.append(PageBreak())

    flow.append(Paragraph("7.4 Material Changes für 7% der Konten", H2))
    flow.append(Paragraph(
        "Damit der Datensatz nicht wie ein gleichförmiges Laufband wirkt, wird "
        "bei 7% der Konto-Kunden ein Ereignis im 24-Monats-Fenster injiziert. "
        "Die Konsistenzprüfung Lohn vs. Lohnausweis weicht für diese Kunden "
        "automatisch um mehr als 15% ab und sie sind so im Cockpit erkennbar.", BODY))

    mc_table = [
        ["Typ", "Häufigkeit", "Effekt im Tx-Strom"],
        ["salary_jump",      "30%", "Lohn steigt sprunghaft um 15% bis 40% ab Monat X"],
        ["salary_loss",      "25%", "1 bis 6 Monate ohne Lohn (Arbeitslosigkeit), danach 65% bis 95% des alten Lohns"],
        ["employer_change",  "15%", "Counterparty wechselt; Lohn 92% bis 118% des alten"],
        ["3a_payout",        "10%", "Einmaliger Eingang CHF 50k bis 200k, Kategorie third_pillar_payout"],
        ["inheritance",      "10%", "Einmaliger Eingang CHF 50k bis 500k, Notariat als Counterparty"],
        ["divorce",          "10%", "Einmaliger Ausgang CHF 20k bis 200k, Anwaltskanzlei als Counterparty"],
    ]
    flow.append(card_table(mc_table, [3.4 * cm, 1.8 * cm, 10.7 * cm]))

    flow.append(Paragraph("7.5 Konsistenzprüfung Lohn ↔ Lohnausweis", H2))
    flow.append(Paragraph(
        "Im 10k-Demo (KU_TX_FRAC 0.05) ergibt der Konsistenzcheck "
        "12 mal AVG(salary tx der letzten 12 Mt) gegen income.gross_salary für "
        "die Lohnkunden:", BODY))
    for b in bullets([
        "<b>Im 500er-Smoke-Test:</b> 132 Lohnkunden, davon 127 (96%) innerhalb +/-10%, 3 (2%) mit Abweichung &gt;20% (das sind die Material-Change-Konten).",
        "<b>Im 10k-Demo:</b> ähnliche Verteilung (~96% in der Toleranz).",
        "Im Cockpit auf Page '10 Konten' visualisiert mit Ampel: 🟢 +/-5%, 🟡 5-15%, 🔴 &gt;15%.",
    ]): flow.append(b)

    flow.append(Paragraph("7.6 Dashboard-Seite '10 Konten'", H2))
    for b in bullets([
        "KPIs: Anzahl Konten, Saldo gesamt, Ø Saldo pro Konto, Lohnkunden in 12 Mt, Ø Monatslohn.",
        "Konsistenz-Tabelle Lohn vs. Lohnausweis mit Ampel und Top-Abweichungen.",
        "Materielle Veränderungen: alle Bewegungen über CHF 40k in den Sondervorgangs-Kategorien.",
        "Drill-down: Konto wählen + Multi-Kategorien-Filter → letzte 500 Tx.",
    ]): flow.append(b)

    flow.append(PageBreak())

    # ---------- ANHANG A — SLA-Matrix ----------
    flow.append(Paragraph("Anhang A: SLA-Matrix (vollständig)", H1))
    flow.append(Paragraph(
        "Tatsächliche Frist = Standard-SLA mal Severity-Modifikator. "
        "Modifikator: critical 0.5x, high 0.75x, medium 1.0x, low 1.5x, info 2.0x.",
        BODY))
    sla_rows = [
        ("sanctions_hit", 1, "GwG Art. 9 / Embargogesetz"),
        ("payment_default", 5, "FINMA-RS 2008/21 NPL"),
        ("pep_status_change", 5, "FINMA-RS 2016/7"),
        ("death_indicator", 10, "OR Erbrecht"),
        ("insurance_lapse", 14, "Hypothekarvertrag Versicherungspflicht"),
        ("ownership_change_grundbuch", 14, "OR / Hypothekarvertrag"),
        ("betreibung_recorded", 14, "Intern Bonitätsprüfung"),
        ("rate_change_threshold", 14, "Intern Kundeninformation"),
        ("duplicate_client_suspected", 14, "GwG Identifikation"),
        ("payment_arrears", 30, "OR Art. 102 / Mahnwesen"),
        ("covenant_breach_ltv", 30, "Internes Kreditreglement"),
        ("covenant_breach_dsti", 30, "SBVg-Selbstregulierung"),
        ("property_value_drop_>10%", 30, "FINMA-Selbstregulierung"),
        ("income_drop", 30, "Intern Re-Tragbarkeit"),
        ("address_change_unverified", 30, "GwG Identifikation"),
        ("divorce_indicator", 30, "Intern Bonitätsupdate"),
        ("third_pillar_payout", 30, "Intern Tragbarkeits-Recheck"),
        ("flood_risk_alert", 30, "Intern Risikoabklärung"),
        ("renovation_reported", 30, "Intern Doku/Neubewertung"),
        ("employer_change", 45, "Intern Lohnausweis"),
        ("property_revaluation_done", 45, "Intern Aktenaktualisierung"),
        ("affordability_recheck_due", 60, "Intern Tragbarkeit jährlich"),
        ("geak_change", 60, "Intern ESG/Akten"),
        ("rate_reset_due", 60, "Intern Konditionsangebot"),
        ("kyc_review_due", 90, "GwG Art. 6 / VSB 20"),
        ("manual_review_request", 30, "RM-Antrag (Default)"),
        ("retirement_upcoming", 180, "Intern Tragbarkeitsplan"),
    ]
    sla_table = [["Event-Typ", "Standard-SLA (Tage)", "Basis"]]
    sla_table += [[r[0], str(r[1]), r[2]] for r in sla_rows]
    flow.append(card_table(sla_table, [5.0 * cm, 2.5 * cm, 8.4 * cm]))

    flow.append(PageBreak())

    # ---------- ANHANG B — ISINs ----------
    flow.append(Paragraph("Anhang B: ISIN-Universum (30 Instrumente)", H1))
    isin_rows = [
        ("CH0224396285", "EIDG 4% 2049",                               "bond",       "CHF"),
        ("CH0344963361", "EIDG 0.5% 2030",                             "bond",       "CHF"),
        ("CH0526540133", "EIDG 0% 2031",                               "bond",       "CHF"),
        ("CH0419041339", "Pfandbriefzentrale 0.25% 2034",              "bond",       "CHF"),
        ("CH0224397044", "Kantonalbank ZH 1% 2032",                    "bond",       "CHF"),
        ("CH0102530786", "UBS ETF SBI Domestic Government 1-3",        "etf_bond",   "CHF"),
        ("CH0226976816", "iShares Swiss Domestic Government 7-15",     "etf_bond",   "CHF"),
        ("IE00B4WXJJ64", "iShares Core Global Aggregate CHF Hgd",      "etf_bond",   "CHF"),
        ("IE00B3F81R35", "iShares Core Euro Corporate Bond",           "etf_bond",   "EUR"),
        ("CH0008899764", "UBS ETF SMI",                                "etf_equity", "CHF"),
        ("CH0237935652", "UBS ETF SLI",                                "etf_equity", "CHF"),
        ("IE00B4L5Y983", "iShares Core MSCI World",                    "etf_equity", "CHF"),
        ("IE00B5BMR087", "iShares Core S&P 500",                       "etf_equity", "CHF"),
        ("IE00BKM4GZ66", "iShares Core MSCI EM IMI",                   "etf_equity", "CHF"),
        ("CH0030849654", "UBS ETF MSCI Switzerland 20/35",             "etf_equity", "CHF"),
        ("CH0012005267", "Novartis",                                   "equity",     "CHF"),
        ("CH0012032048", "Roche GS",                                   "equity",     "CHF"),
        ("CH0038863350", "Nestlé",                                     "equity",     "CHF"),
        ("CH0244767585", "UBS Group",                                  "equity",     "CHF"),
        ("CH0014852781", "Zurich Insurance",                           "equity",     "CHF"),
        ("CH0011075394", "Swiss Re",                                   "equity",     "CHF"),
        ("CH0102484968", "Cembra Money Bank",                          "equity",     "CHF"),
        ("CH0024899483", "Geberit",                                    "equity",     "CHF"),
        ("CH0023405456", "Sika",                                       "equity",     "CHF"),
        ("CH0012221716", "ABB",                                        "equity",     "CHF"),
        ("US0378331005", "Apple",                                      "equity",     "USD"),
        ("US5949181045", "Microsoft",                                  "equity",     "USD"),
        ("US02079K3059", "Alphabet A",                                 "equity",     "USD"),
        ("NL0010273215", "ASML",                                       "equity",     "EUR"),
        ("CH0331454167", "CSAM Money Market Fund CHF",                 "cash",       "CHF"),
    ]
    isin_table = [["ISIN", "Instrument", "Asset-Klasse", "Währung"]]
    isin_table += [[r[0], r[1], r[2], r[3]] for r in isin_rows]
    flow.append(card_table(isin_table, [3.4 * cm, 7.5 * cm, 3.0 * cm, 2.0 * cm]))

    flow.append(PageBreak())

    # ---------- 8. OFFENE PUNKTE ----------
    flow.append(Paragraph("8. Offene Punkte und Themen für Erich", H1))
    flow.append(Paragraph(
        "Alles aus dem Mail vom 4. Mai ist umgesetzt. Diese Liste bündelt "
        "Themen, bei denen Bestätigung oder Justierung sinnvoll wäre, und "
        "Erweiterungen, die mit wenig Mehraufwand möglich wären.", BODY))

    flow.append(Paragraph("8.1 Bestätigung erbeten", H2))
    for b in bullets([
        "<b>Mietzinsen für Gewerbe-Eigennutzer:</b> Aktuell wird ein simplifizierter EBITDA-Proxy von 8% bis 15% des Marktwerts verwendet. Sollte das verfeinert werden (z.B. Branchen-spezifisch nach NOGA-Code)?",
        "<b>SLA payment_arrears 30 Tage:</b> Soll die Frist gestaffelt sein (10 d für 1. Mahnung, 30 d für 2., 60 d für Bonitätsentscheid)? Aktuell ein einziger 30-d-Bucket.",
        "<b>Bauland-Kredite:</b> Aktuell als baufinanzierung markiert. Wäre eine eigene product_line ('landfinanzierung') sinnvoller?",
        "<b>Vacancy MFH:</b> Aktuell 2% bis 5%. Möchtest Du eine differenzierte Vacancy-Kurve nach Region (Zürich vs. Wallis)?",
    ]): flow.append(b)

    flow.append(Paragraph("8.2 Mit kleinem Aufwand machbar", H2))
    for b in bullets([
        "<b>Wertschriften-Drill-down vom Kreditdossier:</b> Im Kreditdossier-Header einen Hinweis 'Depot vorhanden' mit Link auf Wertschriften-Page filterbar nach Kunde.",
        "<b>Konten-Hinweis im Kreditdossier:</b> Analog ein 'Konten verfügbar (24 Mt)'-Badge mit Link.",
        "<b>SLA-Heatmap:</b> Auf Überwachung eine Heatmap Event-Typ vs. Severity vs. Anzahl überfälliger Events.",
        "<b>Konsistenzcheck Lohn vs. Mortgage-Payment:</b> Wenn die monatliche Hypothekenrate &gt;40% des monatlichen Lohns ausmacht, automatisch auf Konten-Page flaggen.",
        "<b>Material-Change-Erkennung:</b> Konten-Bewegungen mit den entsprechenden event-Records (income_drop, employer_change, third_pillar_payout) verknüpfen, damit der RM eine konsolidierte Sicht hat.",
    ]): flow.append(b)

    flow.append(Paragraph("8.3 Grösserer Aufwand", H2))
    for b in bullets([
        "<b>Volle Wertschriften-Bewegung:</b> Käufe und Verkäufe als eigene Tabelle (security_tx) plus Performance-Attribution.",
        "<b>Mieterspiegel:</b> Für MFH eine eigene tenant-Tabelle mit individuellen Mietverträgen, Eingangsverlauf und Mietzinsdepot.",
        "<b>Branchen-Cashflow für Gewerbe:</b> NOGA-spezifische EBITDA-Margen (Hotellerie 8% vs. Industrie 15%) statt pauschal.",
    ]): flow.append(b)

    flow.append(Paragraph("8.4 Deployment-Status", H2))
    for b in bullets([
        "<b>GitHub:</b> Branch feedback-erich-2026-05 nach main gemerged und gepusht (Fast-Forward, 6 Commits, kein PR).",
        "<b>Lokaler Datensatz:</b> output_demo neu generiert, 358 MB SQLite, 10'000 Kunden, 9'500 Kredite, alle neuen Tabellen befüllt.",
        "<b>Supabase Postgres:</b> Migration via COPY FROM STDIN (statt multi-INSERT) erfolgreich durchgelaufen, 27 Tabellen, ~2.6 Mio Rows in rund drei Minuten, kein Retry nötig.",
        "<b>Streamlit Cloud:</b> baut nach Merge automatisch neu, neue Pages '09 Wertschriften' und '10 Konten' sowie alle UX-Updates live.",
        "<b>Verifizierung in Supabase:</b> 0 Bauland-Properties mit Heizung, alle 126'467 Events tragen sla_basis, account_tx mit 414'152 Zeilen, 5 Strategien im Mix 35/25/20/14/8 Prozent, income_basis sauber verteilt (Lohnausweis 8'304, MFH 767, Gewerbe 299, EBITDA 130).",
    ]): flow.append(b)

    doc.build(flow)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "feedback-erich-2026-05.pdf"
    build(out)
    print(f"wrote {out}  ({out.stat().st_size / 1024:.1f} KB)")
