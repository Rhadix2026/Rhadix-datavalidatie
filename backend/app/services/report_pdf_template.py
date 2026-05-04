"""
report_pdf_template.py — Generieke Rhadix PDF-template.

Scheidt opmaak van inhoud volledig:

  ┌─────────────────────────────────────────────────────┐
  │  report_models.py   → datatypen (Pydantic)          │
  │  report_builder.py  → data bouwen vanuit scan       │
  │  report_pdf_template.py → opmaak (dit bestand)      │
  │  reports.py         → thin router + assemblers      │
  └─────────────────────────────────────────────────────┘

Gebruik vanuit een router:

    from app.services.report_pdf_template import RhadixRenderer as R, COLORS as C

    story  = R.header_bar("Rhadix Beschikbaarheidsrapport", date_str)
    story += R.info_bar(["Zorginstelling", "Scan: Q4 2024", "Datum: 01-04-2025"])
    story += R.step_badge("STAP 1 — Beschikbaarheid van data",
                          "Dit rapport richt zich op de beschikbaarheid …",
                          color="blue")
    story += R.score_table(
        headers=["Beschikbaarheidsscore", "Velden aanwezig", "Ontbreekt"],
        values=["78%", "24", "4"],
        value_colors=["amber", "green", "red"],
    )
    story += R.separator()
    story += R.section("Overzicht per schema", heading_level=2)
    story += R.field_table(headers, rows, col_widths_mm)
    story += R.footer_bar("Rhadix Beschikbaarheidsrapport · Stap 1")
    pdf_bytes = R.build_pdf(story)
"""

from __future__ import annotations

import io
from typing import Any

# ── ReportLab ─────────────────────────────────────────────────────────────────
# Lazy import: geeft een duidelijke fout als reportlab niet is geïnstalleerd.
try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable, KeepTogether,
    )
    _RL_AVAILABLE = True
except ImportError:
    _RL_AVAILABLE = False

# ── Paginamaten ───────────────────────────────────────────────────────────────
PAGE_W_MM = 172     # A4 breedte min marges (18 mm elk)
PAGE_W    = None    # ingevuld zodra reportlab beschikbaar is

# ─────────────────────────────────────────────────────────────────────────────
# KLEUREN — één palet voor alle drie rapporten
# ─────────────────────────────────────────────────────────────────────────────

class COLORS:
    """
    Gedeeld kleurenpalet voor alle Rhadix PDF-rapporten.
    Gebruik: COLORS.BLUE, COLORS.RED, etc.
    """
    # Primaire huisstijlkleuren
    DARK     = None   # donkerblauw — titelbalken, sectionheaders
    MID      = None   # middelblauw — sub-badges
    BLUE     = None   # indigo-blauw — accenten, links, badges
    TEAL     = None   # teal — KIK-V badge
    # Semantische kleuren
    GREEN    = None
    AMBER    = None
    RED      = None
    # Neutrale kleuren
    GRAY     = None
    LIGHT    = None   # lichtgrijze achtergrond
    BORDER   = None
    TEXT     = None
    TEXT2    = None
    WHITE    = None
    # Achtergronden
    BG_DARK  = None   # tabelkopachtergrond
    BG_BLUE  = None   # lichtblauwe achtergrond
    BG_GREEN = None
    BG_AMBER = None
    BG_RED   = None
    BG_TEAL  = None

    # Rhadix brand extras
    NAVY         = None   # Rhadix navy header
    RHADIX_BLUE  = None   # light tree-blue accent
    RHADIX_SUB   = None   # subtitle blue

    @classmethod
    def _init(cls) -> None:
        if cls.DARK is not None:
            return   # al geïnitialiseerd
        H = rl_colors.HexColor
        # ── Rhadix brand ─────────────────────────────
        cls.NAVY         = H("#1A2847")   # Rhadix donker navy
        cls.RHADIX_BLUE  = H("#6FA8D0")   # lichtblauw accent (boom)
        cls.RHADIX_SUB   = H("#8BADC5")   # subtitel blauw
        # ── Primaire kleuren ─────────────────────────
        cls.DARK     = H("#1A2847")       # was #1E3A8A → nu Rhadix navy
        cls.MID      = H("#243561")       # iets lichter navy
        cls.BLUE     = H("#6FA8D0")       # was indigo → nu Rhadix accent
        cls.TEAL     = H("#0EA5E9")
        # ── Semantisch ───────────────────────────────
        cls.GREEN    = H("#22C55E")
        cls.AMBER    = H("#F59E0B")
        cls.RED      = H("#EF4444")
        # ── Neutraal ─────────────────────────────────
        cls.GRAY     = H("#64748B")
        cls.LIGHT    = H("#F1F5F9")
        cls.BORDER   = H("#E2E8F0")
        cls.TEXT     = H("#1E293B")
        cls.TEXT2    = H("#334155")
        cls.WHITE    = rl_colors.white
        cls.BG_DARK  = H("#0F1A30")
        cls.BG_BLUE  = H("#E8F2FA")       # was EEF2FF → licht Rhadix blauw
        cls.BG_GREEN = H("#F0FDF4")
        cls.BG_AMBER = H("#FFFBEB")
        cls.BG_RED   = H("#FEF2F2")
        cls.BG_TEAL  = H("#F0F9FF")


def _color(name: str):
    """Zet een kleurstring ('green' | 'red' | 'amber' | 'blue' | 'gray') om naar een COLORS-object."""
    COLORS._init()
    return {
        "green":  COLORS.GREEN,
        "amber":  COLORS.AMBER,
        "red":    COLORS.RED,
        "blue":   COLORS.BLUE,
        "teal":   COLORS.TEAL,
        "dark":   COLORS.DARK,
        "gray":   COLORS.GRAY,
        "white":  COLORS.WHITE,
    }.get(name, COLORS.GRAY)


def _bg_color(name: str):
    """Achtergrondkleur passend bij de semantische naam."""
    COLORS._init()
    return {
        "green": COLORS.BG_GREEN,
        "amber": COLORS.BG_AMBER,
        "red":   COLORS.BG_RED,
        "blue":  COLORS.BG_BLUE,
        "teal":  COLORS.BG_TEAL,
    }.get(name, COLORS.LIGHT)


def score_color_name(score: float) -> str:
    """Vertaalt een 0–100 score naar 'green' | 'amber' | 'red'."""
    if score >= 80:
        return "green"
    if score >= 60:
        return "amber"
    return "red"


# ─────────────────────────────────────────────────────────────────────────────
# STIJLEN — gedeelde ParagraphStyle-factory
# ─────────────────────────────────────────────────────────────────────────────

class STYLES:
    """
    Gedeelde ParagraphStyle-objecten.
    Aanmaken na COLORS._init() (beide vereisen reportlab).
    """
    _built = False

    h1:     Any = None
    h2:     Any = None
    h3:     Any = None
    body:   Any = None
    body2:  Any = None
    small:  Any = None
    bullet: Any = None
    footer: Any = None
    tbl_hdr:  Any = None
    tbl_cell: Any = None
    code:     Any = None

    @classmethod
    def _build(cls) -> None:
        if cls._built:
            return
        COLORS._init()
        C = COLORS
        F  = "Helvetica"
        FB = "Helvetica-Bold"
        FI = "Helvetica-Oblique"

        def ps(name, **kw) -> ParagraphStyle:
            # Defaults kunnen worden overschreven door kw (geen duplicate-kwarg fout).
            defaults = dict(fontName=F, fontSize=9, textColor=C.TEXT, leading=13)
            defaults.update(kw)
            return ParagraphStyle(name, **defaults)

        cls.h1       = ps("rh1", fontName=FB, fontSize=20, textColor=C.WHITE,
                           leading=26, spaceAfter=4)
        cls.h2       = ps("rh2", fontName=FB, fontSize=12, textColor=C.DARK,
                           leading=17, spaceBefore=14, spaceAfter=6)
        cls.h3       = ps("rh3", fontName=FB, fontSize=10, textColor=C.DARK,
                           leading=14, spaceBefore=8, spaceAfter=4)
        cls.body     = ps("rbody", fontSize=9, textColor=C.TEXT2, leading=14,
                           spaceAfter=6, alignment=TA_JUSTIFY)
        cls.body2    = ps("rbody2", fontSize=8, textColor=C.TEXT2, leading=13)
        cls.small    = ps("rsm",  fontSize=8, textColor=C.GRAY, leading=12)
        cls.bullet   = ps("rbul", fontSize=9, textColor=C.TEXT2, leading=13,
                           leftIndent=12, bulletIndent=4, bulletText="•")
        cls.footer   = ps("rft",  fontSize=8, textColor=C.GRAY,
                           alignment=TA_CENTER)
        cls.tbl_hdr  = ps("rth",  fontName=FB, fontSize=8, textColor=C.WHITE,
                           leading=10)
        cls.tbl_cell = ps("rtd",  fontSize=8, textColor=C.TEXT, leading=11)
        cls.code     = ps("rcode", fontSize=8, fontName=FI,
                           textColor=C.TEAL, leading=12)
        cls._built = True

    @classmethod
    def ps(cls, name: str, **kw) -> "ParagraphStyle":
        """Maak een aangepaste ParagraphStyle op basis van de basisstijl."""
        cls._build()
        defaults = dict(fontName="Helvetica", fontSize=9,
                        textColor=COLORS.TEXT, leading=13)
        defaults.update(kw)
        return ParagraphStyle(f"r_{name}", **defaults)


# ─────────────────────────────────────────────────────────────────────────────
# BOUWSTENEN — flowable-factory functies
# ─────────────────────────────────────────────────────────────────────────────

class RhadixRenderer:
    """
    Stateless namespace met flowable-bouwstenen voor Rhadix PDF-rapporten.
    Iedere methode retourneert een list[Flowable] die je bij `story` voegt.

    Voorbeeld:
        story  = RhadixRenderer.header_bar("Rhadix Rapport", "01-04-2025")
        story += RhadixRenderer.info_bar(["Zorginstelling", "Scan: Q1 2025"])
        pdf    = RhadixRenderer.build_pdf(story)
    """

    # ── Initialisatie ──────────────────────────────────────────────────────────

    @staticmethod
    def _require_rl() -> None:
        if not _RL_AVAILABLE:
            raise RuntimeError("reportlab is niet geïnstalleerd. Voeg 'reportlab' toe aan requirements.txt.")
        COLORS._init()
        STYLES._build()

    # ── 1. Titelbalk ──────────────────────────────────────────────────────────

    @staticmethod
    def header_bar(title: str, date_str: str) -> list:
        """
        Rhadix navy titelbalk: logo links, rapporttitel midden, datum rechts.
        """
        import os
        from reportlab.platypus import Image as RLImage

        RhadixRenderer._require_rl()
        C = COLORS

        # ── Logo cel ──────────────────────────────────────────────────────────
        LOGO_PATH = os.path.join(
            os.path.dirname(__file__), "..", "static", "rhadix-logo.png"
        )
        if os.path.exists(LOGO_PATH):
            logo_cell = RLImage(LOGO_PATH, width=55 * mm, height=14 * mm,
                                kind="proportional")
        else:
            # Fallback: tekst-logo als logo niet gevonden wordt
            logo_cell = Paragraph(
                "<b>RHADIX</b>",
                STYLES.ps("logo_fb", fontSize=14, textColor=C.WHITE,
                          fontName="Helvetica-Bold"),
            )

        title_data = [[
            logo_cell,
            Paragraph(title, STYLES.h1),
            Paragraph(date_str, STYLES.ps("hd", fontSize=8,
                      textColor=C.RHADIX_SUB, alignment=TA_RIGHT)),
        ]]
        tbl = Table(title_data, colWidths=[58 * mm, 88 * mm, 26 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.NAVY),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING",   (0, 0), (0, -1),  14),
            ("RIGHTPADDING",  (-1, 0), (-1, -1), 14),
            # subtiele scheidslijn tussen logo en titel
            ("LINEAFTER",     (0, 0), (0, 0), 0.5, C.RHADIX_BLUE),
        ]))
        return [tbl]

    # ── 2. Sub-badge onder titelbalk ──────────────────────────────────────────

    @staticmethod
    def subtitle_badge(text: str) -> list:
        """
        Middelblauw badge-blok direct onder de titelbalk (voor gecombineerd rapport).
        """
        RhadixRenderer._require_rl()
        C = COLORS
        tbl = Table(
            [[Paragraph(text, STYLES.ps("sb", fontName="Helvetica-Bold",
                         fontSize=8, textColor=C.WHITE, leading=10))]],
            colWidths=[172 * mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 18),
        ]))
        return [tbl, Spacer(1, 6)]

    # ── 3. Info-balk ──────────────────────────────────────────────────────────

    @staticmethod
    def info_bar(parts: list[str]) -> list:
        """
        Lichtgrijze balk met metadata (organisatie, scan, datum, bronsysteem).
        `parts` is een lijst strings die worden samengevoegd met '  ·  '.
        """
        RhadixRenderer._require_rl()
        C = COLORS
        tbl = Table(
            [[Paragraph("  ·  ".join(parts), STYLES.ps("ib", fontSize=8, textColor=C.GRAY))]],
            colWidths=[172 * mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.LIGHT),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ]))
        return [tbl]

    # ── 4. Meta-tabel (5 kolommen: org / bronsys / scandatum / gegenereerd / regelset) ──

    @staticmethod
    def meta_table(organization: str, systems_str: str, scan_date: str,
                   generated_date: str, ruleset: str = "KIK-V Modelgegevensset v1.0") -> list:
        """
        5-kolomstabel met scanmeta — geschikt voor het managementrapport.
        """
        RhadixRenderer._require_rl()
        C = COLORS
        W = 172 * mm
        data = [[
            Paragraph(f"<b>Organisatie</b><br/>{organization}", STYLES.tbl_cell),
            Paragraph(f"<b>Bronsysteem</b><br/>{systems_str}", STYLES.tbl_cell),
            Paragraph(f"<b>Scandatum</b><br/>{scan_date}", STYLES.tbl_cell),
            Paragraph(f"<b>Gegenereerd</b><br/>{generated_date}", STYLES.tbl_cell),
            Paragraph(f"<b>Regelset</b><br/>{ruleset}", STYLES.tbl_cell),
        ]]
        tbl = Table(data, colWidths=[W / 5] * 5)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.BG_BLUE),
            ("BOX",           (0, 0), (-1, -1), 0.5, C.BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C.BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        return [tbl, Spacer(1, 14)]

    # ── 5. Stap-badge ────────────────────────────────────────────────────────

    @staticmethod
    def step_badge(badge_text: str, description: str, color: str = "blue") -> list:
        """
        Gekleurde badge met stapomschrijving en beschrijving eronder.
        color: 'blue' | 'teal' | 'dark' | 'amber'
        """
        RhadixRenderer._require_rl()
        accent = _color(color)
        bg     = _bg_color(color)
        tbl = Table(
            [[Paragraph(badge_text, STYLES.ps("ba", fontName="Helvetica-Bold",
                         fontSize=9, textColor=accent, leading=12))]],
            colWidths=[172 * mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("BOX",           (0, 0), (-1, -1), 1, accent),
        ]))
        result = [Spacer(1, 10), tbl]
        if description:
            result += [Spacer(1, 4), Paragraph(description, STYLES.small)]
        result.append(Spacer(1, 12))
        return result

    # ── 6. Samenvatting-scoretabel ────────────────────────────────────────────

    @staticmethod
    def score_table(headers: list[str], values: list[str],
                    value_colors: list[str]) -> list:
        """
        Horizontale KPI-scoretabel met gekleurde waarden.
        headers, values, value_colors moeten dezelfde lengte hebben.
        value_colors: lijst van 'green' | 'amber' | 'red' | 'blue' | 'gray'
        Kolombreedte wordt automatisch verdeeld.
        """
        RhadixRenderer._require_rl()
        C  = COLORS
        n  = len(headers)
        cw = [172 * mm / n] * n

        tbl = Table([headers, values], colWidths=cw)
        ts = [
            # Header-rij
            ("BACKGROUND",    (0, 0), (-1, 0), C.BG_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C.GRAY),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            # Waarde-rij
            ("BACKGROUND",    (0, 1), (-1, 1), C.LIGHT),
            ("FONTNAME",      (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 1), (-1, 1), 14),
            # Gemeenschappelijk
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",           (0, 0), (-1, -1), 0.5, C.BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C.BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
        for col, vc in enumerate(value_colors):
            ts.append(("TEXTCOLOR", (col, 1), (col, 1), _color(vc)))
        tbl.setStyle(TableStyle(ts))
        return [tbl]

    # ── 7. Rhadix Index + KPI-hero ────────────────────────────────────────────

    @staticmethod
    def kpi_hero(main_value: str, main_label: str, main_sublabel: str,
                 main_color: str, kpis: list[dict]) -> list:
        """
        Groot KPI-blok: één hoofdgetal (Rhadix Index) + N kleinere KPI's.
        kpis: [{"value": "78", "label": "Beschikbaarheid", "sub": "Stap 1",
                 "color": "amber"}, ...]
        """
        RhadixRenderer._require_rl()
        C = COLORS
        W = 172 * mm
        mc = _color(main_color)

        def kpi_para(value, label, sub, col_name):
            c = _color(col_name)
            return Paragraph(
                f'<font color="{c.hexval()}" size="28"><b>{value}</b></font>'
                f'<br/><font size="8" color="#475569">van 100</font>'
                f'<br/><font size="9" color="#1e3a8a"><b>{label}</b></font>'
                f'<br/><font size="8" color="#94a3b8">{sub}</font>',
                STYLES.tbl_cell,
            )

        main_para = Paragraph(
            f'<font color="{mc.hexval()}" size="36"><b>{main_value}</b></font>'
            f'<br/><font size="8" color="#475569">van 100</font>'
            f'<br/><font size="9" color="#1e3a8a"><b>{main_label}</b></font>'
            f'<br/><font size="8" color="#94a3b8">{main_sublabel}</font>',
            STYLES.tbl_cell,
        )

        n_kpi = len(kpis)
        total_cols = 1 + n_kpi
        col_w = W / total_cols

        row = [main_para] + [
            kpi_para(k["value"], k["label"], k.get("sub", ""), k.get("color", "blue"))
            for k in kpis
        ]
        tbl = Table([row], colWidths=[col_w] * total_cols)
        ts = [
            ("BOX",           (0, 0), (-1, -1), 0.5, C.BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C.BORDER),
            ("BACKGROUND",    (0, 0), (-1, -1), C.WHITE),
            ("BACKGROUND",    (0, 0), (0, 0),   C.BG_BLUE),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        tbl.setStyle(TableStyle(ts))
        return [tbl, Spacer(1, 10)]

    # ── 8. Sectiekeop ─────────────────────────────────────────────────────────

    @staticmethod
    def section(text: str, heading_level: int = 2) -> list:
        """
        H2 of H3 sectiekop.
        """
        RhadixRenderer._require_rl()
        sty = STYLES.h2 if heading_level == 2 else STYLES.h3
        return [Paragraph(text, sty)]

    # ── 9. Status-badge rij ───────────────────────────────────────────────────

    @staticmethod
    def status_row(label: str, color: str) -> list:
        """
        Gekleurde statusbalk onder een scoretabel.
        Voorbeeld: "Totaalstatus: Gereed voor KIK-V-uitwisseling"
        """
        RhadixRenderer._require_rl()
        accent = _color(color)
        bg     = _bg_color(color)
        tbl = Table(
            [[Paragraph(label, STYLES.ps("sr", fontName="Helvetica-Bold",
                         fontSize=9, textColor=accent))]],
            colWidths=[172 * mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("BOX",           (0, 0), (-1, -1), 0.5, accent),
        ]))
        return [tbl, Spacer(1, 10)]

    # ── 10. Generieke detailtabel ─────────────────────────────────────────────

    @staticmethod
    def data_table(
        headers: list[str],
        rows: list[list],
        col_widths_mm: list[float],
        header_bg: str = "dark",
        stripe: bool = True,
        row_tints: dict[int, str] | None = None,
        tint_col: int | None = None,
    ) -> list:
        """
        Generieke gestreepte detailtabel.

        Args:
            headers       — kolomkoppen (strings)
            rows          — rijen; elementen mogen strings of Paragraph-objecten zijn
            col_widths_mm — breedte per kolom in mm (som ≈ 172)
            header_bg     — 'dark' | 'blue' | 'teal' | 'amber'
            stripe        — zebra-striping aan/uit
            row_tints     — {rij_index → kleurstring} voor per-rij achtergrond (1-based)
            tint_col      — kolom-index (0-based) waarvan de tekst ingekleurd wordt
                            (samen met row_tints)
        """
        RhadixRenderer._require_rl()
        C  = COLORS
        hdr_color = {
            "dark":  C.BG_DARK,
            "blue":  C.DARK,
            "teal":  C.TEAL,
            "amber": C.AMBER,
        }.get(header_bg, C.BG_DARK)

        all_rows = [headers] + rows
        cw = [w * mm for w in col_widths_mm]

        tbl = Table(all_rows, colWidths=cw)

        ts = [
            # Koptekst
            ("BACKGROUND",    (0, 0), (-1, 0), hdr_color),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C.GRAY),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            # Datarijen
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            # Grid
            ("BOX",           (0, 0), (-1, -1), 0.5, C.BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C.BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ]
        if stripe:
            ts.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [C.WHITE, C.LIGHT]))

        if row_tints:
            for row_idx, color_name in row_tints.items():
                bg = _bg_color(color_name)
                ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))
                if tint_col is not None:
                    ts.append(("TEXTCOLOR", (tint_col, row_idx), (tint_col, row_idx),
                                _color(color_name)))

        tbl.setStyle(TableStyle(ts))
        return [tbl]

    # ── 11. Schema-koptabel (gekleurde headerbalk) ────────────────────────────

    @staticmethod
    def schema_header(label: str, sublabel: str, score_str: str,
                      color: str = "blue") -> list:
        """
        Gekleurde koptabel voor een schema (bijv. 'Medewerker · 68 rijen · score 82%').
        """
        RhadixRenderer._require_rl()
        accent = _color(color)
        tbl = Table([[
            Paragraph(label, STYLES.ps(f"shd{label}", fontName="Helvetica-Bold",
                       fontSize=10, textColor=COLORS.WHITE)),
            Paragraph(sublabel, STYLES.ps(f"shs{label}", fontSize=8,
                       textColor=rl_colors.HexColor("#CBD5E1"))),
            Paragraph(score_str, STYLES.ps(f"shsc{label}", fontSize=12,
                       fontName="Helvetica-Bold", textColor=COLORS.WHITE,
                       alignment=TA_RIGHT)),
        ]], colWidths=[55 * mm, 80 * mm, 37 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), accent),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (0, -1),  10),
            ("RIGHTPADDING",  (-1, 0), (-1, -1), 10),
        ]))
        return [tbl]

    # ── 12. Actieplan-tabel ───────────────────────────────────────────────────

    @staticmethod
    def action_table(actions: list) -> list:
        """
        Actieplan-tabel: prioriteit, titel, categorie, schatting, stappen.
        `actions` is een lijst van ReportAction Pydantic-objecten.
        """
        RhadixRenderer._require_rl()
        C = COLORS
        PRIO_COLOR = {"hoog": "red", "gemiddeld": "amber", "laag": "green"}

        hdrs = ["Prioriteit", "Actie", "Categorie", "Uren", "Eerste stap"]
        rows = []
        for act in actions:
            prio_name  = act.priority if isinstance(act.priority, str) else act.priority.value
            prio_color = _color(PRIO_COLOR.get(prio_name, "gray"))
            first_step = act.steps[0] if act.steps else act.description[:80]
            rows.append([
                Paragraph(prio_name.capitalize(),
                          STYLES.ps(f"ap{id(act)}", fontName="Helvetica-Bold",
                                     fontSize=8, textColor=prio_color)),
                Paragraph(act.title, STYLES.ps(f"at{id(act)}", fontName="Helvetica-Bold",
                                                fontSize=8)),
                Paragraph(act.category, STYLES.tbl_cell),
                f"{act.estimated_hours:.0f}h",
                Paragraph(first_step, STYLES.tbl_cell),
            ])

        col_widths = [22, 45, 28, 14, 63]
        return RhadixRenderer.data_table(hdrs, rows, col_widths) + [Spacer(1, 10)]

    # ── 13. Bullet-lijst ──────────────────────────────────────────────────────

    @staticmethod
    def bullets(items: list[str]) -> list:
        """
        Bullet-lijst. Items mogen <b>, <i> en kleur-tags bevatten.
        """
        RhadixRenderer._require_rl()
        STYLES._build()
        return [Paragraph(item, STYLES.bullet) for item in items]

    # ── 14. Tekstparagraaf ────────────────────────────────────────────────────

    @staticmethod
    def text(content: str, size: str = "body") -> list:
        """
        Tekstblok. size: 'body' | 'small' | 'h2' | 'h3'
        """
        RhadixRenderer._require_rl()
        sty = {
            "body":  STYLES.body,
            "small": STYLES.small,
            "h2":    STYLES.h2,
            "h3":    STYLES.h3,
        }.get(size, STYLES.body)
        return [Paragraph(content, sty)]

    # ── 15. Scheidingslijn ────────────────────────────────────────────────────

    @staticmethod
    def separator(space_before: int = 10, space_after: int = 10) -> list:
        """Horizontale scheidingslijn met spatie."""
        RhadixRenderer._require_rl()
        return [
            Spacer(1, space_before),
            HRFlowable(width="100%", thickness=0.5, color=COLORS.BORDER),
            Spacer(1, space_after),
        ]

    # ── 16. Waarschuwingsregel ────────────────────────────────────────────────

    @staticmethod
    def warning_line(text: str, color: str = "amber") -> list:
        """Eén regel met gekleurde waarschuwingstekst."""
        RhadixRenderer._require_rl()
        return [Paragraph(text, STYLES.ps(f"wl{id(text)}", fontSize=8,
                          textColor=_color(color), spaceBefore=3))]

    # ── 17. Footer ────────────────────────────────────────────────────────────

    @staticmethod
    def footer_bar(text: str) -> list:
        """
        Rhadix footer: navy lijn + voettekst met 'by Rhoderlanden Groep'.
        """
        RhadixRenderer._require_rl()
        C = COLORS
        footer_data = [[
            Paragraph(text, STYLES.ps("ft_l", fontSize=7,
                      textColor=C.RHADIX_SUB)),
            Paragraph("Rhadix · by Rhoderlanden Groep",
                      STYLES.ps("ft_r", fontSize=7,
                      textColor=C.RHADIX_BLUE, alignment=TA_RIGHT)),
        ]]
        tbl = Table(footer_data, colWidths=[86 * mm, 86 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.NAVY),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (0, -1),  14),
            ("RIGHTPADDING",  (-1, 0), (-1, -1), 14),
        ]))
        return [Spacer(1, 16), tbl]

    # ── 18. KeepTogether helper ───────────────────────────────────────────────

    @staticmethod
    def keep(flowables: list) -> list:
        """Wrapper die een blok flowables bij elkaar houdt op één pagina."""
        return [KeepTogether(flowables)]

    # ── 19. Verticale ruimte ──────────────────────────────────────────────────

    @staticmethod
    def space(height_pt: int = 12) -> list:
        """Verticale spatie."""
        RhadixRenderer._require_rl()
        return [Spacer(1, height_pt)]

    # ── 20. PDF bouwen en retourneren ─────────────────────────────────────────

    @staticmethod
    def build_pdf(story: list, title: str = "Rhadix Rapport",
                  author: str = "Rhadix Validator") -> bytes:
        """
        Zet een `story` (list[Flowable]) om naar een PDF en retourneert de bytes.

        Gebruik:
            pdf_bytes = RhadixRenderer.build_pdf(story, title="Rhadix Beschikbaarheidsrapport")
            # Stuur als StreamingResponse vanuit de router.
        """
        RhadixRenderer._require_rl()
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm,  bottomMargin=16 * mm,
            title=title,
            author=author,
        )
        doc.build(story)
        buf.seek(0)
        return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
# HULPFUNCTIES — kleur- en labelomzetting
# ─────────────────────────────────────────────────────────────────────────────

def availability_label(score: float) -> str:
    if score >= 80:
        return "Uitstekend — data grotendeels aanwezig"
    if score >= 60:
        return "Goed — enkele hiaten gevonden"
    return "Aandacht vereist — meerdere hiaten"


def readiness_label(score: float) -> str:
    if score >= 90:
        return "Gereed voor KIK-V-uitwisseling"
    if score >= 50:
        return "Gedeeltelijk gereed — actie vereist"
    return "Niet gereed — significante gaps"


def quality_label(score: float) -> str:
    if score >= 80:
        return "Uitstekend"
    if score >= 70:
        return "Goed"
    if score >= 60:
        return "Voldoende"
    return "Onvoldoende"


READINESS_STATUS_LABEL = {
    "gereed":       "Gereed",
    "gedeeltelijk": "Gedeeltelijk gereed",
    "niet_gereed":  "Niet gereed",
}

READINESS_STATUS_COLOR = {
    "gereed":       "green",
    "gedeeltelijk": "amber",
    "niet_gereed":  "red",
}

SEVERITY_LABEL = {
    "error":   "Fout",
    "warning": "Waarschuwing",
    "info":    "Info",
}

SEVERITY_COLOR = {
    "error":   "red",
    "warning": "amber",
    "info":    "teal",
}

AVAILABILITY_STATUS_LABEL = {
    "aanwezig":       "Aanwezig",
    "ontbreekt":      "Ontbreekt",
    "niet_eenduidig": "Deels beschikbaar",
}

AVAILABILITY_STATUS_COLOR = {
    "aanwezig":       "green",
    "ontbreekt":      "red",
    "niet_eenduidig": "amber",
}
