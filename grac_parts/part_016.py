from sqlalchemy import text, func
from sqlalchemy.orm import selectinload
from collections import defaultdict
import sqlite3

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.drawing.image import Image as XLImage

import io
import os
import datetime as datetime_module


# ============================================================
# CONFIG GENERAL
# ============================================================

# SOLO PDF + WORD
REPORT_KEYS_PDF_WORD = {
    "soa",
    "incidentes",
    "metricas_riesgos",
    "metricas_vuln",
    "metricas_cultura",
    "metricas_mejora",
    "dofa",
}

# SOLO EXCEL
REPORT_KEYS_EXCEL_ONLY = {
    "objetivos",
    "docs",
    "rev_accesos",
    "gestion_accesos",
    "legales",
    "cambios",
    "vuln",
    "remediacion",
    "concientizacion",
    "competencia",
    "proveedores",
    "matriz_riesgos",
    "registro_incidentes",
    "planes_respuesta_incidentes",
    "planes_accion_sgsi",
    "partes_interesadas",
    "inventario_ia",
    "inventario_software",
    "inventario_informacion",
    "inventario_datos_personales",
    "inventario_fisico",
}

REPORT_CATALOG = [
    {"key": "soa",                 "label": "Declaración de aplicabilidad (SoA / Anexo A)", "icon": "bi-check2-square"},
    {"key": "incidentes",          "label": "Métricas de Incidentes",                        "icon": "bi-exclamation-triangle"},
    {"key": "metricas_riesgos",    "label": "Métricas de Riesgos",                           "icon": "bi-graph-up"},
    {"key": "metricas_vuln",       "label": "Métricas de Vulnerabilidades",                  "icon": "bi-bar-chart"},
    {"key": "metricas_cultura",    "label": "Métricas de Cultura de Seguridad",              "icon": "bi-people"},
    {"key": "metricas_mejora",     "label": "Métricas Planes de Mejora",                     "icon": "bi-clipboard-check"},
    {"key": "dofa",                "label": "DOFA",                                          "icon": "bi-grid-3x3-gap"},

    {"key": "matriz_riesgos",      "label": "Matriz de Riesgos",                             "icon": "bi-shield-exclamation"},
    {"key": "registro_incidentes", "label": "Registro de Incidentes",                        "icon": "bi-journal-medical"},
    {"key": "planes_respuesta_incidentes", "label": "Planes de Respuesta a Incidentes", "icon": "bi-shield-check"},
    {"key": "planes_accion_sgsi",  "label": "Planes de Acción del Sistema de Gestión",       "icon": "bi-list-check"},
    {"key": "partes_interesadas",  "label": "Partes Interesadas",                            "icon": "bi-diagram-3"},
    {"key": "inventario_ia",       "label": "Inventario de IA (ISO 42001)",                 "icon": "bi-cpu-fill"},
    {"key": "inventario_software", "label": "Inventario de Software",                       "icon": "bi-cpu"},
    {"key": "inventario_informacion", "label": "Inventario de Información",               "icon": "bi-file-earmark-text"},
    {"key": "inventario_datos_personales", "label": "Inventario de Datos Personales",     "icon": "bi-shield-lock"},
    {"key": "inventario_fisico",   "label": "Inventario Físico",                            "icon": "bi-pc-display"},

    {"key": "objetivos",           "label": "Objetivos del SGSI",                            "icon": "bi-bullseye"},
    {"key": "docs",                "label": "Listado maestro de documentos",                 "icon": "bi-journal-text"},
    {"key": "rev_accesos",         "label": "Revisión de accesos",                           "icon": "bi-person-check"},
    {"key": "gestion_accesos",     "label": "Gestión de accesos",                            "icon": "bi-shield-lock"},
    {"key": "legales",             "label": "Requisitos legales",                            "icon": "bi-book"},
    {"key": "cambios",             "label": "Gestión de cambios (RFC)",                      "icon": "bi-arrow-repeat"},
    {"key": "vuln",                "label": "Registro de vulnerabilidades",                  "icon": "bi-bug"},
    {"key": "remediacion",         "label": "Plan de remediación",                           "icon": "bi-wrench-adjustable"},
    {"key": "concientizacion",     "label": "Plan de concientización",                       "icon": "bi-megaphone"},
    {"key": "competencia",         "label": "Plan de competencia",                           "icon": "bi-mortarboard"},
    {"key": "proveedores",         "label": "Registro de proveedores",                       "icon": "bi-truck"},
]


# ============================================================
# HELPERS GENERALES
# ============================================================

def _sql_fetchall(sql: str, params: dict | None = None):
    params = params or {}
    rows = db.session.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def _table_columns(table_name: str):
    try:
        info = db.session.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
        return [r["name"] for r in info]
    except Exception:
        return []


def _first_existing(table_name: str, candidates: list[str]) -> str | None:
    cols = set(_table_columns(table_name))
    for c in candidates:
        if c in cols:
            return c
    return None


def _truncate_text(value, max_len=120):
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, (datetime_module.date, datetime_module.datetime)):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _safe_rows(rows, columns, truncate_map=None):
    truncate_map = truncate_map or {}
    out = []
    for r in (rows or []):
        item = {}
        for c in columns:
            val = r.get(c)
            if c in truncate_map:
                val = _truncate_text(val, truncate_map[c])
            item[c] = val
        out.append(item)
    return out


def _auto_widths(columns):
    widths = []
    for c in columns:
        lc = (c or "").lower()

        if lc in {"id"}:
            widths.append(0.45 * inch)
        elif "fecha" in lc:
            widths.append(0.90 * inch)
        elif lc in {"estado", "severidad", "criticidad", "clasificacion", "version", "tipo"}:
            widths.append(0.85 * inch)
        elif lc in {"codigo", "ticket", "cve", "cvss"}:
            widths.append(0.85 * inch)
        elif "porcentaje" in lc or lc.endswith("_pct") or lc.startswith("pct_"):
            widths.append(0.90 * inch)
        elif lc in {"responsable", "owner", "propietario_riesgo", "usuario", "area"}:
            widths.append(1.10 * inch)
        elif "descripcion" in lc or "observ" in lc or "analisis" in lc or "justificacion" in lc or "motivation" in lc:
            widths.append(1.90 * inch)
        elif "nombre" in lc or "riesgo" in lc or "activo" in lc or "documento" in lc or "objetivo" in lc:
            widths.append(1.45 * inch)
        else:
            widths.append(1.00 * inch)

    return widths


def _join_evidence_names(evidencias):
    if not evidencias:
        return ""
    names = []
    for ev in evidencias:
        nm = getattr(ev, "original_name", None) or getattr(ev, "filename", None) or "Archivo"
        names.append(str(nm))
    return " | ".join(names)


def _risk_label_map():
    try:
        return {c["key"]: c["label"] for c in RISK_COLUMNS}
    except Exception:
        out = {}
        for c in RISK_COLUMNS:
            if hasattr(c, "get"):
                out[c.get("key")] = c.get("label")
        return out


def _mejora_label_map():
    return dict(MEJORA_PLAN_COLS)


def _partes_label_map():
    return dict(PARTES_INTERESADAS_COLS)


def _normalize_company_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _resolve_company_name(company_name: str = "") -> str:
    company_name = (company_name or "").strip()

    try:
        if company_name:
            cfg = EmpresaConfig.query.filter_by(company_name=company_name).first()
            if cfg and cfg.company_name:
                return cfg.company_name

        if company_name:
            normalized = _normalize_company_name(company_name)
            candidatos = EmpresaConfig.query.all()
            for c in candidatos:
                if _normalize_company_name(getattr(c, "company_name", "")) == normalized:
                    return c.company_name

        candidatos = EmpresaConfig.query.all()
        for c in candidatos:
            if getattr(c, "logo_filename", None):
                return c.company_name

        primero = EmpresaConfig.query.order_by(EmpresaConfig.id.asc()).first()
        if primero and primero.company_name:
            return primero.company_name
    except Exception:
        pass

    return company_name or ""


def _get_logo_and_company(company_name: str = ""):
    resolved_company = _resolve_company_name(company_name)

    logo_path = None
    try:
        if resolved_company:
            logo_path = get_company_logo_path(resolved_company)
            if logo_path and not os.path.exists(logo_path):
                logo_path = None
    except Exception:
        logo_path = None

    return resolved_company, logo_path


# ============================================================
# HELPERS PDF
# ============================================================

def _pdf_table(data_rows, columns, col_labels=None, col_widths=None):
    col_labels = col_labels or columns
    styles = getSampleStyleSheet()

    body_style = ParagraphStyle(
        "pdf_body",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
        wordWrap="CJK"
    )
    head_style = ParagraphStyle(
        "pdf_head",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
        textColor=colors.white
    )

    header = [Paragraph(f"<b>{lab}</b>", head_style) for lab in col_labels]
    body = []

    for r in (data_rows or []):
        row = []
        for c in columns:
            row.append(Paragraph(_truncate_text(_fmt(r.get(c)), 180), body_style))
        body.append(row)

    table = Table(
        [header] + body,
        colWidths=col_widths or _auto_widths(columns),
        repeatRows=1,
        splitByRow=1
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _pdf_info_box(title, text, bg_color="#f8fafc"):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ibox_title",
        parent=styles["BodyText"],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0b1220")
    )
    body_style = ParagraphStyle(
        "ibox_body",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#101827")
    )

    data = [[Paragraph(f"<b>{title}</b>", title_style)],
            [Paragraph((_fmt(text) or " "), body_style)]]

    tbl = Table(data, colWidths=[3.55 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_color)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def _build_pdf(title: str, sections: list[dict], company_name: str = "", wide: bool = False) -> bytes:
    buff = io.BytesIO()

    resolved_company, logo_path = _get_logo_and_company(company_name)

    pagesize = landscape(letter) if wide else letter
    doc = SimpleDocTemplate(
        buff,
        pagesize=pagesize,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    normal = ParagraphStyle("normal", parent=styles["BodyText"], fontSize=9, leading=12)

    story = []
    story.append(Paragraph(title, h1))
    story.append(Paragraph(f"Generado: {datetime_module.datetime.now().strftime('%Y-%m-%d %H:%M')}", normal))
    if resolved_company:
        story.append(Paragraph(f"Empresa: {resolved_company}", normal))
    story.append(Spacer(1, 10))

    for sec in (sections or []):
        render_mode = sec.get("render_mode", "default")

        if render_mode == "dofa_cards":
            story.append(Paragraph(str(sec.get("subtitle") or "DOFA"), h2))
            for p in (sec.get("paragraphs") or []):
                story.append(Paragraph(str(p), normal))
                story.append(Spacer(1, 4))

            cards_2x2 = sec.get("cards_2x2") or []
            if cards_2x2:
                rows_tbl = []
                for i in range(0, len(cards_2x2), 2):
                    left = cards_2x2[i]
                    right = cards_2x2[i + 1] if i + 1 < len(cards_2x2) else {"title": "", "text": ""}
                    rows_tbl.append([
                        _pdf_info_box(left.get("title", ""), left.get("text", ""), left.get("bg", "#f8fafc")),
                        _pdf_info_box(right.get("title", ""), right.get("text", ""), right.get("bg", "#f8fafc")),
                    ])

                grid = Table(rows_tbl, colWidths=[3.7 * inch, 3.7 * inch], hAlign="LEFT")
                grid.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(grid)
                story.append(Spacer(1, 8))

            strat_cards = sec.get("strategy_cards") or []
            if strat_cards:
                story.append(Paragraph("🧠 Estrategias FO / FA / DO / DA", h2))
                strat_rows = []
                for i in range(0, len(strat_cards), 2):
                    left = strat_cards[i]
                    right = strat_cards[i + 1] if i + 1 < len(strat_cards) else {"title": "", "text": ""}
                    strat_rows.append([
                        _pdf_info_box(left.get("title", ""), left.get("text", ""), "#f9fafb"),
                        _pdf_info_box(right.get("title", ""), right.get("text", ""), "#f9fafb"),
                    ])

                sgrid = Table(strat_rows, colWidths=[3.7 * inch, 3.7 * inch], hAlign="LEFT")
                sgrid.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(sgrid)

            if sec.get("page_break"):
                story.append(PageBreak())
            continue

        subtitle = sec.get("subtitle")
        if subtitle:
            story.append(Paragraph(str(subtitle), h2))

        for p in (sec.get("paragraphs") or []):
            story.append(Paragraph(str(p), normal))
            story.append(Spacer(1, 6))

        tb = sec.get("table")
        if tb and tb.get("rows") and tb.get("cols"):
            story.append(_pdf_table(
                data_rows=tb["rows"],
                columns=tb["cols"],
                col_labels=tb.get("labels"),
                col_widths=tb.get("widths")
            ))
            story.append(Spacer(1, 10))

        if sec.get("page_break"):
            story.append(PageBreak())

    doc.build(
        story,
        onFirstPage=lambda c, d: pdf_header_footer(c, d, "Informe SGSI", resolved_company, logo_path=logo_path),
        onLaterPages=lambda c, d: pdf_header_footer(c, d, "Informe SGSI", resolved_company, logo_path=logo_path),
    )
    return buff.getvalue()


# ============================================================
# HELPERS DOCX
# ============================================================

def _docx_table(doc: Document, data_rows, columns, col_labels=None):
    col_labels = col_labels or columns
    table = doc.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    for i, lab in enumerate(col_labels):
        hdr[i].text = str(lab)

    for r in (data_rows or []):
        cells = table.add_row().cells
        for i, c in enumerate(columns):
            cells[i].text = _fmt(r.get(c))
    return table


def _build_docx(title: str, sections: list[dict], company_name: str = "") -> bytes:
    doc = Document()

    resolved_company, logo_path = _get_logo_and_company(company_name)

    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    if logo_path and os.path.exists(logo_path):
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run()
            run.add_picture(logo_path, width=Inches(1.6))
        except Exception:
            pass

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p_title.add_run(title)
    run.bold = True
    run.font.size = Pt(16)

    p_meta1 = doc.add_paragraph()
    p_meta1.add_run(f"Generado: {datetime_module.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if resolved_company:
        p_meta2 = doc.add_paragraph()
        p_meta2.add_run(f"Empresa: {resolved_company}")

    doc.add_paragraph("")

    for sec in (sections or []):
        render_mode = sec.get("render_mode", "default")

        if render_mode == "dofa_cards":
            if sec.get("subtitle"):
                doc.add_heading(str(sec["subtitle"]), level=2)

            for ptxt in (sec.get("paragraphs") or []):
                doc.add_paragraph(str(ptxt))

            cards_2x2 = sec.get("cards_2x2") or []
            if cards_2x2:
                t = doc.add_table(rows=0, cols=2)
                t.style = "Table Grid"
                t.alignment = WD_TABLE_ALIGNMENT.CENTER

                for i in range(0, len(cards_2x2), 2):
                    row_cells = t.add_row().cells
                    left = cards_2x2[i]
                    right = cards_2x2[i + 1] if i + 1 < len(cards_2x2) else {"title": "", "text": ""}

                    row_cells[0].text = f"{left.get('title', '')}\n\n{_fmt(left.get('text', ''))}"
                    row_cells[1].text = f"{right.get('title', '')}\n\n{_fmt(right.get('text', ''))}"

                doc.add_paragraph("")

            strat_cards = sec.get("strategy_cards") or []
            if strat_cards:
                doc.add_heading("🧠 Estrategias FO / FA / DO / DA", level=2)
                t2 = doc.add_table(rows=0, cols=2)
                t2.style = "Table Grid"
                t2.alignment = WD_TABLE_ALIGNMENT.CENTER

                for i in range(0, len(strat_cards), 2):
                    row_cells = t2.add_row().cells
                    left = strat_cards[i]
                    right = strat_cards[i + 1] if i + 1 < len(strat_cards) else {"title": "", "text": ""}

                    row_cells[0].text = f"{left.get('title', '')}\n\n{_fmt(left.get('text', ''))}"
                    row_cells[1].text = f"{right.get('title', '')}\n\n{_fmt(right.get('text', ''))}"

                doc.add_paragraph("")

            if sec.get("page_break"):
                doc.add_page_break()
            continue

        if sec.get("subtitle"):
            doc.add_heading(str(sec["subtitle"]), level=2)

        for ptxt in (sec.get("paragraphs") or []):
            doc.add_paragraph(str(ptxt))

        tb = sec.get("table")
        if tb and tb.get("rows") and tb.get("cols"):
            _docx_table(
                doc,
                data_rows=tb["rows"],
                columns=tb["cols"],
                col_labels=tb.get("labels")
            )

        if sec.get("page_break"):
            doc.add_page_break()

        doc.add_paragraph("")

    buff = io.BytesIO()
    doc.save(buff)
    return buff.getvalue()


# ============================================================
# HELPERS EXCEL
# ============================================================

def _write_excel_sheet(ws, title: str, rows, cols, labels=None, company_name: str = "", logo_path: str | None = None):
    labels = labels or cols
    current_row = 1

    if logo_path and os.path.exists(logo_path):
        try:
            img = XLImage(logo_path)
            img.width = 140
            img.height = 70
            ws.add_image(img, "A1")
            current_row = 5
        except Exception:
            current_row = 1

    ws.cell(row=current_row, column=1, value=title)
    ws.cell(row=current_row, column=1).font = Font(bold=True, size=14)
    current_row += 1

    if company_name:
        ws.cell(row=current_row, column=1, value=f"Empresa: {company_name}")
        ws.cell(row=current_row, column=1).font = Font(bold=True)
        current_row += 1

    ws.cell(row=current_row, column=1, value=f"Generado: {datetime_module.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    ws.cell(row=current_row, column=1).font = Font(italic=True)
    current_row += 2

    header_fill = PatternFill("solid", fgColor="0D6EFD")
    header_font = Font(color="FFFFFF", bold=True)

    header_row = current_row
    for idx, lab in enumerate(labels, start=1):
        cell = ws.cell(row=header_row, column=idx, value=str(lab))
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    r = header_row + 1
    for item in (rows or []):
        for cidx, col in enumerate(cols, start=1):
            cell = ws.cell(row=r, column=cidx, value=_fmt(item.get(col)))
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        r += 1

    for col_cells in ws.columns:
        try:
            col_letter = col_cells[0].column_letter
        except Exception:
            continue

        max_len = 0
        for cell in col_cells:
            try:
                max_len = max(max_len, len(str(cell.value or "")))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 40)


def _build_excel(filename: str, sheets: list[dict], company_name: str = "") -> bytes:
    wb = Workbook()
    first = True

    resolved_company, logo_path = _get_logo_and_company(company_name)

    for sheet in sheets:
        if first:
            ws = wb.active
            ws.title = sheet.get("name", "Hoja1")[:31]
            first = False
        else:
            ws = wb.create_sheet(title=sheet.get("name", "Hoja")[:31])

        _write_excel_sheet(
            ws=ws,
            title=sheet.get("title", sheet.get("name", "Reporte")),
            rows=sheet.get("rows", []),
            cols=sheet.get("cols", []),
            labels=sheet.get("labels"),
            company_name=resolved_company,
            logo_path=logo_path
        )

    buff = io.BytesIO()
    wb.save(buff)
    return buff.getvalue()


# ============================================================
# PAYLOADS - SOA Y MÉTRICAS
# ============================================================

def _payload_soa(company=""):
    rows = _sql_fetchall("""
        SELECT
          nr,
          chapter,
          topic,
          applicable,
          implemented,
          justification,
          motivation
        FROM control
    """)

    def _soa_sort_key(row):
        nr = str(row.get("nr") or "").strip()
        nr = nr.replace("A.", "").replace("a.", "")
        parts = nr.split(".")

        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except Exception:
                nums.append(999)

        while len(nums) < 3:
            nums.append(0)

        return nums

    rows = sorted(rows, key=_soa_sort_key)

    cols = ["nr", "chapter", "topic", "applicable", "implemented", "justification", "motivation"]
    labels = ["Control", "Capítulo", "Control", "Aplica", "Implementado", "Justificación", "Evidencia"]

    sections = [{
        "subtitle": "Declaración de aplicabilidad",
        "paragraphs": [
            "Listado de controles de la declaración de aplicabilidad del SGSI."
        ],
        "table": {
            "rows": rows,
            "cols": cols,
            "labels": labels,
            "widths": [0.8*inch, 1.0*inch, 2.0*inch, 0.8*inch, 1.0*inch, 2.0*inch, 2.0*inch]
        }
    }]

    return {
        "title": "Declaración de aplicabilidad (SoA) – ISO/IEC 27001:2022",
        "filename": "soa",
        "wide": True,
        "sections": sections,
        "sheets": []
    }

def _payload_metricas_incidentes(company=""):
    import sqlite3
    from collections import defaultdict

    year_param = request.args.get("year", "", type=str)
    month_param = request.args.get("month", "", type=str)

    year_selected = None
    month_selected = None

    if year_param and year_param != "all":
        try:
            year_selected = int(year_param)
        except ValueError:
            year_selected = None

    if month_param and month_param != "all":
        try:
            month_selected = int(month_param)
        except ValueError:
            month_selected = None

    sql = """
        SELECT
            id,
            fecha_alerta,
            id_incidente,
            nombre_alerta,
            descripcion_alerta,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso_afectado,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion
        FROM registro_incidentes
        WHERE 1=1
    """

    params = []

    if year_selected is not None:
        sql += " AND strftime('%Y', fecha_alerta) = ?"
        params.append(str(year_selected))

    if month_selected is not None:
        sql += " AND strftime('%m', fecha_alerta) = ?"
        params.append(f"{month_selected:02d}")

    sql += " ORDER BY id DESC"

    rows = []
    try:
        conn = sqlite3.connect("sgsi.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        rows = []

    total_incidentes = len(rows)

    por_estado = defaultdict(int)
    por_clasificacion = defaultdict(int)
    por_prioridad = defaultdict(int)
    por_principio = defaultdict(int)
    tiempos_cierre = []

    def _parse_date(v):
        if not v:
            return None
        s = str(v).strip()
        if not s:
            return None

        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ):
            try:
                return datetime_module.datetime.strptime(s, fmt)
            except Exception:
                pass

        try:
            return datetime_module.datetime.fromisoformat(s.replace("Z", ""))
        except Exception:
            return None

    for r in rows:
        estado = (r.get("estado") or "Sin estado").strip()
        clasificacion = (r.get("clasificacion_incidente") or "Sin clasificar").strip()
        prioridad = (r.get("prioridad") or "Sin prioridad").strip()
        principio = (r.get("principio") or "Sin principio").strip()

        por_estado[estado] += 1
        por_clasificacion[clasificacion] += 1
        por_prioridad[prioridad] += 1
        por_principio[principio] += 1

        fa = _parse_date(r.get("fecha_alerta"))
        fc = _parse_date(r.get("fecha_cierre"))

        if fa and fc:
            try:
                dias = (fc.date() - fa.date()).days
                if dias < 0:
                    dias = 0
                tiempos_cierre.append(dias)
            except Exception:
                pass

    promedio_cierre = round(sum(tiempos_cierre) / len(tiempos_cierre), 2) if tiempos_cierre else 0

    rows_estado = sorted(
        [{"estado": k, "total": v} for k, v in por_estado.items()],
        key=lambda x: x["total"],
        reverse=True
    )

    rows_clasificacion = sorted(
        [{"clasificacion": k, "total": v} for k, v in por_clasificacion.items()],
        key=lambda x: x["total"],
        reverse=True
    )

    rows_prioridad = sorted(
        [{"prioridad": k, "total": v} for k, v in por_prioridad.items()],
        key=lambda x: x["total"],
        reverse=True
    )

    rows_principio = sorted(
        [{"principio": k, "total": v} for k, v in por_principio.items()],
        key=lambda x: x["total"],
        reverse=True
    )

    sections = [
        {
            "subtitle": "Resumen ejecutivo",
            "paragraphs": [
                f"Total de incidentes evaluados: {total_incidentes}.",
                f"Promedio de días de cierre: {promedio_cierre}.",
            ]
        },
        {
            "subtitle": "1) Incidentes por estado",
            "table": {
                "rows": rows_estado,
                "cols": ["estado", "total"],
                "labels": ["Estado", "Total"]
            }
        },
        {
            "subtitle": "2) Incidentes por clasificación",
            "table": {
                "rows": rows_clasificacion,
                "cols": ["clasificacion", "total"],
                "labels": ["Clasificación", "Total"]
            }
        },
        {
            "subtitle": "3) Incidentes por prioridad",
            "table": {
                "rows": rows_prioridad,
                "cols": ["prioridad", "total"],
                "labels": ["Prioridad", "Total"]
            }
        },
        {
            "subtitle": "4) Incidentes por principio afectado",
            "table": {
                "rows": rows_principio,
                "cols": ["principio", "total"],
                "labels": ["Principio", "Total"]
            }
        }
    ]

    return {
        "title": "Métricas de Incidentes",
        "filename": "metricas_incidentes",
        "wide": True,
        "sections": sections,
        "sheets": []
    }

def _payload_metricas_riesgos(company=""):
    cfg = MetricConfigRiesgos.query.first()
    apetito = safe_appetite_level((cfg.apetito_residual_definido if cfg else None), default="Moderado")
    tendencia = (cfg.tendencia_tiempo if cfg else "mensual") or "mensual"

    riesgos_all = Riesgo.query.all()
    total_archivados = sum(1 for r in riesgos_all if bool(getattr(r, "archivado", False)))
    total_activos = len(riesgos_all) - total_archivados
    riesgos = [r for r in riesgos_all if not bool(getattr(r, "archivado", False))]

    profile = {
        "inherente": {lvl: 0 for lvl in RISK_ORDER},
        "residual": {lvl: 0 for lvl in RISK_ORDER},
    }

    outside_appetite_count = 0
    top_candidates = []
    by_tipo = defaultdict(int)
    trend = defaultdict(lambda: {
        "inherente": {lvl: 0 for lvl in RISK_ORDER},
        "residual": {lvl: 0 for lvl in RISK_ORDER},
    })

    for r in riesgos:
        lvl_inh = normalize_level(r.riesgo_inherente)
        lvl_res = normalize_level(r.riesgo_residual)

        if lvl_inh in profile["inherente"]:
            profile["inherente"][lvl_inh] += 1
        if lvl_res in profile["residual"]:
            profile["residual"][lvl_res] += 1

        if lvl_res and apetito and is_outside_appetite(lvl_res, apetito):
            outside_appetite_count += 1
            top_candidates.append(r)

        tipo = (r.tipo_riesgo or "").strip() or "Sin clasificar"
        by_tipo[tipo] += 1

        dt = parse_any_date(r.fecha_identificacion) or parse_any_date(r.fecha_revision)
        if dt:
            pk = period_key(dt, tendencia)
            if lvl_inh in trend[pk]["inherente"]:
                trend[pk]["inherente"][lvl_inh] += 1
            if lvl_res in trend[pk]["residual"]:
                trend[pk]["residual"][lvl_res] += 1

    def impact_value(rr):
        try:
            return int(rr.impacto_res or 0)
        except Exception:
            return int(rr.impacto or 0) if rr.impacto else 0

    top_candidates_sorted = sorted(
        top_candidates,
        key=lambda rr: (level_rank(rr.riesgo_residual), impact_value(rr)),
        reverse=True
    )[:5]

    trend_rows = []
    for pk in sorted(trend.keys()):
        inh_dom = dominant_level(trend[pk]["inherente"])
        res_dom = dominant_level(trend[pk]["residual"])
        trend_rows.append({
            "periodo": pk,
            "inh_dominante": inh_dom or "Sin dato",
            "res_dominante": res_dom or "Sin dato",
            "inh_total": sum(trend[pk]["inherente"].values()),
            "res_total": sum(trend[pk]["residual"].values()),
        })

    tipo_rows = sorted(
        [{"tipo": k, "total": v} for k, v in by_tipo.items()],
        key=lambda x: x["total"],
        reverse=True
    )

    trend_text = build_trend_text_dominant(trend_rows)

    profile_rows = []
    for lvl in RISK_ORDER:
        profile_rows.append({
            "criterio": lvl,
            "total_inherente": profile["inherente"][lvl],
            "total_residual": profile["residual"][lvl],
        })

    top5_rows = []
    for r in top_candidates_sorted:
        top5_rows.append({
            "riesgo": getattr(r, "riesgo", ""),
            "nivel_residual": normalize_level(getattr(r, "riesgo_residual", "")),
            "impacto": getattr(r, "impacto_res_label", None) or getattr(r, "impacto_res", None) or getattr(r, "impacto", None) or "",
            "tipo_riesgo": getattr(r, "tipo_riesgo", "") or "Sin clasificar",
            "dueno": getattr(r, "propietario_riesgo", None) or getattr(r, "responsable", None) or "",
        })

    sections = [
        {
            "subtitle": "Resumen ejecutivo",
            "paragraphs": [
                f"Apetito residual: {apetito}.",
                f"Tendencia configurada: {tendencia.capitalize()}.",
                f"Riesgos fuera del apetito: {outside_appetite_count}.",
                f"Riesgos activos: {total_activos}. Riesgos archivados: {total_archivados}.",
            ]
        },
        {
            "subtitle": "1) Perfil de riesgo global",
            "table": {
                "rows": profile_rows,
                "cols": ["criterio", "total_inherente", "total_residual"],
                "labels": ["Criterio", "Total Inherente", "Total Residual"]
            }
        },
        {
            "subtitle": "2) Top 5 riesgos críticos",
            "paragraphs": [f"Riesgos con residual ≥ apetito ({apetito})."],
            "table": {
                "rows": top5_rows,
                "cols": ["riesgo", "nivel_residual", "impacto", "tipo_riesgo", "dueno"],
                "labels": ["Riesgo", "Nivel Residual", "Impacto", "Tipo de Riesgo", "Dueño"]
            }
        },
        {
            "subtitle": "3) Tendencia en el tiempo",
            "paragraphs": [
                f"Análisis de tendencia inherente: {trend_text['inherente']}",
                f"Análisis de tendencia residual: {trend_text['residual']}",
            ] + ([f"Análisis IA guardado: {cfg.tendencia_ai_text}"] if cfg and getattr(cfg, "tendencia_ai_text", None) else []),
            "table": {
                "rows": trend_rows,
                "cols": ["periodo", "inh_dominante", "res_dominante", "inh_total", "res_total"],
                "labels": ["Período", "Nivel dominante (Inherente)", "Nivel dominante (Residual)", "Total Inh", "Total Res"]
            }
        },
        {
            "subtitle": "4) Total de riesgos por Tipo de Riesgo",
            "table": {
                "rows": tipo_rows,
                "cols": ["tipo", "total"],
                "labels": ["Tipo de Riesgo", "Total"]
            }
        }
    ]

    return {
        "title": "Métricas de Riesgos",
        "filename": "metricas_riesgos",
        "wide": True,
        "sections": sections,
        "sheets": []
    }


def _payload_metricas_vulnerabilidades(company=""):
    year = request.args.get("year", type=int)
    today = datetime_module.date.today()
    if not year:
        year = today.year

    config = MetricasVulnerabilidadesConfig.query.first()
    sla_por_clas_norm = {}

    if config:
        for fila in config.clasificaciones:
            key = normalizar_clasificacion(fila.clasificacion)
            if key and fila.tiempo_max_cierre_dias is not None:
                sla_por_clas_norm[key] = fila.tiempo_max_cierre_dias

    def get_sla_dias(cls_raw):
        key = normalizar_clasificacion(cls_raw)
        if not key:
            return None
        return sla_por_clas_norm.get(key)

    inicio_dt = datetime_module.datetime(year, 1, 1)
    fin_dt = datetime_module.datetime(year + 1, 1, 1)

    cerradas = (
        VulnerabilidadRegistro.query
        .filter(VulnerabilidadRegistro.estado == 'Cerrado')
        .filter(VulnerabilidadRegistro.fecha_identificacion.isnot(None))
        .filter(
            db.or_(
                db.and_(
                    VulnerabilidadRegistro.fecha_cierre.isnot(None),
                    VulnerabilidadRegistro.fecha_cierre >= inicio_dt,
                    VulnerabilidadRegistro.fecha_cierre < fin_dt,
                ),
                db.and_(
                    VulnerabilidadRegistro.fecha_cierre.is_(None),
                    VulnerabilidadRegistro.fecha_identificacion >= inicio_dt,
                    VulnerabilidadRegistro.fecha_identificacion < fin_dt,
                )
            )
        )
        .all()
    )

    abiertas = (
        VulnerabilidadRegistro.query
        .filter(VulnerabilidadRegistro.estado == 'Abierto')
        .filter(VulnerabilidadRegistro.fecha_identificacion.isnot(None))
        .all()
    )

    cerradas_anio = []
    anio_dentro_tiempo = 0
    anio_fuera_tiempo = 0
    mensual = {}
    cerradas_fuera_sla = []
    cerradas_fuera_por_clas = {}

    for v in cerradas:
        cierre = v.fecha_cierre or v.fecha_identificacion
        if not cierre or cierre.year != year:
            continue

        cerradas_anio.append(v)
        cls_label = v.clasificacion or 'Sin clasificar'
        sla_dias = get_sla_dias(v.clasificacion)

        dias_cierre = None
        if v.fecha_identificacion:
            dias_cierre = (cierre - v.fecha_identificacion).days
            if dias_cierre < 0:
                dias_cierre = 0

        if sla_dias is not None and dias_cierre is not None:
            if dias_cierre <= sla_dias:
                anio_dentro_tiempo += 1
            else:
                anio_fuera_tiempo += 1
                cerradas_fuera_sla.append({
                    "codigo": v.codigo,
                    "clasificacion": cls_label,
                    "responsable": v.responsable,
                    "fecha_identificacion": v.fecha_identificacion,
                    "fecha_cierre": cierre,
                    "dias_cierre": dias_cierre,
                    "sla_dias": sla_dias,
                })
                info = cerradas_fuera_por_clas.setdefault(cls_label, {
                    "sla_dias": sla_dias,
                    "cantidad": 0
                })
                info["cantidad"] += 1

        m = cierre.month
        data_mes = mensual.setdefault(m, {'total': 0, 'dentro': 0, 'fuera': 0})
        data_mes['total'] += 1
        if sla_dias is not None and dias_cierre is not None:
            if dias_cierre <= sla_dias:
                data_mes['dentro'] += 1
            else:
                data_mes['fuera'] += 1

    total_cerradas_anio = len(cerradas_anio)
    pct_anio_dentro = round((anio_dentro_tiempo * 100.0 / total_cerradas_anio), 2) if total_cerradas_anio > 0 else 0.0
    pct_anio_fuera = round((anio_fuera_tiempo * 100.0 / total_cerradas_anio), 2) if total_cerradas_anio > 0 else 0.0

    vencidas = []
    vencidas_por_clas = {}
    for v in abiertas:
        cls_label = v.clasificacion or 'Sin clasificar'
        sla_dias = get_sla_dias(v.clasificacion)

        if sla_dias is None or not v.fecha_identificacion:
            continue

        fi = v.fecha_identificacion
        if hasattr(fi, "date"):
            fi = fi.date()

        dias_abierta = (today - fi).days
        if dias_abierta > sla_dias:
            vencidas.append({
                'codigo': v.codigo,
                'clasificacion': cls_label,
                'responsable': v.responsable,
                'fecha_identificacion': v.fecha_identificacion,
                'dias_abierta': dias_abierta,
                'sla_dias': sla_dias
            })
            info = vencidas_por_clas.setdefault(cls_label, {
                'sla_dias': sla_dias,
                'cantidad': 0
            })
            info['cantidad'] += 1

    codigos = [x["codigo"] for x in vencidas]
    analisis_map = {}
    if codigos:
        regs = VulnerabilidadAnalisis.query.filter(VulnerabilidadAnalisis.codigo.in_(codigos)).all()
        analisis_map = {r.codigo: (r.analisis or "") for r in regs}
    for x in vencidas:
        x["analisis"] = analisis_map.get(x["codigo"], "")

    codigos_cerradas = [x["codigo"] for x in cerradas_fuera_sla]
    analisis_map_cerradas = {}
    if codigos_cerradas:
        regs = VulnerabilidadAnalisis.query.filter(VulnerabilidadAnalisis.codigo.in_(codigos_cerradas)).all()
        analisis_map_cerradas = {r.codigo: (r.analisis or "") for r in regs}
    for x in cerradas_fuera_sla:
        x["analisis"] = analisis_map_cerradas.get(x["codigo"], "")

    datos_metricas = {
        "anio": year,
        "resumen_anual": {
            "total_cerradas": total_cerradas_anio,
            "dentro_sla": anio_dentro_tiempo,
            "fuera_sla": anio_fuera_tiempo,
            "pct_dentro": pct_anio_dentro,
            "pct_fuera": pct_anio_fuera,
        },
        "resumen_mensual": {
            m: {
                "total": data["total"],
                "dentro": data["dentro"],
                "fuera": data["fuera"],
            }
            for m, data in mensual.items()
        },
        "backlog": {
            "total_vencidas": len(vencidas),
            "por_clasificacion": {
                cls: {
                    "sla_dias": data["sla_dias"],
                    "cantidad": data["cantidad"],
                }
                for cls, data in vencidas_por_clas.items()
            },
        },
    }

    analisis_ia = None
    try:
        analisis_ia = analizar_metricas_vuln_ia(datos_metricas)
    except Exception:
        analisis_ia = None

    analisis_manual = session.get('analisis_vuln_manual')
    if analisis_manual:
        analisis_ia = analisis_manual

    mensual_rows = []
    for m in range(1, 13):
        data = mensual.get(m, {'total': 0, 'dentro': 0, 'fuera': 0})
        total = data['total']
        dentro = data['dentro']
        fuera = data['fuera']
        pct_dentro = round((dentro * 100.0 / total), 2) if total > 0 else 0
        pct_fuera = round((fuera * 100.0 / total), 2) if total > 0 else 0
        mensual_rows.append({
            "mes": f"{m:02d}",
            "cerradas_mes": total,
            "dentro_tiempo": dentro,
            "fuera_tiempo": fuera,
            "pct_dentro": pct_dentro,
            "pct_fuera": pct_fuera,
        })

    cerradas_fuera_resumen_rows = []
    for cls, data in cerradas_fuera_por_clas.items():
        cerradas_fuera_resumen_rows.append({
            "clasificacion": cls,
            "sla_dias": data["sla_dias"],
            "cantidad_fuera_sla": data["cantidad"],
        })

    backlog_rows = []
    for cls, data in vencidas_por_clas.items():
        backlog_rows.append({
            "clasificacion": cls,
            "sla_dias": data["sla_dias"],
            "cantidad_abiertas_vencidas": data["cantidad"],
        })

    sections = [
        {
            "subtitle": "🤖 Análisis IA (Resumen ejecutivo)",
            "paragraphs": [
                analisis_ia or "No se pudo generar análisis IA o no hay datos suficientes."
            ]
        },
        {
            "subtitle": f"Cumplimiento mensual por tiempos de cierre (detalle anual {year})",
            "table": {
                "rows": mensual_rows,
                "cols": ["mes", "cerradas_mes", "dentro_tiempo", "fuera_tiempo", "pct_dentro", "pct_fuera"],
                "labels": ["Mes", "Cerradas en el mes", "Dentro del tiempo", "Fuera de tiempo", "% dentro", "% fuera"]
            }
        },
        {
            "subtitle": f"Vulnerabilidades cerradas fuera de SLA (año {year})",
            "table": {
                "rows": cerradas_fuera_resumen_rows,
                "cols": ["clasificacion", "sla_dias", "cantidad_fuera_sla"],
                "labels": ["Clasificación", "SLA cierre (días)", "Cerradas fuera de SLA"]
            }
        },
        {
            "subtitle": "Detalle de vulnerabilidades cerradas fuera de SLA",
            "table": {
                "rows": _safe_rows(cerradas_fuera_sla, ["codigo", "clasificacion", "responsable", "fecha_identificacion", "fecha_cierre", "dias_cierre", "sla_dias", "analisis"], {"analisis": 150}),
                "cols": ["codigo", "clasificacion", "responsable", "fecha_identificacion", "fecha_cierre", "dias_cierre", "sla_dias", "analisis"],
                "labels": ["Código", "Clasificación", "Responsable", "Fecha identificación", "Fecha cierre", "Días cierre", "SLA (días)", "Análisis"]
            }
        },
        {
            "subtitle": "Backlog de vulnerabilidades abiertas vencidas (fuera de SLA)",
            "paragraphs": [f"Total abiertas vencidas: {len(vencidas)}"],
            "table": {
                "rows": backlog_rows,
                "cols": ["clasificacion", "sla_dias", "cantidad_abiertas_vencidas"],
                "labels": ["Clasificación", "SLA cierre (días)", "Vulnerabilidades abiertas vencidas"]
            }
        },
        {
            "subtitle": "Detalle de vulnerabilidades abiertas fuera de tiempo",
            "table": {
                "rows": _safe_rows(vencidas, ["codigo", "clasificacion", "responsable", "fecha_identificacion", "dias_abierta", "sla_dias", "analisis"], {"analisis": 150}),
                "cols": ["codigo", "clasificacion", "responsable", "fecha_identificacion", "dias_abierta", "sla_dias", "analisis"],
                "labels": ["Código", "Clasificación", "Responsable", "Fecha identificación", "Días abierta", "SLA (días)", "Análisis"]
            }
        }
    ]

    return {
        "title": "Métricas de Tiempos de Cierre de Vulnerabilidades",
        "filename": "metricas_vulnerabilidades",
        "wide": True,
        "sections": sections,
        "sheets": []
    }


def _payload_metricas_cultura(company=""):
    year_param = request.args.get("year", "", type=str)
    month_param = request.args.get("month", "", type=str)

    year_selected = None
    month_selected = None

    if year_param and year_param != "all":
        try:
            year_selected = int(year_param)
        except ValueError:
            year_selected = None

    if month_param and month_param != "all":
        try:
            month_selected = int(month_param)
        except ValueError:
            month_selected = None

    query = MetricasCultura.query

    if year_selected is not None:
        query = query.filter(MetricasCultura.anio == year_selected)

    if month_selected is not None:
        query = query.filter(MetricasCultura.mes == month_selected)

    registros = (
        query.order_by(MetricasCultura.anio.desc(), MetricasCultura.mes.desc()).all()
    )

    config_cultura = MetricasCulturaConfig.query.first()

    matrix_rows = []
    for r in registros:
        matrix_rows.append({
            "anio": r.anio,
            "mes": f"{r.mes:02d}" if r.mes is not None else "",
            "personas_contratadas": r.personas_contratadas or 0,
            "formacion_inicial_aprobada": r.formacion_inicial_aprobada or 0,
            "personas_reinduccion": r.personas_reinduccion or 0,
            "reinduccion_aprobada": r.reinduccion_aprobada or 0,
            "meta_formacion": round(r.meta_formacion or 0, 2),
            "actividades_planeadas": r.actividades_planeadas or 0,
            "actividades_ejecutadas": r.actividades_ejecutadas or 0,
            "meta_actividades": round(r.meta_actividades or 0, 2),
            "resultado_meta_general": round(r.resultado_meta_general or 0, 2),
            "analisis_mensual": r.analisis_mensual or "",
        })

    total_registros = len(matrix_rows)

    meta_fi = getattr(config_cultura, "meta_fi", None)
    meta_ep = getattr(config_cultura, "meta_ep", None)
    meta_general = getattr(config_cultura, "meta_general", None)

    promedio_formacion = round(
        sum(x["meta_formacion"] for x in matrix_rows) / total_registros, 2
    ) if total_registros else 0.0

    promedio_planeacion = round(
        sum(x["meta_actividades"] for x in matrix_rows) / total_registros, 2
    ) if total_registros else 0.0

    promedio_general = round(
        sum(x["resultado_meta_general"] for x in matrix_rows) / total_registros, 2
    ) if total_registros else 0.0

    cumple_formacion = 0
    cumple_planeacion = 0
    cumple_general = 0

    if meta_fi is not None:
        cumple_formacion = sum(1 for x in matrix_rows if (x["meta_formacion"] or 0) >= meta_fi)

    if meta_ep is not None:
        cumple_planeacion = sum(1 for x in matrix_rows if (x["meta_actividades"] or 0) >= meta_ep)

    if meta_general is not None:
        cumple_general = sum(1 for x in matrix_rows if (x["resultado_meta_general"] or 0) >= meta_general)

    resumen_rows = [
        {"indicador": "Cantidad de registros evaluados", "valor": total_registros},
        {"indicador": "Meta formación inicial configurada", "valor": meta_fi if meta_fi is not None else "No definida"},
        {"indicador": "Meta ejecución del plan configurada", "valor": meta_ep if meta_ep is not None else "No definida"},
        {"indicador": "Meta general configurada", "valor": meta_general if meta_general is not None else "No definida"},
        {"indicador": "Promedio meta formación (%)", "valor": f"{promedio_formacion}%"},
        {"indicador": "Promedio meta planeación (%)", "valor": f"{promedio_planeacion}%"},
        {"indicador": "Promedio resultado general (%)", "valor": f"{promedio_general}%"},
        {"indicador": "Meses que cumplieron meta formación", "valor": cumple_formacion},
        {"indicador": "Meses que cumplieron meta planeación", "valor": cumple_planeacion},
        {"indicador": "Meses que cumplieron meta general", "valor": cumple_general},
    ]

    detalle_rows = []
    for x in matrix_rows:
        detalle_rows.append({
            "anio": x["anio"],
            "mes": x["mes"],
            "meta_formacion": f'{x["meta_formacion"]}%',
            "meta_actividades": f'{x["meta_actividades"]}%',
            "resultado_meta_general": f'{x["resultado_meta_general"]}%',
            "analisis_mensual": x["analisis_mensual"],
        })

    sections = [
        {
            "subtitle": "Resumen ejecutivo",
            "paragraphs": [
                "Vista ejecutiva de la métrica de cultura de seguridad.",
                "Se presenta un consolidado de cumplimiento frente a las metas definidas y un detalle resumido por período."
            ]
        },
        {
            "subtitle": "Indicadores clave",
            "table": {
                "rows": resumen_rows,
                "cols": ["indicador", "valor"],
                "labels": ["Indicador", "Valor"],
                "widths": [4.8 * inch, 2.2 * inch]
            }
        },
        {
            "subtitle": "Detalle resumido por período",
            "table": {
                "rows": _safe_rows(
                    detalle_rows,
                    ["anio", "mes", "meta_formacion", "meta_actividades", "resultado_meta_general", "analisis_mensual"],
                    {"analisis_mensual": 160}
                ),
                "cols": ["anio", "mes", "meta_formacion", "meta_actividades", "resultado_meta_general", "analisis_mensual"],
                "labels": ["Año", "Mes", "Meta formación", "Meta planeación", "Resultado general", "Análisis mensual"]
            }
        }
    ]

    return {
        "title": "Métricas de Cultura de Seguridad",
        "filename": "metricas_cultura",
        "wide": True,
        "sections": sections,
        "sheets": []
    }


def _payload_metricas_mejora(company=""):
    estado = func.lower(func.trim(MejoraPlanRegistro.estado_actividad))
    eficacia = func.lower(func.trim(MejoraPlanRegistro.eficacia))
    tipo = func.lower(func.trim(MejoraPlanRegistro.tipo_accion))

    total = db.session.query(func.count(MejoraPlanRegistro.id)).scalar() or 0
    abiertos = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "abierto").scalar() or 0
    cerrados = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado").scalar() or 0
    eficaces = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado", eficacia == "sí").scalar() or 0
    no_eficaces = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado", eficacia == "no").scalar() or 0
    sin_eficacia = db.session.query(func.count(MejoraPlanRegistro.id)).filter(
        estado == "cerrado",
        (MejoraPlanRegistro.eficacia == None) | (func.trim(MejoraPlanRegistro.eficacia) == "")
    ).scalar() or 0

    correctivos = db.session.query(func.count(MejoraPlanRegistro.id)).filter(tipo == "correctiva").scalar() or 0
    mejoras = db.session.query(func.count(MejoraPlanRegistro.id)).filter(tipo == "mejora").scalar() or 0
    sin_tipo = db.session.query(func.count(MejoraPlanRegistro.id)).filter(
        (MejoraPlanRegistro.tipo_accion == None) | (func.trim(MejoraPlanRegistro.tipo_accion) == "")
    ).scalar() or 0

    cerrados_con_eficacia = eficaces + no_eficaces
    pct_eficacia = round((eficaces / cerrados_con_eficacia) * 100, 2) if cerrados_con_eficacia else 0.0

    sections = [
        {
            "subtitle": "Resumen ejecutivo",
            "paragraphs": [
                f"Total planes: {total}.",
                f"Abiertos: {abiertos}. Cerrados: {cerrados}.",
                f"Eficaces: {eficaces}. No eficaces: {no_eficaces}. Sin evaluar: {sin_eficacia}.",
                f"% eficacia (sobre cerrados con evaluación): {pct_eficacia}%.",
                f"Tipo de acción - Correctivos: {correctivos}. Mejora: {mejoras}. Sin tipo: {sin_tipo}.",
            ]
        },
        {
            "subtitle": "Indicadores clave",
            "table": {
                "rows": [{
                    "total_planes": total,
                    "abiertos": abiertos,
                    "cerrados": cerrados,
                    "eficaces": eficaces,
                    "no_eficaces": no_eficaces,
                    "sin_eficacia": sin_eficacia,
                    "pct_eficacia": f"{pct_eficacia}%",
                    "correctivos": correctivos,
                    "mejoras": mejoras,
                    "sin_tipo": sin_tipo,
                }],
                "cols": ["total_planes", "abiertos", "cerrados", "eficaces", "no_eficaces", "sin_eficacia", "pct_eficacia", "correctivos", "mejoras", "sin_tipo"],
                "labels": ["Total planes", "Abiertos", "Cerrados", "Eficaces", "No eficaces", "Sin evaluar", "% eficacia", "Correctivos", "Mejora", "Sin tipo"]
            }
        }
    ]

    return {
        "title": "Métricas – Planes de Mejora",
        "filename": "metricas_mejora",
        "wide": True,
        "sections": sections,
        "sheets": []
    }


# ============================================================
# PAYLOADS NUEVOS SOLO EXCEL O DOFA
# ============================================================

def _payload_matriz_riesgos(company=""):
    ver = (request.args.get("ver") or "activos").strip().lower()

    if ver == "archivados":
        riesgos = Riesgo.query.filter_by(archivado=True).order_by(Riesgo.id.desc()).all()
    elif ver == "todos":
        riesgos = Riesgo.query.order_by(Riesgo.archivado.asc(), Riesgo.id.desc()).all()
    else:
        riesgos = Riesgo.query.filter_by(archivado=False).order_by(Riesgo.id.desc()).all()

    sel = session.get('riesgos_campos', RISK_DEFAULT_FIELDS)
    label_map = _risk_label_map()

    selected_cols = [k for k in sel if k in label_map]
    if not selected_cols:
        selected_cols = list(RISK_DEFAULT_FIELDS)

    rows = []
    for r in riesgos:
        item = {}
        for key in selected_cols:
            item[key] = getattr(r, key, None)
        rows.append(item)

    labels = [label_map.get(k, k) for k in selected_cols]

    return {
        "title": "Matriz de Riesgos",
        "filename": "matriz_riesgos",
        "wide": True,
        "sections": [],
        "sheets": [{
            "name": "MatrizRiesgos",
            "title": "Matriz de Riesgos",
            "rows": rows,
            "cols": selected_cols,
            "labels": labels
        }]
    }


def _payload_registro_incidentes(company=""):
    conn = sqlite3.connect('sgsi.db')
    c = conn.cursor()

    filtro = (request.args.get('filtro') or '').strip()
    campo = (request.args.get('campo') or 'nombre_alerta').strip()

    campos_validos = {
        "nombre_alerta",
        "descripcion_alerta",
        "atacante",
        "estado",
        "principio",
        "prioridad",
        "id_incidente",
        "clasificacion_incidente",
        "cargo_responsable"
    }
    if campo not in campos_validos:
        campo = "nombre_alerta"

    base_query = """
        SELECT
            id,
            fecha_alerta,
            id_incidente,
            nombre_alerta,
            descripcion_alerta,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso_afectado,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion
        FROM registro_incidentes
    """

    params = ()
    if filtro:
        base_query += f" WHERE {campo} LIKE ?"
        params = (f"%{filtro}%",)

    base_query += " ORDER BY id DESC"
    c.execute(base_query, params)
    data = c.fetchall()
    conn.close()

    cols = [
        "id",
        "fecha_alerta",
        "id_incidente",
        "nombre_alerta",
        "descripcion_alerta",
        "clasificacion_incidente",
        "cargo_responsable",
        "atacante",
        "ubicacion_atacante",
        "tipo_recurso_afectado",
        "nombre_recurso_id",
        "estado",
        "fecha_cierre",
        "descripcion_cierre",
        "principio",
        "prioridad",
        "se_requiere_contencion",
        "fecha_hora_contencion",
        "descripcion_contencion",
        "se_requiere_recuperacion",
        "fecha_hora_recuperacion",
        "descripcion_recuperacion",
    ]

    labels = [
        "ID",
        "Fecha Alerta",
        "ID Incidente",
        "Nombre Alerta",
        "Descripción Alerta",
        "Clasificación",
        "Cargo Responsable",
        "Atacante",
        "Ubicación Atacante",
        "Tipo Recurso Afectado",
        "Recurso / ID",
        "Estado",
        "Fecha Cierre",
        "Descripción Cierre",
        "Principio",
        "Prioridad",
        "Req. Contención",
        "Fecha Contención",
        "Desc. Contención",
        "Req. Recuperación",
        "Fecha Recuperación",
        "Desc. Recuperación",
    ]

    rows = [dict(zip(cols, fila)) for fila in data]

    return {
        "title": "Registro de Incidentes",
        "filename": "registro_incidentes",
        "wide": True,
        "sections": [],
        "sheets": [{
            "name": "RegistroIncidentes",
            "title": "Registro de Incidentes",
            "rows": rows,
            "cols": cols,
            "labels": labels
        }]
    }


def _payload_planes_accion_sgsi(company=""):
    sel = session.get('mejora_plan_cols') or DEFAULT_MEJORA_PLAN_COLS
    label_map = _mejora_label_map()

    selected_cols = [k for k in sel if k in label_map]
    if not selected_cols:
        selected_cols = list(DEFAULT_MEJORA_PLAN_COLS)

    items = (
        MejoraPlanRegistro.query
        .options(selectinload(MejoraPlanRegistro.evidencias))
        .order_by(MejoraPlanRegistro.id.desc())
        .all()
    )

    rows = []
    for it in items:
        item = {}
        for key in selected_cols:
            if key == "evidencias":
                item[key] = _join_evidence_names(getattr(it, "evidencias", []))
            else:
                item[key] = getattr(it, key, None)
        rows.append(item)

    labels = [label_map.get(k, k) for k in selected_cols]

    return {
        "title": "Planes de Acción del Sistema de Gestión (Mejora)",
        "filename": "planes_accion_sgsi",
        "wide": True,
        "sections": [],
        "sheets": [{
            "name": "PlanesAccionSGSI",
            "title": "Planes de Acción del SGSI",
            "rows": rows,
            "cols": selected_cols,
            "labels": labels
        }]
    }


def _payload_dofa(company=""):
    dofa_id = request.args.get("dofa_id", type=int)

    if dofa_id:
        registros = [DofaAnalisis.query.get_or_404(dofa_id)]
    else:
        registros = DofaAnalisis.query.order_by(DofaAnalisis.id.desc()).all()

    sections = []

    for r in registros:
        subtitle_meta = f"{r.titulo or 'DOFA'}"
        meta_lines = [f"Fecha: {_fmt(r.fecha)}"]
        if getattr(r, "creado_por", None):
            meta_lines.append(f"Creado por: {r.creado_por}")

        sections.append({
            "render_mode": "dofa_cards",
            "subtitle": subtitle_meta,
            "paragraphs": meta_lines,
            "cards_2x2": [
                {"title": "✅ Fortalezas",      "text": r.fortalezas or "",      "bg": "#eaf7ef"},
                {"title": "🌟 Oportunidades",   "text": r.oportunidades or "",   "bg": "#eef5ff"},
                {"title": "⚠️ Debilidades",    "text": r.debilidades or "",     "bg": "#fff8e8"},
                {"title": "🛡️ Amenazas",       "text": r.amenazas or "",        "bg": "#fdeeee"},
            ],
            "strategy_cards": [
                {"title": "FO (Fortalezas + Oportunidades)",  "text": r.estrategias_fo or ""},
                {"title": "FA (Fortalezas + Amenazas)",       "text": r.estrategias_fa or ""},
                {"title": "DO (Debilidades + Oportunidades)", "text": r.estrategias_do or ""},
                {"title": "DA (Debilidades + Amenazas)",      "text": r.estrategias_da or ""},
            ],
            "page_break": False
        })

    return {
        "title": "DOFA",
        "filename": "dofa",
        "wide": True,
        "sections": sections if sections else [{
            "subtitle": "DOFA",
            "paragraphs": ["No hay registros disponibles."]
        }],
        "sheets": []
    }


def _payload_partes_interesadas(company=""):
    sel = session.get('partes_interesadas_cols') or list(DEFAULT_PARTES_INTERESADAS_COLS)
    label_map = _partes_label_map()

    selected_cols = [k for k in sel if k in label_map]
    if not selected_cols:
        selected_cols = list(DEFAULT_PARTES_INTERESADAS_COLS)

    items = ParteInteresada.query.order_by(ParteInteresada.parte_interesada.asc()).all()

    rows = []
    for it in items:
        item = {}
        for key in selected_cols:
            if key == "evidencias":
                item[key] = _join_evidence_names(getattr(it, "evidencias", []))
            else:
                item[key] = getattr(it, key, None)
        rows.append(item)

    labels = [label_map.get(k, k) for k in selected_cols]

    return {
        "title": "Partes Interesadas",
        "filename": "partes_interesadas",
        "wide": True,
        "sections": [],
        "sheets": [{
            "name": "PartesInteresadas",
            "title": "Partes Interesadas",
            "rows": rows,
            "cols": selected_cols,
            "labels": labels
        }]
    }


# ============================================================
# PAYLOADS - EXCEL GENÉRICO PARA LOS DEMÁS
# ============================================================

def _payload_excel_only_generic(key: str):
    key = (key or "").strip().lower()

    generic_map = {
        "objetivos": ("objetivos_sgsi", "Objetivos del SGSI"),
        "docs": ("doc_maestro_documentos", "Listado maestro de documentos"),
        "rev_accesos": ("revision_accesos", "Revisión de accesos"),
        "gestion_accesos": ("gestion_acceso", "Gestión de accesos"),
        "legales": ("requisitos_legales", "Requisitos legales"),
        "cambios": ("cambio_rfc_registro", "Gestión de cambios (RFC)"),
        "vuln": ("vulnerabilidades_registro", "Registro de vulnerabilidades"),
        "remediacion": ("planes_remediacion", "Plan de remediación"),
        "concientizacion": ("plan_cf_registros", "Plan de concientización"),
        "competencia": ("plan_remediacion_competencias", "Plan de competencia"),
        "proveedores": ("proveedor_evaluaciones", "Registro de proveedores"),
    }

    if key not in generic_map:
        return {
            "title": "Reporte",
            "filename": "reporte",
            "sheets": [{
                "name": "Reporte",
                "title": "Reporte no encontrado",
                "rows": [{"mensaje": f"El reporte '{key}' no está registrado."}],
                "cols": ["mensaje"],
                "labels": ["Mensaje"]
            }]
        }

    table_name, title = generic_map[key]
    rows = _sql_fetchall(f"SELECT * FROM {table_name} ORDER BY id DESC")
    cols = list(rows[0].keys()) if rows else ["id"]

    return {
        "title": title,
        "filename": key,
        "sheets": [{
            "name": "Datos",
            "title": title,
            "rows": rows[:1000],
            "cols": cols,
            "labels": cols
        }]
    }


# ============================================================
# INVENTARIOS DE ACTIVOS - REPORTES EXCEL
# ============================================================

_INVENTARIOS_EXCEL_TABLAS = {
    "inventario_software": ("inventario_software", "Inventario de Software", "Inventario de Software"),
    "inventario_informacion": ("inventario_informacion", "Inventario de Información", "Inventario de Información"),
    "inventario_datos_personales": ("inventario_datos_personales", "Inventario de Datos Personales", "Inventario de Datos Personales"),
    "inventario_fisico": ("inventario_fisico", "Inventario Físico", "Inventario Físico"),
}
_INVENTARIOS_EXCEL_PERMISOS = {
    key: nombre for key, (_, nombre, _) in _INVENTARIOS_EXCEL_TABLAS.items()
}
_INVENTARIOS_EXCEL_PERMISOS["inventario_ia"] = "Inventario de IA"


def _inventarios_excel_valor(v):
    """Evita que fórmulas inyectadas desde registros se ejecuten en Excel."""
    val = _fmt(v)
    if isinstance(val, str) and val.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + val
    return val


def _payload_inventarios_activos(key):
    if key == "inventario_ia":
        # Base independiente: no usar el SQLAlchemy principal para esta matriz.
        with _ai_inv_connection() as con:
            raw = [dict(r) for r in con.execute('SELECT * FROM sistemas_ia ORDER BY id').fetchall()]
        cols = ['codigo'] + list(_AI_INV_KEYS)
        labels = ['Código'] + [label for _, label, _, _ in _AI_INV_FIELDS]
        rows = [dict(codigo='IA-{:05d}'.format(r['id']), **{
            k: _inventarios_excel_valor(r.get(k)) for k in _AI_INV_KEYS
        }) for r in raw]
        nombre = 'Inventario de IA (ISO 42001)'
        filename = 'GRAC_Inventario_IA'
        sheet_name = 'Inventario IA'
    else:
        tabla, nombre, _ = _INVENTARIOS_EXCEL_TABLAS[key]
        # La tabla procede de una lista interna fija, nunca de entrada del usuario.
        rows = _sql_fetchall('SELECT * FROM "{}" ORDER BY id'.format(tabla))
        cols = list(rows[0].keys()) if rows else _table_columns(tabla)
        rows = [{k: _inventarios_excel_valor(r.get(k)) for k in cols} for r in rows]
        labels = list(cols)
        filename = 'GRAC_' + key
        sheet_name = 'Matriz'
    return {
        'title': nombre,
        'filename': filename,
        'sheets': [{
            'name': sheet_name,
            'title': nombre,
            'rows': rows, 'cols': cols, 'labels': labels,
        }],
    }


# ============================================================
# FÁBRICA CENTRAL DE PAYLOAD
# ============================================================

def _get_report_payload(key: str):
    key = (key or "").strip().lower()

    if key in _INVENTARIOS_EXCEL_PERMISOS:
        return _payload_inventarios_activos(key)

    if key == "soa":
        return _payload_soa()

    if key == "incidentes":
        return _payload_metricas_incidentes()

    if key == "metricas_riesgos":
        return _payload_metricas_riesgos()

    if key == "metricas_vuln":
        return _payload_metricas_vulnerabilidades()

    if key == "metricas_cultura":
        return _payload_metricas_cultura()

    if key == "metricas_mejora":
        return _payload_metricas_mejora()

    if key == "matriz_riesgos":
        return _payload_matriz_riesgos()

    if key == "registro_incidentes":
        return _payload_registro_incidentes()

    if key == "planes_respuesta_incidentes":
        return _ir_excel_payload()

    if key == "planes_accion_sgsi":
        return _payload_planes_accion_sgsi()

    if key == "dofa":
        return _payload_dofa()

    if key == "partes_interesadas":
        return _payload_partes_interesadas()

    return _payload_excel_only_generic(key)


# ============================================================
# PANTALLA PRINCIPAL
# ============================================================

@app.route("/reportes")
@login_required
def reportes_home():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and not verificar_permiso(user, "Reportes"):
        flash("No tiene permiso para acceder al módulo de reportes.", "danger")
        return redirect(url_for('menu'))

    company_input = (request.args.get("company") or "").strip()
    company = _resolve_company_name(company_input)

    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    catalogo_visible = [r for r in REPORT_CATALOG if (
        (r['key'] not in _INVENTARIOS_EXCEL_PERMISOS or
         verificar_permiso_activos(user, _INVENTARIOS_EXCEL_PERMISOS[r['key']]))
        and (r['key'] != 'planes_respuesta_incidentes' or verificar_permiso(user, 'Planes de Respuesta a Incidentes'))
    )]

    ir_categorias_reporte = []
    if any(r['key'] == 'planes_respuesta_incidentes' for r in catalogo_visible):
        _ir_init()
        with _ir_db() as ir_con:
            ir_categorias_reporte = [r['category'] for r in ir_con.execute(
                "SELECT DISTINCT category FROM ir_plans WHERE TRIM(category) <> '' ORDER BY category COLLATE NOCASE"
            )]

    content = render_template_string("""
    <div class="rep-shell">

      <div class="rep-header-card">
        <div class="rep-header-overlay">
          <div class="rep-header-text">
            <h3 class="rep-title m-0">Reportes del Sistema de Gestión</h3>
            <div class="rep-subtitle">
              La declaración de aplicabilidad, métricas y DOFA se exportan en PDF / Word.
              Matriz de riesgos, registro de incidentes, planes de acción y partes interesadas se exportan en Excel.
            </div>
          </div>
        </div>
      </div>

      <div class="rep-header-actions">
        
      </div>

      <div class="rep-card p-4 mb-3">
        <div class="rep-section-title">
          Filtros de generación
        </div>

        <form method="GET" action="{{ url_for('reportes_home') }}">
          <div class="row g-3 align-items-end">

            <div class="col-md-4">
              <label class="form-label fw-semibold">Empresa</label>
              <input class="form-control"
                     name="company"
                     value="{{ company }}"
                     placeholder="Nombre empresa">
            </div>

            <div class="col-md-3">
              <label class="form-label fw-semibold">Desde</label>
              <input type="date"
                     class="form-control"
                     name="start_date"
                     value="{{ start_date }}">
            </div>

            <div class="col-md-3">
              <label class="form-label fw-semibold">Hasta</label>
              <input type="date"
                     class="form-control"
                     name="end_date"
                     value="{{ end_date }}">
            </div>

            <div class="col-md-2 d-flex gap-2">
              <button class="btn btn-primary rounded-pill px-3 w-100" type="submit">
                Aplicar
              </button>
              <a class="btn btn-outline-secondary rounded-pill px-3 w-100"
                 href="{{ url_for('reportes_home') }}">
                Limpiar
              </a>
            </div>

          </div>
        </form>
      </div>

      <div class="row g-3">
        {% for r in catalog %}
          {% set allow_pdf_word = r.key in pdf_word_allowed %}
          {% set allow_excel_only = r.key in excel_only_allowed %}
          <div class="col-xl-4 col-lg-4 col-md-6 col-sm-12">
            <div class="rep-report-card h-100">
              <div class="rep-report-card-body d-flex flex-column h-100">

                <div class="rep-report-top">
                  <div class="rep-report-icon">
                    <i class="bi {{ r.icon }}"></i>
                  </div>

                  <div class="rep-report-head-text">
                    <div class="rep-report-title">{{ r.label }}</div>

                    <div class="rep-report-desc">
                      {% if r.key == 'soa' %}
                        Reporte formal de la declaración de aplicabilidad del SGSI.
                      {% elif r.key == 'incidentes' %}
                        Presentación basada en el submódulo de métricas de incidentes.
                      {% elif r.key == 'metricas_riesgos' %}
                        Presentación basada en el submódulo de métricas de riesgos.
                      {% elif r.key == 'metricas_vuln' %}
                        Presentación basada en el submódulo de métricas de vulnerabilidades.
                      {% elif r.key == 'metricas_cultura' %}
                        Presentación basada en el submódulo de métricas de cultura.
                      {% elif r.key == 'metricas_mejora' %}
                        Presentación basada en el submódulo de métricas de planes de mejora.
                      {% elif r.key == 'dofa' %}
                        Exportación con estructura visual del módulo Ver DOFA.
                      {% elif r.key == 'matriz_riesgos' %}
                        Exportación de la matriz de riesgos en Excel.
                      {% elif r.key == 'registro_incidentes' %}
                        Exportación del registro de incidentes en Excel.
                      {% elif r.key == 'planes_respuesta_incidentes' %}
                        Catálogo y ejecuciones en Excel; plan operativo por categoría con diagrama de flujo para imprimir.
                      {% elif r.key == 'planes_accion_sgsi' %}
                        Exportación de planes de acción del sistema de gestión en Excel.
                      {% elif r.key == 'partes_interesadas' %}
                        Exportación de partes interesadas en Excel.
                      {% elif r.key == 'inventario_ia' %}
                        Matriz de inteligencia artificial, basada en ISO/IEC 42001, en Excel.
                      {% else %}
                        Disponible únicamente para exportación en Excel.
                      {% endif %}
                    </div>
                  </div>
                </div>

                <div class="rep-report-meta mt-3">
                  <div class="small text-muted">
                    Formatos disponibles:
                  </div>
                  <div class="d-flex gap-2 flex-wrap mt-2">
                    {% if allow_pdf_word %}
                      <span class="rep-chip rep-chip-pdf">PDF</span>
                      <span class="rep-chip rep-chip-word">WORD</span>
                    {% endif %}
                    {% if allow_excel_only %}
                      <span class="rep-chip rep-chip-excel">EXCEL</span>
                    {% endif %}
                  </div>
                </div>

                {% if r.key == 'planes_respuesta_incidentes' %}
                <form method="get" action="{{ url_for('ir_category_report_pdf') }}"
                      target="_blank" class="mt-3 no-progress"
                      data-no-progress="true" aria-label="Imprimir plan de respuesta por categoría">
                  <input type="hidden" name="company" value="{{ company }}">
                  <label class="form-label fw-semibold small" for="ir-report-category">Categoría del incidente</label>
                  <select id="ir-report-category" class="form-select form-select-sm mb-2" name="categoria" required>
                    <option value="__todas__">Todas las categorías</option>
                    {% for categoria in ir_categorias_reporte %}
                    <option value="{{ categoria }}">{{ categoria }}</option>
                    {% endfor %}
                  </select>
                  <button type="submit" class="btn btn-primary btn-sm w-100 no-progress"
                          data-no-progress="true">
                    <i class="bi bi-diagram-3 me-1"></i> Imprimir plan y diagrama (PDF)
                  </button>
                  <div class="form-text">Incluye la versión vigente o borrador, fases, actividades e instrucciones.</div>
                </form>
                {% endif %}
                <div class="rep-report-actions mt-auto pt-3 d-flex gap-2 flex-wrap">
                  {% if allow_pdf_word %}
                    <a class="btn btn-primary btn-sm rounded-pill px-3"
                       target="_blank"
                       href="{{ url_for('reportes_pdf', key=r.key, company=company, start_date=start_date, end_date=end_date, year=request.args.get('year', ''), month=request.args.get('month', ''), ver=request.args.get('ver', ''), campo=request.args.get('campo', ''), filtro=request.args.get('filtro', ''), dofa_id=request.args.get('dofa_id', '')) }}"
                       onclick="showLoader(); setTimeout(hideLoader, 1200);">
                      <i class="bi bi-printer me-1"></i> Imprimir PDF
                    </a>

                    <a class="btn btn-success btn-sm rounded-pill px-3"
                       href="{{ url_for('reportes_docx', key=r.key, company=company, start_date=start_date, end_date=end_date, year=request.args.get('year', ''), month=request.args.get('month', ''), ver=request.args.get('ver', ''), campo=request.args.get('campo', ''), filtro=request.args.get('filtro', ''), dofa_id=request.args.get('dofa_id', '')) }}"
                       onclick="showLoader(); window.open(this.href, '_blank', 'noopener'); setTimeout(hideLoader, 1200); return false;">
                      <i class="bi bi-file-earmark-word me-1"></i> Descargar Word
                    </a>
                  {% endif %}

                  {% if allow_excel_only %}
                    <a class="btn btn-outline-success btn-sm rounded-pill px-3"
                       href="{{ url_for('reportes_excel', key=r.key, company=company, start_date=start_date, end_date=end_date, year=request.args.get('year', ''), month=request.args.get('month', ''), ver=request.args.get('ver', ''), campo=request.args.get('campo', ''), filtro=request.args.get('filtro', ''), dofa_id=request.args.get('dofa_id', '')) }}"
                       onclick="showLoader(); window.open(this.href, '_blank', 'noopener'); setTimeout(hideLoader, 1200); return false;">
                      <i class="bi bi-file-earmark-excel me-1"></i> Descargar Excel
                    </a>
                  {% endif %}
                </div>

              </div>
            </div>
          </div>
        {% endfor %}
      </div>

    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .rep-shell{
        width:96%;
        max-width:1350px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .rep-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }

      .rep-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rep-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .rep-header-overlay::before{
        content:"📊";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .rep-header-text{
        max-width:1000px;
        min-width:0;
      }

      .rep-header-text::before{
        content:"SGSI · Centro de Reportes";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .rep-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .rep-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .rep-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .rep-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rep-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .rep-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .rep-card .card-body{
        padding:22px;
        overflow:hidden;
      }

      .rep-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      /* =========================
         FILTROS / BOTÓN LIMPIAR FIX
         ========================= */
      .rep-card form,
      .rep-filter-form{
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .rep-card form .row{
        width:100%;
        max-width:100%;
        margin-left:0 !important;
        margin-right:0 !important;
        align-items:end;
      }

      .rep-card form [class*="col-"]{
        min-width:0;
      }

      .rep-card form .col-auto,
      .rep-card form .col-md-auto,
      .rep-card form .col-lg-auto{
        max-width:100%;
      }

      .rep-filter-actions,
      .rep-card form .rep-filter-actions{
        display:flex;
        flex-wrap:wrap;
        gap:6px;
        align-items:center;
        justify-content:flex-start;
        width:100%;
        max-width:100%;
        min-width:0;
      }

      .rep-filter-actions .btn,
      .rep-card form button,
      .rep-card form a.btn,
      .rep-card form input[type="submit"],
      .rep-card form input[type="reset"]{
        white-space:nowrap;
        flex-shrink:0;
        max-width:100%;
      }

      .rep-card form .btn{
        margin-bottom:0;
      }

      .rep-report-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.14);
        border:1px solid rgba(219,230,244,.9);
        transition:all .22s ease;
        overflow:hidden;
        width:100%;
        max-width:100%;
        height:100%;
      }

      .rep-report-card:hover{
        transform:translateY(-5px);
        box-shadow:0 16px 30px rgba(15,23,42,.22);
      }

      .rep-report-card-body{
        padding:20px;
      }

      .rep-report-top{
        display:flex;
        align-items:flex-start;
        gap:14px;
        min-width:0;
      }

      .rep-report-icon{
        min-width:52px;
        width:52px;
        height:52px;
        border-radius:14px;
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        display:flex;
        align-items:center;
        justify-content:center;
        color:#ffffff;
        font-size:1.3rem;
        box-shadow:0 8px 18px rgba(20,89,166,.28);
        flex-shrink:0;
      }

      .rep-report-head-text{
        flex:1;
        min-width:0;
      }

      .rep-report-title{
        font-weight:950;
        font-size:1.03rem;
        color:#0b4a8f;
        line-height:1.25;
        margin-bottom:6px;
        overflow-wrap:break-word;
      }

      .rep-report-desc{
        font-size:.78rem;
        color:#475569;
        line-height:1.45;
        min-height:58px;
        overflow-wrap:break-word;
      }

      .rep-report-meta{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px 14px;
        overflow:hidden;
      }

      .rep-chip{
        display:inline-flex;
        align-items:center;
        justify-content:center;
        padding:4px 10px;
        border-radius:999px;
        font-size:.75rem;
        font-weight:900;
        letter-spacing:.3px;
        max-width:100%;
        white-space:normal;
        text-align:center;
      }

      .rep-chip-pdf{
        background:#fee2e2;
        color:#991b1b;
        border:1px solid #fecaca;
      }

      .rep-chip-word{
        background:#dcfce7;
        color:#166534;
        border:1px solid #bbf7d0;
      }

      .rep-chip-excel{
        background:#dbeafe;
        color:#1d4ed8;
        border:1px solid #bfdbfe;
      }

      .rep-report-actions{
        display:flex;
        flex-wrap:wrap;
        gap:6px;
      }

      .rep-report-actions .btn{
        min-width:145px;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        max-width:100%;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .rep-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rep-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .rep-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .rep-report-desc{
          min-height:auto;
        }

        .rep-card .card-body{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .rep-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rep-header-overlay::before{
          margin:0;
        }

        .rep-title,
        .rep-subtitle{
          text-align:center;
        }

        .rep-header-actions .btn,
        .rep-report-actions .btn,
        .rep-filter-actions .btn,
        .rep-card form button,
        .rep-card form a.btn,
        .rep-card form input[type="submit"],
        .rep-card form input[type="reset"]{
          width:100%;
        }

        .rep-report-top{
          flex-direction:column;
          align-items:center;
          text-align:center;
        }
      }
    </style>
    """,
    catalog=catalogo_visible,
    pdf_word_allowed=REPORT_KEYS_PDF_WORD,
    excel_only_allowed=REPORT_KEYS_EXCEL_ONLY,
    ir_categorias_reporte=ir_categorias_reporte,
    company=company,
    start_date=start_date,
    end_date=end_date,
    request=request
    )

    return render_template_string(BASE, content=content)


# ============================================================
# RUTA PDF
# ============================================================

@app.route("/reportes/pdf/<key>")
@login_required
def reportes_pdf(key):
    key = (key or "").strip().lower()

    if key not in REPORT_KEYS_PDF_WORD:
        flash("Este reporte no está disponible en PDF.", "warning")
        return redirect(url_for("reportes_home"))

    company = (request.args.get("company") or "").strip()
    payload = _get_report_payload(key)

    pdf_bytes = _build_pdf(
        title=payload["title"],
        sections=payload["sections"],
        company_name=company,
        wide=payload.get("wide", False)
    )

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={payload.get('filename', 'reporte')}.pdf"}
    )


# ============================================================
# RUTA DOCX
# ============================================================

@app.route("/reportes/docx/<key>")
@login_required
def reportes_docx(key):
    key = (key or "").strip().lower()

    if key not in REPORT_KEYS_PDF_WORD:
        flash("Este reporte no está disponible en Word.", "warning")
        return redirect(url_for("reportes_home"))

    company = (request.args.get("company") or "").strip()
    payload = _get_report_payload(key)

    docx_bytes = _build_docx(
        title=payload["title"],
        sections=payload["sections"],
        company_name=company
    )

    return Response(
        docx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={payload.get('filename', 'reporte')}.docx"}
    )


# ============================================================
# RUTA EXCEL
# ============================================================

@app.route("/reportes/excel/<key>")
@login_required
def reportes_excel(key):
    key = (key or "").strip().lower()

    if key not in REPORT_KEYS_EXCEL_ONLY:
        flash("Este reporte no está disponible en Excel.", "warning")
        return redirect(url_for("reportes_home"))

    usuario = db.session.get(User, session.get('user_id'))
    if usuario is None or (usuario.role != 'admin' and not verificar_permiso(usuario, 'Reportes')):
        abort(403, description='Sin acceso al Centro de Reportes.')
    if key == 'planes_respuesta_incidentes' and not verificar_permiso(usuario, 'Planes de Respuesta a Incidentes'):
        abort(403, description='Sin permiso para exportar planes de respuesta.')
    permiso_inventario = _INVENTARIOS_EXCEL_PERMISOS.get(key)
    if permiso_inventario and not verificar_permiso_activos(usuario, permiso_inventario):
        abort(403, description='Sin permiso para exportar este inventario.')

    company = (request.args.get("company") or "").strip()
    payload = _get_report_payload(key)

    xlsx_bytes = _build_excel(
        filename=payload.get("filename", "reporte"),
        sheets=payload.get("sheets", []),
        company_name=company
    )

    return Response(
        xlsx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={payload.get('filename', 'reporte')}.xlsx"}
    )


# ============================================================================================================================================
#                                                   FIN MÓDULO REPORTES (PDF / WORD / EXCEL)
# ============================================================================================================================================


# ==========================================================================================================================================
#                                                               Módulo NIST
# ==========================================================================================================================================

# =====================================================================
#                 MÓDULO NIVEL DE MADUREZ NIST CSF 2.0 vs ISO 27001
# =====================================================================

class NistAnalysisRun(db.Model):
    __tablename__ = "nist_analysis_runs"

    id = db.Column(db.Integer, primary_key=True)
    iso_analysis_id = db.Column(
        db.Integer,
        db.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False
    )

    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    nivel_promedio_general = db.Column(db.Float)

    # JSON con resultados por función
    resultados_json = db.Column(db.Text)  # Guarda estructura completa

    iso_analysis = db.relationship("AnalysisRun", backref="nist_runs")



@app.route("/nist_madurez")
@login_required
def nist_madurez():

    runs = NistAnalysisRun.query.order_by(
        NistAnalysisRun.fecha_calculo.desc()
    ).all()

    html = render_template_string("""
    <div class="menu-wrap">

        <div class="plan-hero">
            <h2 class="plan-title">🛡️ Nivel de Madurez NIST CSF 2.0</h2>
        </div>

        <div class="volver-center">
            <a href="{{ url_for('menu') }}"
               class="btn btn-light rounded-pill px-4 shadow-sm">
               ⬅ Volver al menú
            </a>
        </div>

        <div class="container mt-4">

            <h4>📚 Historial de Revisiones</h4>

            <table class="table table-striped mt-3">
                <thead class="table-dark">
                    <tr>
                        <th>Fecha</th>
                        <th>Nivel Promedio General</th>
                        <th>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in runs %}
                    <tr>
                        <td>{{ r.fecha_calculo.strftime('%Y-%m-%d') }}</td>
                        <td><strong>{{ r.nivel_promedio_general }}</strong></td>
                        <td>
                            <a href="{{ url_for('ver_nist_detalle', run_id=r.id) }}"
                               class="btn btn-primary btn-sm">
                               Ver detalle
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

        </div>
    </div>
    """)

    return html

@app.route("/nist_madurez/<int:run_id>")
@login_required
def ver_nist_detalle(run_id):

    run = NistAnalysisRun.query.get_or_404(run_id)
    resultados = json.loads(run.resultados_json)

    # ==========================
    # ✅ RADAR NIST (AQUÍ VA)
    # ==========================
    labels = ["Govern", "Identify", "Protect", "Detect", "Respond", "Recover"]

    values = []
    for f in labels:
        cats = resultados.get(f, {})  # {"GV.OC": 2.5, ...}
        if cats:
            values.append(round(sum(cats.values()) / len(cats), 2))
        else:
            values.append(0)

    radar_nist_b64 = make_radar_base64(labels, values, title="Araña Consolidada – NIST CSF 2.0")

    return render_template_string("""
    <div class="container mt-4">
        <h3>Detalle NIST CSF 2.0</h3>
        <h5>Nivel General: {{ run.nivel_promedio_general }}</h5>

        {% for funcion, categorias in resultados.items() %}
            <div class="card mt-3 shadow-sm">
                <div class="card-header bg-dark text-white">
                    {{ funcion }}
                </div>
                <div class="card-body">
                    <ul>
                        {% for cat, nivel in categorias.items() %}
                            <li><strong>{{ cat }}</strong>: {{ nivel }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        {% endfor %}

        <div class="card mt-3 shadow-sm">
          <div class="card-header bg-dark text-white">📈 Radar NIST CSF 2.0</div>
          <div class="card-body text-center">
            <img src="data:image/png;base64,{{ radar_nist_b64 }}" class="img-fluid" style="max-width: 900px;">
          </div>
        </div>

        <a href="{{ url_for('nist_madurez') }}"
           class="btn btn-secondary mt-3">
           ⬅ Volver
        </a>
    </div>
    """, run=run, resultados=resultados, radar_nist_b64=radar_nist_b64)



def _nist_group_questions():
    """
    Retorna estructura:
    {
      "GOVERN": {
         "GV.OC": {"categoria": "...", "items":[(pregunta), ...]},
         ...
      },
      ...
    }
    """
    qs = NistMadurezPregunta.query.filter_by(activo=True).order_by(
        NistMadurezPregunta.orden.asc()
    ).all()

    data = {}
    for q in qs:
        f = (q.funcion or "OTROS").upper()
        ccode = (q.categoria_codigo or "SIN_CATEGORIA").upper()
        data.setdefault(f, {})
        data[f].setdefault(ccode, {"categoria": q.categoria or "", "items": []})
        data[f][ccode]["items"].append(q)

    # ordena funciones
    ordered = {}
    for f in NIST_FUNC_ORDER:
        if f in data:
            ordered[f] = data[f]
    # añade las que no estén en el orden
    for f in data:
        if f not in ordered:
            ordered[f] = data[f]
    return ordered


# ==========================================================================================================================================
#                                                       Módulo Nivel de Madurez — NIST CSF 2.0
# ==========================================================================================================================================

# ==============================
# MODELOS - MADUREZ NIST CSF 2.0
# ==============================

class NistMadurezPregunta(db.Model):
    __tablename__ = "nist_madurez_pregunta"

    id = db.Column(db.Integer, primary_key=True)

    # Estructura NIST
    funcion = db.Column(db.String(40), nullable=False)        # "GOVERN", ...
    funcion_codigo = db.Column(db.String(20), nullable=True)  # "GV"
    categoria = db.Column(db.String(140), nullable=True)      # "Organizational Context"
    categoria_codigo = db.Column(db.String(30), nullable=True) # "GV.OC"

    orden = db.Column(db.Integer, nullable=False, default=0)

    # Pregunta
    pregunta_en = db.Column(db.Text, nullable=False)
    pregunta_es = db.Column(db.Text, nullable=True)  # se llenará al importar (traducción)

    activo = db.Column(db.Boolean, default=True)


class NistMadurezRun(db.Model):
    __tablename__ = "nist_madurez_runs"

    id = db.Column(db.Integer, primary_key=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    consecutivo = db.Column(db.String(255), nullable=False, index=True)

    # NUEVOS
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)  # BORRADOR / FINALIZADO
    progreso_pct = db.Column(db.Integer, nullable=False, default=0)

    # Resultados
    resumen_json = db.Column(db.Text, nullable=False, default="{}")
    pct_general = db.Column(db.Float, nullable=False, default=0.0)
    radar_overall_b64 = db.Column(db.Text, nullable=True)

    # INFORME EJECUTIVO
    informe_ejecutivo_ai = db.Column(db.Text, nullable=True)
    informe_ejecutivo_editado = db.Column(db.Text, nullable=True)
    plan_trabajo_ai = db.Column(db.Text, nullable=True)
    plan_trabajo_editado = db.Column(db.Text, nullable=True)


class NistMadurezRespuesta(db.Model):
    __tablename__ = "nist_madurez_respuesta"

    id = db.Column(db.Integer, primary_key=True)

    run_id = db.Column(db.Integer, db.ForeignKey("nist_madurez_runs.id"), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("nist_madurez_pregunta.id"), nullable=False)

    estado = db.Column(db.String(20), nullable=False)  # "SI" | "PARCIAL" | "NO" | "NA"
    comentario = db.Column(db.Text, nullable=True)

    run = db.relationship("NistMadurezRun", backref=db.backref("respuestas", cascade="all, delete-orphan"))
    pregunta = db.relationship("NistMadurezPregunta")

class NistMadurezCategoriaAnalisis(db.Model):
    __tablename__ = "nist_madurez_categoria_analisis"

    id = db.Column(db.Integer, primary_key=True)

    run_id = db.Column(db.Integer, db.ForeignKey("nist_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    funcion = db.Column(db.String(40), nullable=False, index=True)          # GOV, ID, PR, DE, RS, RC (o el nombre que uses)
    categoria_codigo = db.Column(db.String(40), nullable=False, index=True) # GV.OC, ID.AM, etc.

    # Campos del análisis
    estado_actual = db.Column(db.Text, nullable=True)
    estado_requerido = db.Column(db.Text, nullable=True)
    plan_accion_ai = db.Column(db.Text, nullable=True)       # lo que devuelve la IA
    plan_accion_editado = db.Column(db.Text, nullable=True)  # lo que edita el usuario (si quiere)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("run_id", "funcion", "categoria_codigo", name="uq_nist_run_func_cat"),
    )

class SystemSecret(db.Model):
    __tablename__ = "system_secrets"
    id = db.Column(db.Integer, primary_key=True)
    key_name = db.Column(db.String(120), unique=True, nullable=False)
    value_enc = db.Column(db.Text, nullable=False)  # token Fernet (texto)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


NIST_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Ejecutado (Performed)",
        "descripcion": "La organización puede llevar a cabo prácticas de seguridad de manera ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas ad hoc"
    },
    {
        "nivel": "Nivel 2: Documentado (Documented)",
        "descripcion": "La organización ha establecido y documentado prácticas relacionadas con los requisitos de seguridad. Esta documentación permite que la organización las ejecute de manera repetible y logre los resultados esperados.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Existe documentación"
    },
    {
        "nivel": "Nivel 3: Gestionado (Managed)",
        "descripcion": "La organización revisa el cumplimiento de las políticas y proporciona recursos adecuados para implementar y mantener los requisitos de seguridad.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Se revisa cumplimiento"
    },
    {
        "nivel": "Nivel 4: Gestionado Cuantitativamente (Quantitatively Managed)",
        "descripcion": "La organización revisa y mide la efectividad de las prácticas. Se toman acciones correctivas cuando es necesario, y la alta dirección es informada periódicamente sobre el estado o los problemas identificados.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Se mide efectividad"
    },
    {
        "nivel": "Nivel 5: Optimizado (Optimizing)",
        "descripcion": "La organización ha estandarizado y optimizado la implementación de procesos en toda la organización. Además, comunica y comparte información de mejora de manera transversal.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua institucionalizada"
    },
]

# =========================================================
# PUNTAJE DE RESPUESTAS NIST
# =========================================================
# Escala 0..1 para luego convertir a porcentaje multiplicando por 100

NIST_STATUS_SCORE = {
    "SI": 1.0,
    "PARCIAL": 0.5,
    "NO": 0.0,
    "NA": None,   # N/A no suma ni resta; se excluye del cálculo
}

# =========================================================
# HELPERS NIST
# =========================================================

def _normalizar_texto(v):
    return (v or "").replace("\r\n", "\n").replace("\r", "\n").strip()

def _nist_limpiar_texto_rico_guardado(texto: str) -> str:
    """
    Limpia respuestas IA guardadas en NIST:
    - quita JSON envolvente si viene {"informe_ejecutivo": "..."}
    - quita fences ```json
    - convierte <br> a saltos reales
    - elimina tags HTML como <b>
    - elimina títulos generados por Ollama como **INFORME EJECUTIVO**
    """
    txt = (texto or "").strip()
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Si viene como JSON, extraer informe_ejecutivo
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            val = (obj.get("informe_ejecutivo") or "").strip()
            if val:
                txt = val
    except Exception:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(txt[start:end+1])
                if isinstance(obj, dict):
                    val = (obj.get("informe_ejecutivo") or "").strip()
                    if val:
                        txt = val
        except Exception:
            pass

    txt = html.unescape(txt)
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    # Quitar llaves sueltas si quedaron por JSON mal guardado
    txt = re.sub(r'^\s*\{\s*"?informe_ejecutivo"?\s*:\s*"?', "", txt, flags=re.IGNORECASE)
    txt = re.sub(r'"?\s*\}\s*$', "", txt)

    # Quitar títulos que Ollama suele agregar
    patrones_titulos = [
        r"^\s*\*{1,3}\s*INFORME\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*RESUMEN\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
    ]

    for patron in patrones_titulos:
        txt = re.sub(patron, "", txt, flags=re.IGNORECASE).strip()

    # Quitar markdown residual
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()

def _contar_respuestas_run_nist(run_id: int) -> int:
    if not run_id:
        return 0
    return NistMadurezRespuesta.query.filter_by(run_id=run_id).count()

def _eliminar_runs_vacios_nist(user_id: int | None = None):
    """
    Limpia runs que quedaron creados sin respuestas.
    """
    q = NistMadurezRun.query
    if user_id:
        q = q.filter(NistMadurezRun.user_id == user_id)

    runs = q.all()
    eliminados = 0

    for run in runs:
        total_resp = NistMadurezRespuesta.query.filter_by(run_id=run.id).count()
        if total_resp == 0:
            NistMadurezCategoriaAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
            db.session.delete(run)
            eliminados += 1

    if eliminados:
        db.session.commit()

    return eliminados

def _build_plan_accion_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""

    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = _normalizar_texto(it.get("accion"))
        prioridad = _normalizar_texto(it.get("prioridad"))
        responsable = _normalizar_texto(it.get("responsable_sugerido"))
        plazo = _normalizar_texto(it.get("plazo"))
        evidencia = _normalizar_texto(it.get("evidencia_esperada"))

        bloque = (
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )
        lines.append(bloque)

    return "\n\n".join(lines).strip()

def _normalizar_plan_accion_nist_texto(texto_raw: str) -> str:
    """
    Convierte JSON crudo del análisis NIST a texto legible.
    Si ya viene como texto, lo devuelve igual.
    """
    txt = (texto_raw or "").strip()
    if not txt:
        return ""

    # Quitar fences tipo ```json ... ```
    txt = txt.replace("```json", "").replace("```", "").strip()

    obj = _extraer_json_objeto(txt)

    if isinstance(obj, dict):
        estado_actual = _normalizar_texto(obj.get("estado_actual") or "")
        estado_requerido = _normalizar_texto(obj.get("estado_requerido") or "")

        plan_list = None
        if isinstance(obj.get("plan_accion"), list):
            plan_list = obj.get("plan_accion")
        elif isinstance(obj.get("plan"), list):
            plan_list = obj.get("plan")
        elif isinstance(obj.get("acciones"), list):
            plan_list = obj.get("acciones")

        plan_txt = _build_plan_accion_texto(plan_list or [])

        # PRIORIDAD: mostrar SOLO el plan convertido si existe
        if plan_txt:
            return plan_txt.strip()

        # Si no hay lista, mostrar bloques útiles
        bloques = []
        if estado_actual:
            bloques.append(f"Estado actual:\n{estado_actual}")
        if estado_requerido:
            bloques.append(f"Estado requerido:\n{estado_requerido}")

        if bloques:
            return "\n\n".join(bloques).strip()

    return txt


def _extraer_json_objeto(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}

    # quitar fences tipo ```json ... ```
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return {}


def calcular_progreso_nist(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        estado = ""
        if form_data is not None:
            estado = (form_data.get(f"st_{q.id}") or "").strip().upper()
        elif respuestas_db is not None:
            estado = (respuestas_db.get(q.id, {}).get("estado") or "").strip().upper()

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, pct


def obtener_borrador_nist(user_id):
    if not user_id:
        return None

    return (
        NistMadurezRun.query
        .filter(
            NistMadurezRun.user_id == user_id,
            NistMadurezRun.estado == "BORRADOR"
        )
        .order_by(NistMadurezRun.updated_at.desc(), NistMadurezRun.id.desc())
        .first()
    )


def cargar_respuestas_nist(run_id):
    out = {}
    if not run_id:
        return out

    rows = NistMadurezRespuesta.query.filter_by(run_id=run_id).all()
    for r in rows:
        out[r.pregunta_id] = {
            "estado": (r.estado or "").strip().upper(),
            "comentario": (r.comentario or "").strip()
        }
    return out

def _parse_rango_pct(rango: str):
    # "0% – 20%" -> (0.0, 20.0)
    if not rango:
        return None, None
    s = rango.replace("%", "").strip().replace("–", "-")
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None

def nist_nivel_visual_por_pct(pct: float):
    """
    Devuelve:
    {
        "nivel": "Nivel 4: ...",
        "score": 4,
        "color": "#0d6efd"
    }
    """
    try:
        p = float(pct)
    except Exception:
        p = 0.0

    if p < 0:
        p = 0.0
    if p > 100:
        p = 100.0

    for lvl in NIST_MADUREZ_LEVELS:
        lo, hi = _parse_rango_pct(lvl.get("rango_pct", ""))
        if lo is None or hi is None:
            continue
        if lo <= p <= hi:
            score = lvl.get("score", 0)

            # Colores por nivel
            color_map = {
                1: "#dc3545",  # rojo
                2: "#fd7e14",  # naranja
                3: "#ffc107",  # amarillo
                4: "#0d6efd",  # azul
                5: "#198754",  # verde
            }

            return {
                "nivel": lvl.get("nivel", ""),
                "score": score,
                "color": color_map.get(score, "#6c757d")
            }

    return {
        "nivel": "Nivel no definido",
        "score": 0,
        "color": "#6c757d"
    }

def nist_pct_por_funcion(resumen: dict, func_order: list[str]):
    """
    resumen: run.resumen_json (dict) con estructura:
      { "GOVERN": { "GV.OC": {"pct": 55.2, "total": 10, ...}, ... }, ... }

    Retorna: (labels, values)
      labels: ["GOVERN", "IDENTIFY", ...]
      values: [pct_func, pct_func, ...] 0..100
    """
    labels = []
    values = []

    for func in func_order:
        cats = (resumen or {}).get(func, {}) or {}
        if not cats:
            labels.append(func)
            values.append(0.0)
            continue

        # Promedio ponderado por "total" (items) de cada categoría
        w_sum = 0.0
        w_cnt = 0.0
        for _cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            total = float(d.get("total", 0) or 0)
            if total <= 0:
                continue
            w_sum += pct * total
            w_cnt += total

        pct_func = round((w_sum / w_cnt) if w_cnt else 0.0, 2)

        labels.append(func)
        values.append(pct_func)

    return labels, values


def nist_radar_b64(labels: list[str], values: list[float], title: str = "Radar NIST CSF 2.0"):
    """
    Genera PNG base64 (sin guardar archivo).
    values debe venir en escala 0..100.
    """
    if not labels:
        return ""

    vals = [max(0.0, min(100.0, float(v))) for v in values]
    N = len(labels)

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    # MÁS PEQUEÑO
    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7.3)
    ax.tick_params(axis="x", pad=10)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.tick_params(axis="y", pad=4)

    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)

    ax.set_title(title, fontsize=9.5, pad=14)

    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        transparent=True,
        bbox_inches="tight",
        pad_inches=0.22
    )
    plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode("utf-8")

def _nist_build_pdf_run(run: "NistMadurezRun") -> io.BytesIO:
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
    radar_b64 = nist_radar_b64(
        radar_labels,
        radar_values,
        title="Radar por Función - NIST CSF 2.0"
    )

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="NIST CSF 2.0 - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="SGSI_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SGSI_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SGSI_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="SGSI_Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4
    ))

    def pdf_escape(v):
        return html.escape(str(v or ""))

    def nivel_color(pct):
        try:
            pct = float(pct or 0)
        except Exception:
            pct = 0

        if pct >= 81:
            return colors.HexColor("#198754")
        if pct >= 61:
            return colors.HexColor("#0d6efd")
        if pct >= 41:
            return colors.HexColor("#ffc107")
        if pct >= 21:
            return colors.HexColor("#fd7e14")
        return colors.HexColor("#dc3545")

    def nivel_nombre_corto(nivel_txt):
        txt = str(nivel_txt or "")
        if ":" in txt:
            txt = txt.split(":", 1)[1].strip()
        if "(" in txt:
            txt = txt.split("(", 1)[0].strip()
        return txt or "No definido"

    def nivel_badge_pdf(pct, nivel_data):
        c = nivel_color(pct)
        score = nivel_data.get("score", 0)
        nombre = nivel_nombre_corto(nivel_data.get("nivel", ""))

        badge = Table(
            [[
                "",
                Paragraph(
                    f"<b>Nivel {score}</b> - {pdf_escape(nombre)}",
                    styles["SGSI_Small"]
                )
            ]],
            colWidths=[0.28 * cm, 4.25 * cm]
        )

        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), c),
            ("BOX", (0, 0), (0, 0), 0.25, c),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        return badge

    def add_section(title):
        table = Table(
            [[Paragraph(pdf_escape(title), styles["SGSI_Title"])]],
            colWidths=[26.8 * cm]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def add_text_block(texto):
        texto = _nist_limpiar_texto_rico_guardado(texto or "")
        if not texto:
            story.append(Paragraph("No hay información registrada.", styles["SGSI_Normal"]))
            return

        for parrafo in re.split(r"\n\s*\n", texto):
            parrafo = parrafo.strip()
            if parrafo:
                story.append(Paragraph(pdf_escape(parrafo), styles["SGSI_Normal"]))

    story = []

    # =========================
    # ENCABEZADO
    # =========================
    add_section("NIST CSF 2.0 - Informe de Madurez")

    nivel_general = nist_nivel_visual_por_pct(run.pct_general)
    nivel_nombre = nivel_nombre_corto(nivel_general.get("nivel", ""))

    resumen_tbl = Table([
        ["Consecutivo", pdf_escape(run.consecutivo)],
        ["Fecha", run.created_at.strftime("%Y-%m-%d %H:%M")],
        [
            "Cumplimiento general",
            f"{run.pct_general:.2f}% - Nivel {nivel_general.get('score', 0)} ({pdf_escape(nivel_nombre)})"
        ],
        ["Nivel de madurez", pdf_escape(nivel_general.get("nivel", ""))]
    ], colWidths=[5.2 * cm, 21.6 * cm])

    resumen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(resumen_tbl)
    story.append(Spacer(1, 12))

    # =========================
    # INFORME EJECUTIVO
    # =========================
    story.append(Paragraph("Informe Ejecutivo", styles["SGSI_Section"]))

    informe_exec = (
        run.informe_ejecutivo_editado
        or run.informe_ejecutivo_ai
        or ""
    ).strip()

    add_text_block(informe_exec)
    story.append(Spacer(1, 10))

    # =========================
    # RADAR / ARAÑA
    # =========================
    story.append(Paragraph("Radar por Función NIST CSF 2.0", styles["SGSI_Section"]))

    if radar_b64:
        try:
            radar_png = base64.b64decode(radar_b64)
            img_buf = io.BytesIO(radar_png)
            img = RLImage(img_buf, width=11.5 * cm, height=11.0 * cm)
            story.append(img)
            story.append(Spacer(1, 10))
        except Exception as e:
            story.append(
                Paragraph(
                    f"No se pudo renderizar el radar: {pdf_escape(e)}",
                    styles["SGSI_Normal"]
                )
            )

    # =========================
    # TABLA GENERAL CON COLORIMETRÍA TIPO ISO
    # =========================
    story.append(Paragraph("Detalle por Función y Categoría", styles["SGSI_Section"]))

    data = [[
        "Función",
        "Categoría",
        "Nombre",
        "% Cumplimiento",
        "Nivel de madurez",
        "Items"
    ]]

    for func in NIST_FUNC_ORDER:
        cats = (resumen or {}).get(func, {}) or {}
        if not cats:
            continue

        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            nivel_data = nist_nivel_visual_por_pct(pct)

            data.append([
                Paragraph(pdf_escape(func), styles["SGSI_Small"]),
                Paragraph(pdf_escape(cat_code), styles["SGSI_Small"]),
                Paragraph(pdf_escape(d.get("categoria") or ""), styles["SGSI_Small"]),
                Paragraph(f"{pct:.2f}%", styles["SGSI_Small"]),
                nivel_badge_pdf(pct, nivel_data),
                Paragraph(str(int(d.get("total", 0) or 0)), styles["SGSI_Small"])
            ])

    tbl = Table(
        data,
        colWidths=[2.7 * cm, 2.8 * cm, 10.3 * cm, 3.0 * cm, 5.0 * cm, 2.0 * cm],
        repeatRows=1
    )

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("ALIGN", (5, 1), (5, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tbl)

    # =========================
    # ANÁLISIS POR CATEGORÍA
    # =========================
    analisis_rows = NistMadurezCategoriaAnalisis.query.filter_by(
        run_id=run.id
    ).order_by(
        NistMadurezCategoriaAnalisis.funcion.asc(),
        NistMadurezCategoriaAnalisis.categoria_codigo.asc()
    ).all()

    if analisis_rows:
        story.append(PageBreak())
        add_section("Análisis Ejecutivo por Categoría")

        for a in analisis_rows:
            titulo_cat = f"{a.funcion} - {a.categoria_codigo}"
            story.append(Paragraph(pdf_escape(titulo_cat), styles["SGSI_Section"]))

            estado_actual = _normalizar_texto(a.estado_actual or "")
            estado_requerido = _normalizar_texto(a.estado_requerido or "")
            plan_accion = _normalizar_plan_accion_nist_texto(
                a.plan_accion_editado or a.plan_accion_ai or ""
            )

            bloque = Table([
                [
                    Paragraph("<b>Estado actual</b>", styles["SGSI_Small"]),
                    Paragraph(pdf_escape(estado_actual or "No registrado."), styles["SGSI_Small"])
                ],
                [
                    Paragraph("<b>Estado requerido</b>", styles["SGSI_Small"]),
                    Paragraph(pdf_escape(estado_requerido or "No registrado."), styles["SGSI_Small"])
                ],
                [
                    Paragraph("<b>Plan de acción</b>", styles["SGSI_Small"]),
                    Paragraph(pdf_escape(plan_accion or "No registrado."), styles["SGSI_Small"])
                ],
            ], colWidths=[4.2 * cm, 22.6 * cm])

            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(bloque)
            story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)
    return buf

def _nist_get_items_categoria(run_id: int, func_u: str, cat_u: str):
    """
    Retorna preguntas + estado + comentario de la categoría.
    Solo devuelve filas válidas.
    """
    q = (
        db.session.query(NistMadurezRespuesta, NistMadurezPregunta)
        .join(NistMadurezPregunta, NistMadurezPregunta.id == NistMadurezRespuesta.pregunta_id)
        .filter(NistMadurezRespuesta.run_id == run_id)
        .filter(db.func.upper(NistMadurezPregunta.funcion) == func_u)
        .filter(db.func.upper(NistMadurezPregunta.categoria_codigo) == cat_u)
        .order_by(NistMadurezPregunta.orden.asc(), NistMadurezPregunta.id.asc())
    )

    items = []
    for r, p in q.all():
        estado = (r.estado or "").upper().strip()
        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        items.append({
            "pregunta": _normalizar_texto(p.pregunta_es or p.pregunta_en or ""),
            "estado": estado,
            "comentario": _normalizar_texto(r.comentario or "")
        })

    return items



def _nist_ai_prompt_categoria(func_u: str, cat_u: str, cat_nombre: str, pct: float, items: list[dict]):
    bullets = []

    for it in items[:80]:
        pregunta = (it.get("pregunta") or "")[:280].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:350].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- [{estado}] {pregunta}"
        if comentario:
            linea += f" | Evidencia / información adicional: {comentario}"
        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor experto en NIST CSF 2.0. Debes producir un análisis accionable y concreto.

CONTEXTO
- Función: {func_u}
- Categoría: {cat_u}
- Nombre categoría: {cat_nombre}
- Cumplimiento actual: {pct:.2f}%

EVIDENCIAS (preguntas, estado e información adicional)
{joined}

INSTRUCCIONES OBLIGATORIAS
1) Devuelve SOLAMENTE JSON válido.
2) No devuelvas markdown.
3) No devuelvas texto antes ni después del JSON.
4) Debes devolver SIEMPRE estas tres llaves:
   - "estado_actual"
   - "estado_requerido"
   - "plan_accion"
5) "estado_actual" y "estado_requerido" deben ser textos obligatorios, no vacíos.
6) "plan_accion" debe ser un arreglo, aunque sea con 1 elemento.
7) Si falta evidencia, igual debes llenar "estado_actual" y "estado_requerido" explicándolo claramente.

FORMATO EXACTO DE SALIDA
{{
  "estado_actual": "texto obligatorio",
  "estado_requerido": "texto obligatorio",
  "plan_accion": [
    {{
      "accion": "texto",
      "prioridad": "Alta",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS
- Usa explícitamente la información adicional escrita por el usuario cuando exista.
- No inventes herramientas específicas si no aparecen.
- Si hay muchos "NO" o "PARCIAL", prioriza quick wins y controles base.
- Si no hay suficiente evidencia, dilo en "estado_actual" y plantea "estado_requerido" de forma objetiva.
""".strip()


def _nist_ai_text_openrouter(prompt: str, max_tokens: int = 1400) -> str:
    """
    Helper EXCLUSIVO para OpenRouter en NIST.
    No toca Ollama.
    Evita colisiones con otros módulos que también usan _ai_text.
    """
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("No hay OpenRouter API Key configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    max_tokens_safe = max(600, min(int(max_tokens or 1400), 2200))

    resp = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        temperature=0.2,
        max_tokens=max_tokens_safe,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un consultor experto en ciberseguridad, PCI-DSS, ISO 27001 y NIST CSF 2.0. "
                    "Debes responder únicamente con JSON válido, sin markdown, sin comentarios, "
                    "sin texto adicional antes o después del JSON."
                )
            },
            {"role": "user", "content": prompt},
        ],
    )

    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")

    return texto

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

def _ai_text(prompt: str, max_tokens: int = 900) -> str:
    """
    Helper central de IA para NIST.
    Respeta el proveedor configurado en Administración:
    - openrouter
    - ollama
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada en Administración.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado en Administración.")

        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        data = resp.json() or {}
        texto = (data.get("response") or "").strip()

        if not texto:
            raise RuntimeError("Ollama respondió sin contenido.")
        return texto

    # =========================
    # OPENROUTER
    # =========================
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("No hay OpenRouter API Key configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key
    )

    max_tokens_safe = max(300, min(int(max_tokens or 900), 2000))

    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        temperature=0.2,
        max_tokens=max_tokens_safe,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un consultor experto en ciberseguridad, PCI-DSS, ISO 27001 y NIST CSF 2.0. "
                    "Debes responder únicamente con JSON válido, sin markdown, sin comentarios, "
                    "sin texto adicional antes o después del JSON."
                )
            },
            {"role": "user", "content": prompt},
        ],
    )

    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")

    return texto

def _nist_prompt_informe_ejecutivo(run: "NistMadurezRun", resumen: dict) -> str:
    partes = []
    for func in NIST_FUNC_ORDER:
        cats = (resumen or {}).get(func, {}) or {}
        if not cats:
            partes.append(f"- {func}: sin información.")
            continue

        lineas_cat = []
        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            total = int(d.get("total", 0) or 0)
            nombre = (d.get("categoria") or "").strip()
            lineas_cat.append(
                f"  * {cat_code} - {nombre}: {pct:.2f}% ({total} ítems)"
            )

        labels, vals = nist_pct_por_funcion(resumen, [func])
        pct_func = vals[0] if vals else 0.0
        partes.append(
            f"- {func}: {pct_func:.2f}%\n" + "\n".join(lineas_cat[:20])
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ciberseguridad y gobierno de seguridad. Debes redactar un INFORME EJECUTIVO para alta dirección, claro, breve, profesional y accionable, basado en una evaluación de madurez NIST CSF 2.0.

DATOS GENERALES
- Consecutivo: {run.consecutivo}
- Cumplimiento general: {run.pct_general:.2f}%
- Nivel general: {nist_nivel_visual_por_pct(run.pct_general).get("nivel","")}

RESULTADOS POR FUNCIÓN Y CATEGORÍA
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "informe_ejecutivo": "texto"
}}

REGLAS DEL TEXTO:
- Escribe en español.
- Extensión aproximada: 4 a 7 párrafos cortos.
- Incluye:
  a) resumen general del nivel de madurez,
  b) fortalezas principales,
  c) brechas principales,
  d) funciones/capítulos más débiles,
  e) riesgos ejecutivos si no se actúa,
  f) prioridades recomendadas para los próximos 90 días.
- No inventes herramientas específicas.
- Usa un tono ejecutivo, no técnico en exceso.
- No uses markdown ni viñetas; redacta como informe.
""".strip()

def _nist_prompt_plan_trabajo(run: "NistMadurezRun", resumen: dict) -> str:
    partes = []

    for func in NIST_FUNC_ORDER:
        cats = (resumen or {}).get(func, {}) or {}
        if not cats:
            continue

        lineas_cat = []
        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            total = int(d.get("total", 0) or 0)
            nombre = (d.get("categoria") or "").strip()
            brecha = round(100.0 - pct, 2)

            lineas_cat.append(
                f"  * {cat_code} - {nombre}: {pct:.2f}% | brecha {brecha:.2f}% | {total} ítems"
            )

        labels, vals = nist_pct_por_funcion(resumen, [func])
        pct_func = vals[0] if vals else 0.0

        partes.append(
            f"- {func}: {pct_func:.2f}%\n" + "\n".join(lineas_cat[:25])
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ciberseguridad y NIST CSF 2.0.
Debes construir un PLAN DE TRABAJO GENERAL para cerrar brechas de madurez.

DATOS GENERALES
- Consecutivo: {run.consecutivo}
- Cumplimiento general: {run.pct_general:.2f}%
- Nivel general: {nist_nivel_visual_por_pct(run.pct_general).get("nivel","")}

RESULTADOS POR FUNCIÓN Y CATEGORÍA
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "plan_trabajo": [
    {{
      "frente": "string",
      "actividad": "string",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "string",
      "plazo": "string",
      "entregable": "string"
    }}
  ]
}}

REGLAS
- Genera entre 8 y 15 actividades.
- Prioriza primero las funciones y categorías con menor cumplimiento.
- Usa lenguaje ejecutivo y accionable.
- No inventes herramientas específicas.
""".strip()

@nist_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar el plan de trabajo con IA.", "danger")
        return redirect(url_for("madurez_nist.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF 2.0"):
        flash("No tiene permiso para generar el plan de trabajo del módulo NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    run = NistMadurezRun.query.get_or_404(run_id)

    if user.role != "admin" and run.user_id != user.id:
        flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
        return redirect(url_for("madurez_nist.historial"))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el plan de trabajo.", "warning")
        return redirect(url_for("madurez_nist.detalle", run_id=run.id))

    prompt = _nist_prompt_plan_trabajo(run, resumen)

    try:
        raw = _nist_ai_text_openrouter(prompt, max_tokens=1800)
    except Exception as e:
        flash(f"❌ Error llamando IA para el plan de trabajo: {e}", "danger")
        return redirect(url_for("madurez_nist.detalle", run_id=run.id))

    plan_texto = ""
    try:
        obj = _extraer_json_objeto(raw)
        plan_list = obj.get("plan_trabajo", []) if isinstance(obj, dict) else []

        if isinstance(plan_list, list) and plan_list:
            lines = []
            for i, it in enumerate(plan_list, start=1):
                frente = (it.get("frente") or "").strip()
                actividad = (it.get("actividad") or "").strip()
                prioridad = (it.get("prioridad") or "").strip()
                responsable = (it.get("responsable_sugerido") or "").strip()
                plazo = (it.get("plazo") or "").strip()
                entregable = (it.get("entregable") or "").strip()

                lines.append(
                    f"{i}. Frente: {frente or 'Sin definir'}\n"
                    f"   Actividad: {actividad or 'Sin definir'}\n"
                    f"   Prioridad: {prioridad or 'Sin definir'}\n"
                    f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
                    f"   Plazo: {plazo or 'Sin definir'}\n"
                    f"   Entregable: {entregable or 'Sin definir'}"
                )

            plan_texto = "\n\n".join(lines).strip()
    except Exception:
        plan_texto = ""

    if plan_texto and plan_texto.strip().startswith("{"):
        plan_texto = ""

    if not plan_texto:
        plan_texto = "No se pudo generar correctamente el plan de trabajo. Regenera el análisis."

    run.plan_trabajo_ai = plan_texto
    run.plan_trabajo_editado = plan_texto

    db.session.commit()
    flash("✅ Plan de trabajo generado con IA.", "success")
    return redirect(url_for("madurez_nist.detalle", run_id=run.id))

@nist_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede editar el plan de trabajo.", "danger")
        return redirect(url_for("madurez_nist.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF V.2.0"):
        flash("No tiene permiso para editar el plan de trabajo del módulo NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    run = NistMadurezRun.query.get_or_404(run_id)

    if user.role != "admin" and run.user_id != user.id:
        flash("No tiene permiso para editar esta revisión.", "danger")
        return redirect(url_for("madurez_nist.historial"))

    texto_actual = (run.plan_trabajo_editado or run.plan_trabajo_ai or "").strip()

    if request.method == "POST":
        texto = (request.form.get("plan_trabajo") or "").strip()
        run.plan_trabajo_editado = texto
        db.session.commit()
        flash("✅ Plan de trabajo actualizado.", "success")
        return redirect(url_for("madurez_nist.detalle", run_id=run.id))

    content = f"""
    <div class="nistexec-shell">

      <div class="nistexec-header-card">
        <div class="nistexec-header-overlay">
          <div class="nistexec-header-text">
            <h3 class="nistexec-title m-0">🗂️ Editar Plan de Trabajo — NIST CSF 2.0</h3>
            <div class="nistexec-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistexec-header-actions">
        <a href="{url_for('madurez_nist.detalle', run_id=run.id)}"
           class="btn nistexec-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="nistexec-card p-4">
        <form method="POST">
          <div class="nistexec-section-title">Plan de trabajo editable</div>

          <textarea name="plan_trabajo"
                    class="form-control nistexec-textarea"
                    rows="20"
                    placeholder="Escribe o ajusta aquí el plan de trabajo...">{escape(texto_actual)}</textarea>

          <div class="d-flex justify-content-center mt-4">
            <button type="submit" class="btn btn-primary rounded-pill px-5 fw-bold">
              <i class="bi bi-save2 me-2"></i>Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>
    """
    return render_template_string(BASE, title="Editar Plan de Trabajo NIST", content=content)

def _extraer_json_objeto(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return {}

def _extraer_valor_json_texto(raw: str, clave: str) -> str:
    """
    Extrae un valor de texto desde un JSON crudo o semiformado.
    Soporta respuestas con ```json ... ``` y JSON incompleto.
    """
    txt = (raw or "").strip()
    if not txt:
        return ""

    txt = txt.replace("```json", "").replace("```", "").strip()

    obj = _extraer_json_objeto(txt)
    if isinstance(obj, dict):
        return _normalizar_texto(obj.get(clave) or "")

    try:
        patron = rf'"{re.escape(clave)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
        m = re.search(patron, txt, re.DOTALL)
        if m:
            val = m.group(1)
            val = val.encode("utf-8").decode("unicode_escape")
            return _normalizar_texto(val)
    except Exception:
        pass

    return ""

def _nist_ai_text_categoria(prompt: str, max_tokens: int = 1600) -> str:
    provider = (get_ai_provider() or "openrouter").strip().lower()

    if provider == "ollama":
        return _ai_text(prompt, max_tokens=max_tokens)

    return _nist_ai_text_openrouter(prompt, max_tokens=max_tokens)

def _nist_extraer_json_objeto_categoria(raw: str) -> dict:
    txt = (raw or "").strip()
    if not txt:
        return {}

    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(txt)
    except Exception:
        pass

    try:
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(txt[start:end+1])
    except Exception:
        pass

    return {}

# ================
# Pagina Principal
# ================

@nist_madurez_bp.route("/", methods=["GET"])
@login_required
def home():
    user = User.query.get(session.get('user_id'))

    # Permisos
    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF V.2.0"):
        flash("No tiene permiso para acceder al módulo de plan de competencias.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    # Botón Ingresar la información
    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez_nist.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold grac-nav-blue-btn">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """

    # Botón Parámetros
    if read_only:
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        parametros_btn = f"""
          <a href="{url_for('madurez_nist.parametros')}"
             class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """
    
    total = NistMadurezPregunta.query.count()

    # Estado visual del instrumento
    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento (1 vez)."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información o consultar el historial de revisiones."

    content = f"""
    <div class="nistmad-shell">

      <!-- CABECERA -->
      <div class="nistmad-header-card">
        <div class="nistmad-header-overlay">
          <div class="nistmad-header-text">
            <h3 class="nistmad-title m-0">Nivel de Madurez — NIST CSF 2.0</h3>
            <div class="nistmad-subtitle">
              Evaluación por Función y Categoría del marco NIST CSF 2.0:
              GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND y RECOVER.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES PRINCIPALES -->
      <div class="nistmad-header-actions">

        {ingreso_btn}

        <a href="{url_for('madurez_nist.historial')}"
           class="btn nistmad-btn-soft rounded-pill px-4 historial-pill">
          <span class="d-inline-flex align-items-center gap-2">
            <span class="hist-dot"></span>
            <i class="bi bi-clock-history"></i>
            <span class="fw-semibold">Historial de Revisiones</span>
          </span>
        </a>
      </div>

      <!-- RESUMEN / ESTADO -->
      <div class="row g-3 mt-2">

        <div class="col-12 col-lg-8">
          <div class="nistmad-card p-4 h-100">

            <div class="nistmad-section-title">
              Estado del instrumento
            </div>

            <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
              <div>
                <div class="fw-bold">
                  Estado del instrumento {badge}
                </div>

                <div class="text-muted small mt-1">
                  Preguntas cargadas: <b>{total}</b>
                </div>

                <div class="mt-2 small">
                  {hint}
                </div>
              </div>

              <div class="text-end">
                <div class="text-muted small">Acceso rápido</div>
                <div class="d-flex gap-2 flex-wrap justify-content-end mt-2">
                  {parametros_btn}
                </div>
              </div>
            </div>

            <div class="alert alert-info mt-3 mb-0 small">
              <b>Sugerencia:</b> Usa <b>Parámetros</b> para ver la definición de niveles 1–5
              y gestionar la importación del instrumento.
            </div>

          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="nistmad-card p-4 h-100">

            <div class="nistmad-section-title">
              ¿Qué puedes hacer aquí?
            </div>

            <ul class="small mb-0 text-black ps-3">
              <li><b>Ingresar la información:</b> diligenciar respuestas (Sí/Parcial/No/N/A) con evidencia.</li>
              <li><b>Historial:</b> revisar evaluaciones previas y su porcentaje general.</li>
              <li><b>Parámetros:</b> ver niveles de madurez y cargar el instrumento.</li>
            </ul>

          </div>
        </div>

      </div>

    </div>

    <style>
      .bg-purple{{ background-color:#6f42c1 !important; }}
      .badge.bg-purple{{ color:#ffffff !important; }}

      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistmad-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      /* =========================
         HEADER ESTÁNDAR NIST
         ========================= */
      .nistmad-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nistmad-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistmad-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nistmad-header-overlay::before{{
        content:"🧭️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistmad-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
      }}

      .nistmad-header-text::before{{
        content:"SGSI · NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistmad-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistmad-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }}

      /* =========================
         BOTONES
         ========================= */
      .nistmad-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistmad-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
      }}

      .nistmad-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistmad-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .nistmad-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
      }}

      /* =========================
         CARDS
         ========================= */
      .nistmad-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
      }}

      .card-body{{
        padding:18px;
      }}

      /* =========================
         TABLAS
         ========================= */
      .table-responsive{{
        max-height:72vh;
        overflow:auto;
        border-radius:14px;
        background:#ffffff;
      }}

      .table thead th{{
        position:sticky;
        top:0;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900;
        text-align:center;
      }}

      .table tbody td{{
        font-size:.82rem;
        padding:9px;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      /* =========================
         FORMULARIOS
         ========================= */
      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
      }}

      /* =========================
         RESPONSIVE
         ========================= */
      @media (max-width:768px){{
        .nistmad-header-overlay{{
          flex-direction:column;
          text-align:center;
        }}

        .nistmad-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Madurez NIST", content=content)


# ================
# Parametros
# ================

@nist_madurez_bp.route("/parametros", methods=["GET"])
@login_required
def parametros():
    total = NistMadurezPregunta.query.count()

    badge = ""
    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'

    rows = []

    for lvl in NIST_MADUREZ_LEVELS:
        rows.append(f"""
        <tr>
          <td class="fw-semibold">{escape(lvl["nivel"])}</td>
          <td class="text-muted">{escape(lvl["descripcion"])}</td>
          <td class="text-center fw-bold">{lvl["score"]}</td>
          <td class="text-center">{escape(lvl.get("rango_pct",""))}</td>
          <td class="text-muted">{escape(lvl.get("logica",""))}</td>
        </tr>
        """)

    content = f"""
    <div class="nistpar-shell">

      <!-- CABECERA -->
      <div class="nistpar-header-card">
        <div class="nistpar-header-overlay">
          <div class="nistpar-header-text">
            <h3 class="nistpar-title m-0">Parámetros — Madurez NIST CSF 2.0</h3>
            <div class="nistpar-subtitle">
              Configuración del instrumento de evaluación y definición de los niveles
              de madurez utilizados para el cálculo del resultado del módulo.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="nistpar-header-actions">
        <a href="{url_for('madurez_nist.home')}" class="btn nistpar-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>
          Volver al Menú Principal de Madurez NIST
        </a>
      </div>

      <div class="row g-3 mt-2">

        <!-- CARD INSTRUMENTO -->
        <div class="col-12 col-lg-5">
          <div class="nistpar-card p-4 h-100">

            <div class="nistpar-section-title">
              Instrumento
            </div>

            <div class="text-muted small">
              Preguntas cargadas: <b>{total}</b> {badge}
            </div>

            <div class="d-flex gap-2 flex-wrap mt-3">

              <form method="POST" action="{url_for('madurez_nist.nist_importar_instrumento_admin')}">
                <button class="btn btn-danger rounded-pill px-4">
                  <i class="bi bi-database-add me-2"></i>
                  Importar instrumento (1 vez)
                </button>
              </form>

              <form method="POST" action="{url_for('madurez_nist.nist_importar_instrumento_admin', force=1)}">
                <button class="btn btn-outline-danger rounded-pill px-4">
                  <i class="bi bi-arrow-repeat me-2"></i>
                  Re-importar (force)
                </button>
              </form>

            </div>

            <div class="alert alert-warning mt-3 mb-0 small">
              <b>Nota:</b> “Re-importar (force)” elimina preguntas, runs y respuestas
              del módulo NIST y vuelve a cargar el instrumento completo.
            </div>

            <div class="mt-3">
              <a href="{url_for('madurez_nist.ingreso')}"
                 class="btn btn-primary rounded-pill px-4 w-100 fw-semibold grac-nav-blue-btn">
                <i class="bi bi-pencil-square me-2"></i>
                Ir a Ingresar la información
              </a>
            </div>

          </div>
        </div>

        <!-- CARD TABLA NIVELES -->
        <div class="col-12 col-lg-7">
          <div class="nistpar-card p-4 h-100">

            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
              <div class="nistpar-section-title mb-0">
                📌 Niveles de Madurez
              </div>

              <span class="badge bg-secondary">
                1 a 5
              </span>
            </div>

            <div class="table-responsive nistpar-table-wrap">

              <table class="table table-sm align-middle mb-0">

                <thead class="nistpar-table-head">
                  <tr>
                    <th style="width: 28%;">Nivel de Madurez</th>
                    <th>Descripción del Nivel</th>
                    <th class="text-center" style="width:70px;">Score</th>
                    <th class="text-center" style="width:110px;">Rango %</th>
                    <th style="width:22%;">Lógica</th>
                  </tr>
                </thead>

                <tbody>
                  {''.join(rows)}
                </tbody>

              </table>

            </div>

            <div class="small text-muted mt-3">
              Estos niveles describen la madurez del proceso organizacional.
              El puntaje del módulo se calcula por cumplimiento (Sí/Parcial/No)
              a nivel de preguntas del instrumento.
            </div>

          </div>
        </div>

      </div>

    </div>


    <style>
      .bg-purple{{ background-color:#6f42c1 !important; }}
      .badge.bg-purple{{ color:#ffffff !important; }}

      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistpar-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      /* =========================
         HEADER ESTÁNDAR NIST PARÁMETROS
         ========================= */
      .nistpar-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nistpar-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistpar-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nistpar-header-overlay::before{{
        content:"⚙️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistpar-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistpar-header-text::before{{
        content:"SGSI · Parámetros NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistpar-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistpar-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      /* =========================
         BOTONES
         ========================= */
      .nistpar-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistpar-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistpar-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nistpar-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistpar-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .nistpar-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistpar-btn-soft:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .btn-purple{{
        background:#6f42c1;
        border-color:#6f42c1;
        color:#ffffff;
      }}

      .btn-purple:hover{{
        background:#5b34a4;
        border-color:#5b34a4;
        color:#ffffff;
      }}

      .btn.pill,
      .btn.rounded-pill,
      .pill{{
        border-radius:999px !important;
      }}

      /* =========================
         CARDS
         ========================= */
      .nistpar-card,
      .card,
      .card-soft,
      .report-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistpar-card.p-4{{
        padding:1.5rem !important;
      }}

      .card-body{{
        padding:18px;
      }}

      .nistpar-card .btn-primary,
      .nistpar-card .btn-outline-danger,
      .nistpar-card .btn-outline-primary{{
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      /* =========================
         TÍTULOS DE SECCIÓN
         ========================= */
      .nistpar-section-title,
      .section-head h5,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:0;
      }}

      .nistpar-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      .section-head{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
      }}

      .section-sub,
      .muted{{
        color:#475569;
        font-size:.82rem;
      }}

      /* =========================
         TABLAS
         ========================= */
      .nistpar-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .table{{
        margin-bottom:0;
      }}

      .nistpar-table-head th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .table tbody td,
      table td,
      table th{{
        vertical-align:top !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .table-tight th,
      .table-tight td,
      .cell-small{{
        font-size:.78rem !important;
      }}

      .wrap{{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      /* =========================
         FORMULARIOS
         ========================= */
      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select,
      .report-textarea{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control,
      .report-textarea{{
        min-height:90px;
      }}

      .form-control:focus,
      .form-select:focus,
      .report-textarea:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      /* =========================
         NIVELES / DOTS / BADGES
         ========================= */
      .nivel-dot{{
        width:14px;
        height:14px;
        border-radius:50%;
        display:inline-block;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      /* =========================
         RESPONSIVE
         ========================= */
      @media (max-width:991.98px){{
        .nistpar-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistpar-header-card{{
          min-height:88px;
        }}

        .nistpar-title{{
          font-size:1.20rem;
        }}

        .nistpar-subtitle{{
          font-size:.68rem;
        }}

        .card-body{{
          padding:8px 7px;
        }}
      }}

      @media (max-width:768px){{
        .nistpar-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistpar-header-overlay::before{{
          margin:0;
        }}

        .nistpar-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistpar-title,
        .nistpar-subtitle{{
          text-align:center;
        }}

        .nistpar-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetros Madurez NIST", content=content)

# ==========================
# Ingreso de Información CSF
# ==========================

@nist_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF 2.0"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez_nist.home"))

    if NistMadurezPregunta.query.count() == 0:
        flash("⚠️ Primero debes importar el instrumento NIST (1 vez).", "warning")
        return redirect(url_for("madurez_nist.home"))

    preguntas = (
        NistMadurezPregunta.query
        .filter_by(activo=True)
        .order_by(
            NistMadurezPregunta.funcion.asc(),
            NistMadurezPregunta.categoria_codigo.asc(),
            NistMadurezPregunta.orden.asc()
        )
        .all()
    )

    draft = obtener_borrador_nist(user.id if user else None)
    respuestas_guardadas = cargar_respuestas_nist(draft.id) if draft else {}

    consecutivo_val = (draft.consecutivo if draft else "") or ""

    _, _, progreso_inicial = calcular_progreso_nist(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    grouped = _nist_group_questions()

    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(x or "")

    for func_name, cats in grouped.items():
        acc_id += 1
        func_key = f"func{acc_id}"
        inner = []

        for cat_code, payload in cats.items():
            rows = []

            for q in payload["items"]:
                saved = respuestas_guardadas.get(q.id, {})
                saved_estado = (saved.get("estado") or "").strip().upper()
                saved_com = esc(saved.get("comentario") or "")
                qtext = q.pregunta_es or q.pregunta_en or ""

                chk_na = "checked" if saved_estado == "NA" else ""
                chk_si = "checked" if saved_estado == "SI" else ""
                chk_pa = "checked" if saved_estado == "PARCIAL" else ""
                chk_no = "checked" if saved_estado == "NO" else ""

                rows.append(f"""
                <div class="col-12 col-xl-6">
                  <div class="nistform-qcard h-100">
                    <div class="nistform-qhead">
                      <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="badge rounded-pill text-bg-light border fw-semibold">
                          {esc(cat_code)}
                        </span>
                        <span class="badge rounded-pill text-bg-primary">
                          Orden {q.orden or 0}
                        </span>
                      </div>
                    </div>

                    <div class="nistform-qtext">
                      {esc(qtext)}
                    </div>

                    <div class="nistform-radio-row">
                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{q.id}" value="NA" {chk_na}>
                        <span>N/A</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{q.id}" value="SI" {chk_si}>
                        <span>Sí</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{q.id}" value="PARCIAL" {chk_pa}>
                        <span>Parcial</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{q.id}" value="NO" {chk_no}>
                        <span>No</span>
                      </label>
                    </div>

                    <div class="mt-3">
                      <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                      <textarea class="form-control form-control-sm"
                                name="cm_{q.id}"
                                rows="3"
                                placeholder="Comentarios / evidencia">{saved_com}</textarea>
                    </div>
                  </div>
                </div>
                """)

            inner.append(f"""
            <div class="nistform-cat-block">
              <div class="nistform-cat-title">
                <div>
                  <div class="nistform-cat-code">{esc(cat_code)}</div>
                  <div class="nistform-cat-name">{esc(payload.get('categoria', ''))}</div>
                </div>
                <div>
                  <span class="badge rounded-pill text-bg-secondary">{len(payload["items"])} preguntas</span>
                </div>
              </div>

              <div class="row g-3">
                {''.join(rows)}
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item nistform-acc-item">
          <h2 class="accordion-header" id="h{func_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''} nistform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{func_key}"
                    aria-expanded="{str(acc_id == 1).lower()}"
                    aria-controls="c{func_key}">
              <div class="nistform-acc-inner">
                <div class="nistform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="nistform-acc-title">{esc(func_name)}</span>
                </div>
                <span class="badge rounded-pill text-bg-light border">
                  {sum(len(v["items"]) for v in cats.values())} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="c{func_key}"
               class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body nistform-acc-body">
              {''.join(inner)}
            </div>
          </div>
        </div>
        """)

    alerta_borrador = ""
    if draft:
        alerta_borrador = f"""
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador cargado automáticamente.
          <strong>Progreso actual:</strong> {progreso_inicial}%.
        </div>
        """

    disabled_analizar = "" if progreso_inicial == 100 else "disabled"

    content = f"""
    <div class="nistform-shell">

      <div class="nistform-header-card">
        <div class="nistform-header-overlay">
          <div class="nistform-header-text">
            <h3 class="nistform-title m-0">Nivel de Madurez — NIST CSF 2.0</h3>
            <div class="nistform-subtitle">
              Registro de respuestas del instrumento de evaluación basado en
              el marco NIST Cybersecurity Framework 2.0.
            </div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_nist.home')}"
           class="btn nistform-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver a Madurez NIST
        </a>
      </div>

      <div class="nistform-card p-4">

        {alerta_borrador}

        <form id="nistIngresoForm"
              method="POST"
              action="{url_for('madurez_nist.ingreso_guardar')}"
              novalidate
              autocomplete="off">

          <input type="hidden" name="draft_id" value="{draft.id if draft else ''}">

          <div class="nistform-section-title">
            Información de la revisión
          </div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold" for="nistConsecutivoRevision">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control"
                   name="consecutivo"
                   id="nistConsecutivoRevision"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off"
                   required>

            <div id="nistConsecutivoRevisionError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress nistform-progress">
              <div id="nistProgressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width:{progreso_inicial}%"
                   aria-valuemin="0"
                   aria-valuemax="100"
                   aria-valuenow="{progreso_inicial}">
                {progreso_inicial}%
              </div>
            </div>

            <div class="text-center small text-muted mt-2">
              <span id="nistProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="nistform-section-title">
            Instrumento de evaluación
          </div>

          <div class="accordion nistform-accordion" id="accNist">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button id="btnGuardarNist"
                    class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar">
              <i class="bi bi-save2 me-2"></i>
              Guardar
            </button>

            <button id="btnAnalizarNist"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="analizar"
                    data-accion="analizar"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>
              Analizar
            </button>
          </div>

        </form>

      </div>

    </div>

    <script>
    (function() {{

        let NIST_BLOQUEAR_LOADER = false;

        function nistOcultarLoaderGlobal() {{
            const ids = [
                "SGSI_PROGRESS_GLOBAL",
                "globalLoader",
                "loader",
                "progressOverlay",
                "sgsiProgressGlobal",
                "globalProgress",
                "overlayProgress",
                "loadingOverlay"
            ];

            ids.forEach(function(id) {{
                const el = document.getElementById(id);
                if (el) {{
                    el.style.display = "none";
                    el.style.visibility = "hidden";
                    el.style.opacity = "0";
                    el.style.pointerEvents = "none";
                    el.classList.add("d-none");
                    el.classList.remove("show");
                }}
            }});

            document.querySelectorAll(
                ".modal-backdrop, " +
                ".progress-overlay, " +
                ".loader-overlay, " +
                ".sgsi-loader, " +
                ".sgsi-progress, " +
                ".loading-overlay, " +
                ".global-loader, " +
                ".global-progress, " +
                ".progress-global"
            ).forEach(function(el) {{
                el.style.display = "none";
                el.style.visibility = "hidden";
                el.style.opacity = "0";
                el.style.pointerEvents = "none";
                el.classList.add("d-none");
                el.classList.remove("show");
            }});

            document.body.classList.remove("modal-open");
            document.body.style.overflow = "";
            document.body.style.paddingRight = "";
        }}

        function nistValidarConsecutivoRevision() {{
            const input = document.getElementById("nistConsecutivoRevision");
            const error = document.getElementById("nistConsecutivoRevisionError");

            const valor = input ? input.value.trim() : "";

            if (!valor) {{
                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

                if (input) {{
                    input.classList.add("is-invalid");
                    input.setAttribute("aria-invalid", "true");
                    input.focus();
                }}

                if (error) {{
                    error.classList.remove("d-none");
                    error.style.display = "block";
                }}

                return false;
            }}

            NIST_BLOQUEAR_LOADER = false;

            if (input) {{
                input.classList.remove("is-invalid");
                input.setAttribute("aria-invalid", "false");
            }}

            if (error) {{
                error.classList.add("d-none");
                error.style.display = "none";
            }}

            return true;
        }}

        function actualizarProgresoNist() {{
            const radios = document.querySelectorAll('input[type="radio"][name^="st_"]');
            const nombres = [...new Set(Array.from(radios).map(r => r.name))];
            const total = nombres.length;

            let respondidas = 0;

            nombres.forEach(function(nombre) {{
                const marcado = document.querySelector('input[name="' + nombre + '"]:checked');
                if (marcado) {{
                    respondidas++;
                }}
            }});

            const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;

            const bar = document.getElementById("nistProgressBar");
            const text = document.getElementById("nistProgressText");
            const btnAnalizar = document.getElementById("btnAnalizarNist");

            if (bar) {{
                bar.style.width = porcentaje + "%";
                bar.innerText = porcentaje + "%";
                bar.setAttribute("aria-valuenow", porcentaje);
            }}

            if (text) {{
                text.innerText = porcentaje + "%";
            }}

            if (btnAnalizar) {{
                btnAnalizar.disabled = porcentaje < 100;
                btnAnalizar.classList.toggle("disabled", porcentaje < 100);
            }}
        }}

        const posiblesLoaders = [
            "showLoader",
            "mostrarLoader",
            "showGlobalLoader",
            "mostrarProgresoGlobal",
            "showProgress",
            "openLoader",
            "activarLoader",
            "SGSI_showLoader"
        ];

        posiblesLoaders.forEach(function(nombreFuncion) {{
            const original = window[nombreFuncion];

            if (typeof original === "function" && !original.__nistInterceptado) {{
                const wrapper = function() {{
                    if (NIST_BLOQUEAR_LOADER || !nistValidarConsecutivoRevision()) {{
                        nistOcultarLoaderGlobal();
                        return false;
                    }}

                    return original.apply(this, arguments);
                }};

                wrapper.__nistInterceptado = true;
                window[nombreFuncion] = wrapper;
            }}
        }});

        document.addEventListener("change", function(e) {{
            if (e.target.matches('input[type="radio"][name^="st_"]')) {{
                actualizarProgresoNist();
            }}
        }});

        document.addEventListener("click", function(e) {{
            const btn = e.target.closest(".nist-submit-btn");

            if (!btn) {{
                return;
            }}

            if (!nistValidarConsecutivoRevision()) {{
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

                return false;
            }}
        }}, true);

        window.addEventListener("DOMContentLoaded", function() {{
            const form = document.getElementById("nistIngresoForm");
            const input = document.getElementById("nistConsecutivoRevision");

            if (input) {{
                input.addEventListener("input", function() {{
                    nistValidarConsecutivoRevision();
                }});

                input.addEventListener("blur", function() {{
                    nistValidarConsecutivoRevision();
                }});
            }}

            if (form) {{
                form.addEventListener("submit", function(e) {{
                    if (!nistValidarConsecutivoRevision()) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        NIST_BLOQUEAR_LOADER = true;
                        nistOcultarLoaderGlobal();

                        return false;
                    }}
                }}, true);
            }}

            actualizarProgresoNist();
            nistOcultarLoaderGlobal();
        }});

        window.addEventListener("pageshow", function() {{
            nistOcultarLoaderGlobal();
        }});

    }})();
    </script>

    <style>
      .bg-purple{{ background-color:#6f42c1 !important; }}
      .badge.bg-purple{{ color:#ffffff !important; }}

      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistform-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .nistform-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nistform-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistform-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nistform-header-overlay::before{{
        content:"📝";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistform-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistform-header-text::before{{
        content:"SGSI · Evaluación NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistform-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistform-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistform-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistform-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistform-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nistform-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistform-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .nistform-card,
      .card,
      .card-soft,
      .report-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistform-card.p-4{{
        padding:1.5rem !important;
      }}

      .nistform-section-title{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      .nistform-progress{{
        height:22px;
        border-radius:999px;
        overflow:hidden;
        background:#e5edf7;
        box-shadow:inset 0 1px 3px rgba(15,23,42,.12);
      }}

      .progress-bar{{
        font-weight:900;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select,
      .report-textarea{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control,
      .report-textarea{{
        min-height:90px;
      }}

      .form-control:focus,
      .form-select:focus,
      .report-textarea:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-control.is-invalid{{
        border-color:#dc3545 !important;
        background:#fff5f5 !important;
        box-shadow:0 0 0 .15rem rgba(220,53,69,.15) !important;
      }}

      .invalid-feedback{{
        color:#b42318;
        background:#fff1f1;
        border:1px solid #ffd4d4;
        border-radius:10px;
        padding:8px 12px;
      }}

      .nistform-accordion{{
        --bs-accordion-border-color:transparent;
        --bs-accordion-btn-focus-box-shadow:0 0 0 .2rem rgba(63,134,214,.12);
      }}

      .nistform-acc-item,
      .accordion-item{{
        border:1px solid #dbe6f4 !important;
        border-radius:0 20px 20px 0 !important;
        overflow:hidden;
        margin-bottom:12px;
        background:#ffffff !important;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }}

      .nistform-acc-btn,
      .accordion-button{{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        padding:18px 22px !important;
        box-shadow:none !important;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-acc-btn:not(.collapsed),
      .accordion-button:not(.collapsed){{
        background:#dbeafe !important;
        color:#0b4a8f !important;
        box-shadow:none !important;
      }}

      .nistform-acc-inner{{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding-right:10px;
      }}

      .nistform-acc-title-wrap{{
        display:flex;
        align-items:center;
        gap:6px;
        min-width:0;
      }}

      .nistform-acc-title{{
        font-size:1rem;
        font-weight:950;
        color:#1e293b;
      }}

      .nistform-acc-body,
      .accordion-body{{
        background:rgba(255,255,255,.96) !important;
        padding:18px !important;
      }}

      .nistform-cat-block{{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        margin-bottom:16px;
      }}

      .nistform-cat-title{{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:12px;
        margin-bottom:14px;
        padding-bottom:10px;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-cat-code{{
        font-size:.92rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.15;
      }}

      .nistform-cat-name{{
        font-size:.78rem;
        color:#334155;
        margin-top:3px;
        line-height:1.25;
      }}

      .nistform-qcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
        height:100%;
        transition:.2s ease;
      }}

      .nistform-qcard:hover{{
        transform:translateY(-2px);
        box-shadow:0 8px 20px rgba(15,23,42,.10);
      }}

      .nistform-qhead{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin-bottom:10px;
      }}

      .nistform-qtext{{
        font-size:.92rem;
        color:#0f172a;
        font-weight:700;
        line-height:1.45;
      }}

      .nistform-radio-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .nistform-radio-card{{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:6px;
        background:#f8fafc;
        border:1px solid #dbe4ee;
        border-radius:12px;
        min-height:46px;
        font-weight:900;
        color:#101827;
        cursor:pointer;
        transition:.2s;
        padding:8px 10px;
      }}

      .nistform-radio-card:hover{{
        background:#eef6ff;
        border-color:#93c5fd;
      }}

      .nistform-radio-card input[type="radio"]{{
        transform:scale(1.08);
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:1200px){{
        .nistform-radio-row{{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:991.98px){{
        .nistform-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistform-header-card{{
          min-height:88px;
        }}

        .nistform-title{{
          font-size:1.20rem;
        }}

        .nistform-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .nistform-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistform-header-overlay::before{{
          margin:0;
        }}

        .nistform-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistform-title,
        .nistform-subtitle{{
          text-align:center;
        }}

        .nistform-header-actions .btn{{
          width:100%;
        }}

        .nistform-acc-inner,
        .nistform-cat-title{{
          flex-direction:column;
          align-items:flex-start;
        }}

        .nistform-radio-row{{
          grid-template-columns:1fr;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Ingreso NIST", content=content)


# =========================================================
# INGRESO NIST - GUARDAR / ANALIZAR
# REEMPLAZAR COMPLETO
# =========================================================

@nist_madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    consecutivo = _normalizar_texto(request.form.get("consecutivo"))
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not consecutivo:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez_nist.ingreso"))

    preguntas = (
        NistMadurezPregunta.query
        .filter_by(activo=True)
        .order_by(
            NistMadurezPregunta.funcion.asc(),
            NistMadurezPregunta.categoria_codigo.asc(),
            NistMadurezPregunta.orden.asc(),
            NistMadurezPregunta.id.asc()
        )
        .all()
    )

    if not preguntas:
        flash("⚠️ No hay preguntas activas cargadas en el instrumento NIST.", "warning")
        return redirect(url_for("madurez_nist.home"))

    respondidas, total, progreso_pct = calcular_progreso_nist(
        preguntas,
        form_data=request.form
    )

    try:
        run = None

        if draft_id and draft_id.isdigit():
            run = NistMadurezRun.query.filter_by(id=int(draft_id)).first()
            if run and user and run.user_id != user.id:
                flash("No tienes permiso para modificar este borrador.", "danger")
                return redirect(url_for("madurez_nist.ingreso"))

        if not run:
            run = obtener_borrador_nist(user.id if user else None)

        if respondidas == 0:
            if run and _contar_respuestas_run_nist(run.id) == 0:
                try:
                    NistMadurezCategoriaAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                    db.session.delete(run)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            flash("⚠️ Debes responder al menos una pregunta antes de guardar o analizar.", "warning")
            return redirect(url_for("madurez_nist.ingreso"))

        if not run:
            run = NistMadurezRun(
                consecutivo=consecutivo,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0,
                resumen_json="{}",
                pct_general=0.0,
                radar_overall_b64=None
            )
            db.session.add(run)
            db.session.flush()

        run.consecutivo = consecutivo
        run.progreso_pct = progreso_pct
        run.updated_at = datetime.now(timezone.utc)

        NistMadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        NistMadurezCategoriaAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        respuestas_insertadas = 0

        for q in preguntas:
            st = (request.form.get(f"st_{q.id}") or "").strip().upper()
            cm = _normalizar_texto(request.form.get(f"cm_{q.id}"))

            if st in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(NistMadurezRespuesta(
                    run_id=run.id,
                    pregunta_id=q.id,
                    estado=st,
                    comentario=cm
                ))
                respuestas_insertadas += 1

        db.session.flush()

        if respuestas_insertadas == 0:
            db.session.rollback()
            flash("⚠️ No se encontraron respuestas válidas para guardar.", "warning")
            return redirect(url_for("madurez_nist.ingreso"))

        if accion == "guardar":
            run.estado = "BORRADOR"
            run.resumen_json = "{}"
            run.pct_general = 0.0
            run.radar_overall_b64 = None
            db.session.commit()

            flash(
                f"✅ Borrador NIST guardado correctamente. "
                f"Preguntas respondidas: {respuestas_insertadas}/{total}. "
                f"Progreso actual: {progreso_pct}%.",
                "success"
            )
            return redirect(url_for("madurez_nist.ingreso"))

        if accion == "analizar":
            if progreso_pct < 100 or respondidas < total:
                db.session.commit()
                flash(
                    f"⚠️ El análisis solo se habilita cuando el instrumento esté al 100%. "
                    f"Actualmente llevas {progreso_pct}% ({respondidas}/{total}).",
                    "warning"
                )
                return redirect(url_for("madurez_nist.ingreso"))

            respuestas = (
                db.session.query(NistMadurezRespuesta, NistMadurezPregunta)
                .join(NistMadurezPregunta, NistMadurezPregunta.id == NistMadurezRespuesta.pregunta_id)
                .filter(NistMadurezRespuesta.run_id == run.id)
                .order_by(
                    NistMadurezPregunta.funcion.asc(),
                    NistMadurezPregunta.categoria_codigo.asc(),
                    NistMadurezPregunta.orden.asc(),
                    NistMadurezPregunta.id.asc()
                )
                .all()
            )

            if not respuestas:
                db.session.rollback()
                flash("❌ No fue posible consolidar el análisis porque no existen respuestas guardadas.", "danger")
                return redirect(url_for("madurez_nist.ingreso"))

            acc = {}
            sum_all = 0.0
            cnt_all = 0.0

            for r, q in respuestas:
                st = (r.estado or "").strip().upper()
                score = NIST_STATUS_SCORE.get(st, None)

                # Si es N/A o no existe, no entra al cálculo
                if score is None:
                    continue

                func = (q.funcion or "OTROS").upper().strip()
                cat = (q.categoria_codigo or "SIN_CATEGORIA").upper().strip()

                if func not in acc:
                    acc[func] = {}

                if cat not in acc[func]:
                    acc[func][cat] = {
                        "sum": 0.0,
                        "count": 0.0,
                        "categoria": (q.categoria or "").strip()
                    }

                acc[func][cat]["sum"] += float(score)
                acc[func][cat]["count"] += 1.0

                sum_all += float(score)
                cnt_all += 1.0

            resumen = {}
            for func, cats in acc.items():
                resumen[func] = {}
                for cat, d in cats.items():
                    count = float(d.get("count", 0) or 0)
                    pct = round((float(d.get("sum", 0.0)) / count) * 100.0, 2) if count > 0 else 0.0

                    resumen[func][cat] = {
                        "categoria": d.get("categoria", ""),
                        "pct": pct,
                        "total": int(count)
                    }

            pct_general = round((sum_all / cnt_all) * 100.0, 2) if cnt_all > 0 else 0.0

            for r, q in respuestas:
                st = (r.estado or "").strip().upper()
                score = NIST_STATUS_SCORE.get(st)
                if score is None:
                    continue

                func = (q.funcion or "OTROS").upper().strip()
                cat = (q.categoria_codigo or "SIN_CATEGORIA").upper().strip()

                if func not in acc:
                    acc[func] = {}

                if cat not in acc[func]:
                    acc[func][cat] = {
                        "sum": 0.0,
                        "count": 0,
                        "categoria": (q.categoria or "").strip()
                    }

                acc[func][cat]["sum"] += float(score)
                acc[func][cat]["count"] += 1
                sum_all += float(score)
                cnt_all += 1

            resumen = {}
            for func, cats in acc.items():
                resumen[func] = {}
                for cat, d in cats.items():
                    count = int(d.get("count", 0) or 0)
                    pct = round((float(d.get("sum", 0.0)) / count) * 100.0, 2) if count > 0 else 0.0

                    resumen[func][cat] = {
                        "categoria": d.get("categoria", ""),
                        "pct": pct,
                        "total": count
                    }

            pct_general = round((sum_all / cnt_all) * 100.0, 2) if cnt_all > 0 else 0.0
            radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
            radar_b64 = nist_radar_b64(radar_labels, radar_values, title="Radar por Función")

            run.estado = "FINALIZADO"
            run.progreso_pct = 100
            run.resumen_json = json.dumps(resumen, ensure_ascii=False)
            run.pct_general = pct_general
            run.radar_overall_b64 = radar_b64

            db.session.commit()

            flash(
                f"✅ Revisión NIST analizada correctamente. "
                f"Se consolidaron {cnt_all} respuestas válidas.",
                "success"
            )
            return redirect(url_for("madurez_nist.historial"))

        db.session.commit()
        flash("✅ Información procesada correctamente.", "success")
        return redirect(url_for("madurez_nist.ingreso"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error guardando la revisión NIST: {e}", "danger")
        return redirect(url_for("madurez_nist.ingreso"))
    
# =========================================================
# Historial NIST
# =========================================================
@nist_madurez_bp.route("/historial", methods=["GET"])
@login_required
def historial():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF 2.0"):
        flash("No tiene permiso para acceder al historial del módulo NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == "auditor")

    # =========================================================
    # IMPORTANTE:
    # NO eliminar automáticamente runs vacíos al abrir historial
    # porque puede hacer desaparecer revisiones que sí quieres ver.
    # =========================================================
    # try:
    #     _eliminar_runs_vacios_nist(user.id if user and user.role != "admin" else None)
    # except Exception:
    #     db.session.rollback()

    q = NistMadurezRun.query

    # =========================================================
    # Si quieres que Auditor vea TODO el historial, no filtres por user_id.
    # Si prefieres que vea solo lo suyo, vuelve a activar el filtro.
    # =========================================================
    # if user.role != "admin":
    #     q = q.filter(NistMadurezRun.user_id == user.id)

    runs = q.order_by(
        NistMadurezRun.created_at.desc(),
        NistMadurezRun.id.desc()
    ).all()

    rows_html = ""

    for run in runs:
        total_preguntas = NistMadurezRespuesta.query.filter_by(run_id=run.id).count()

        # =========================================================
        # NO ocultar la revisión si no tiene respuestas
        # =========================================================
        # if total_preguntas == 0:
        #     continue

        estado_txt = (run.estado or "BORRADOR").upper().strip()
        estado_badge = {
            "BORRADOR": "secondary",
            "FINALIZADO": "success"
        }.get(estado_txt, "secondary")

        try:
            pct_general = float(run.pct_general or 0)
        except Exception:
            pct_general = 0.0

        nivel_info = nist_nivel_visual_por_pct(pct_general)
        nivel_txt = nivel_info.get("nivel", "") if total_preguntas > 0 else "Sin respuestas registradas"
        pct_txt = f"{pct_general:.2f}%" if total_preguntas > 0 else "0.00%"

        if read_only:
            btn_eliminar = """
            <button class="btn btn-sm btn-outline-secondary rounded-pill" type="button" disabled
                    title="El perfil Auditor no puede eliminar revisiones">
              Eliminar
            </button>
            """
        else:
            btn_eliminar = f"""
            <form method="POST"
                  action="{url_for('madurez_nist.eliminar_revision', run_id=run.id)}"
                  style="display:inline;"
                  onsubmit="return confirm('¿Eliminar la revisión NIST #{run.id} - {escape(run.consecutivo or '')}?');">
              <button class="btn btn-sm btn-outline-danger rounded-pill" type="submit">
                Eliminar
              </button>
            </form>
            """

        rows_html += f"""
        <tr>
          <td class="text-muted">{run.id}</td>
          <td>{escape(run.consecutivo or "")}</td>
          <td>
            <span class="badge bg-{estado_badge}">
              {escape(estado_txt)}
            </span>
          </td>
          <td>{pct_txt}</td>
          <td class="wrap">{escape(nivel_txt)}</td>
          <td class="text-muted">
            {run.created_at.strftime('%Y-%m-%d %H:%M') if run.created_at else ''}
          </td>
          <td class="text-center">
            {total_preguntas}
          </td>
          <td class="text-end">
            <a class="btn btn-sm btn-outline-primary rounded-pill"
               href="{url_for('madurez_nist.detalle', run_id=run.id)}">
              Ver detalle
            </a>

            <a class="btn btn-sm btn-outline-warning rounded-pill"
               href="{url_for('madurez_nist.detalle_pdf', run_id=run.id)}">
              PDF
            </a>

            {btn_eliminar}
          </td>
        </tr>
        """

    content = f"""
    <div class="nisthist-shell">

      <div class="nisthist-header-card">
        <div class="nisthist-header-overlay">
          <div class="nisthist-header-text">
            <h3 class="nisthist-title m-0">Historial de Revisiones — NIST CSF 2.0</h3>
            <div class="nisthist-subtitle">
              Consulta revisiones previas, su porcentaje general, nivel de madurez y detalle.
            </div>
          </div>
        </div>
      </div>

      <div class="nisthist-header-actions">
        <a href="{url_for('madurez_nist.home')}"
           class="btn nisthist-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al inicio
        </a>
      </div>

      {"<div class='alert alert-info'>🔒 El perfil Auditor puede ver el historial y el detalle, pero no puede eliminar ni generar/editar contenido con IA.</div>" if read_only else ""}

      <div class="nisthist-card p-4">
        <div class="nisthist-section-title">Revisiones guardadas</div>

        <div class="table-responsive nisthist-table-wrap" style="max-height:620px; overflow:auto;">
          <table class="table table-sm align-middle table-hover mb-0">
            <thead class="nisthist-table-head">
              <tr>
                <th>ID</th>
                <th>Consecutivo</th>
                <th>Estado</th>
                <th>% General</th>
                <th>Nivel</th>
                <th>Fecha</th>
                <th>Respuestas</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows_html if rows_html else "<tr><td colspan='8' class='text-muted'>Aún no hay revisiones NIST guardadas.</td></tr>"}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nisthist-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      /* =========================
         HEADER ESTÁNDAR HISTORIAL NIST
         ========================= */
      .nisthist-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nisthist-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nisthist-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nisthist-header-overlay::before{{
        content:"📚";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nisthist-header-text{{
        max-width:1000px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nisthist-header-text::before{{
        content:"SGSI · Historial NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nisthist-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nisthist-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      /* =========================
         BOTONES
         ========================= */
      .nisthist-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nisthist-header-actions .btn,
      .btn{{
        border-radius:999px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nisthist-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nisthist-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
        border-radius:999px !important;
      }}

      .nisthist-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      /* =========================
         CARDS
         ========================= */
      .nisthist-card,
      .card,
      .card-soft,
      .report-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .card-body{{
        padding:18px;
      }}

      /* =========================
         TÍTULOS
         ========================= */
      .nisthist-section-title,
      .section-head h5,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:0;
      }}

      .nisthist-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      /* =========================
         TABLAS
         ========================= */
      .nisthist-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .nisthist-table-wrap .table,
      .table{{
        margin-bottom:0;
      }}

      .nisthist-table-wrap thead th,
      .nisthist-table-head th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .nisthist-table-wrap tbody td,
      .table tbody td{{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .wrap{{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      /* =========================
         RESPONSIVE
         ========================= */
      @media (max-width:991.98px){{
        .nisthist-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nisthist-header-card{{
          min-height:88px;
        }}

        .nisthist-title{{
          font-size:1.20rem;
        }}

        .nisthist-subtitle{{
          font-size:.68rem;
        }}

        .card-body{{
          padding:8px 7px;
        }}
      }}

      @media (max-width:768px){{
        .nisthist-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nisthist-header-overlay::before{{
          margin:0;
        }}

        .nisthist-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nisthist-title,
        .nisthist-subtitle{{
          text-align:center;
        }}

        .nisthist-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Historial NIST", content=content)

@nist_madurez_bp.route("/historial/<int:run_id>/eliminar", methods=["POST"])
@login_required
def eliminar_revision(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede eliminar revisiones NIST.", "danger")
        return redirect(url_for("madurez_nist.historial"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF 2.0"):
        flash("No tiene permiso para eliminar revisiones del módulo NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    run = NistMadurezRun.query.get_or_404(run_id)

    if user.role != "admin" and run.user_id != user.id:
        flash("No tiene permiso para eliminar esta revisión.", "danger")
        return redirect(url_for("madurez_nist.historial"))

    try:
        NistMadurezCategoriaAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        NistMadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        db.session.delete(run)
        db.session.commit()
        flash("🗑️ Revisión NIST eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error eliminando la revisión NIST: {e}", "danger")

    return redirect(url_for("madurez_nist.historial"))


@nist_madurez_bp.route("/historial/eliminar/<int:run_id>", methods=["POST"])
@login_required
def historial_eliminar(run_id: int):
    run = NistMadurezRun.query.get_or_404(run_id)

    try:
        # 1) Borrar análisis IA por categoría (si existe)
        NistMadurezCategoriaAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        # 2) Borrar respuestas del run
        NistMadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        # 3) Borrar el run
        db.session.delete(run)
        db.session.commit()

        flash("🗑️ Revisión eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error eliminando la revisión: {e}", "danger")

    return redirect(url_for("madurez_nist.historial"))

# ================
# Detalle
# ================

@nist_madurez_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id: int):
    run = NistMadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    def _nl2br(s: str) -> str:
        txt = _nist_limpiar_texto_rico_guardado(s or "")
        return txt.replace("\n", "<br>")

    # =========================
    # Radar por función
    # =========================
    radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
    radar_b64 = nist_radar_b64(radar_labels, radar_values, title="Radar por Función")

    informe_ai = _nist_limpiar_texto_rico_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = _nist_limpiar_texto_rico_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    nivel_general = nist_nivel_visual_por_pct(run.pct_general)
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = nivel_general_texto.split(":", 1)[1].strip() if ":" in nivel_general_texto else nivel_general_texto

    # =========================
    # Tarjeta superior
    # =========================
    top_html = f"""
    <div class="row g-3 mb-4">

      <div class="col-12 col-xl-5">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <div class="nistdet-card-title">📊 Radar por Capítulo General</div>
              <div class="text-muted small">
                Resultado consolidado por función NIST CSF 2.0.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:{nivel_general.get('color','#6c757d')}; color:#fff; font-size:.82rem;">
                Nivel {nivel_general.get('score', 0)}
              </div>
              <div class="small text-muted mt-1">{escape(nivel_general_nombre)}</div>
            </div>
          </div>

          <div class="text-center mt-3">
            {f'<img class="img-fluid nistdet-radar-img-small" src="data:image/png;base64,{radar_b64}">' if radar_b64 else '<div class="alert alert-warning mb-0">No fue posible generar el radar.</div>'}
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="nistdet-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados por capítulo y categoría.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <form method="POST"
                      action="{url_for('madurez_nist.informe_ejecutivo_generar', run_id=run.id)}"
                      class="m-0">
                  <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
                    <i class="bi bi-magic me-2"></i>Generar con IA
                  </button>
                </form>

                <a href="{url_for('madurez_nist.informe_ejecutivo_editar', run_id=run.id)}"
                   class="btn btn-primary rounded-pill px-4 fw-bold">
                  <i class="bi bi-pencil-square me-2"></i>Editar
                </a>
            </div>
          </div>

          <div class="nistdet-exec-box mt-3">
            {f'<div class="nistdet-exec-text">{_nl2br(escape(informe_mostrar))}</div>' if informe_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#129302;</div>>
                <div class="fw-bold text-black">Aún no hay informe ejecutivo</div>
                <div class="text-muted small mt-1">
                  Presiona <b>Generar con IA</b> para construir el informe con base en el resultado de los capítulos NIST.
                </div>
              </div>
            '''}
          </div>
        </div>
      </div>

    </div>
    """

    # =========================
    # Gauge
    # =========================
    def gauge_svg_categoria(pct, color="#2f6fb6"):
        try:
            pct = max(0, min(100, float(pct or 0)))
        except Exception:
            pct = 0.0

        radius = 44
        circumference = math.pi * radius
        progress = circumference * (pct / 100.0)

        return f"""
        <svg width="150" height="96" viewBox="0 0 120 78" aria-hidden="true">
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="#e9ecef" stroke-width="10" stroke-linecap="round"/>
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="{progress:.2f} {circumference:.2f}"/>
          <text x="60" y="46" text-anchor="middle"
                style="font-size:15px;font-weight:800;fill:#111;">{pct:.0f}%</text>
          <text x="17" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">0</text>
          <text x="103" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">100</text>
        </svg>
        """

    # =========================
    # Capítulos y categorías
    # =========================
    capitulo_cards = []

    for func in NIST_FUNC_ORDER:
        if func not in resumen:
            continue

        cats = resumen.get(func, {}) or {}

        # promedio del capítulo
        pct_func_list = []
        for _, d in cats.items():
            try:
                pct_func_list.append(float(d.get("pct", 0) or 0))
            except Exception:
                pct_func_list.append(0.0)

        pct_func = (sum(pct_func_list) / len(pct_func_list)) if pct_func_list else 0.0
        nivel_func = nist_nivel_visual_por_pct(pct_func)
        nivel_func_texto = (nivel_func.get("nivel") or "").strip()
        nivel_func_nombre = nivel_func_texto.split(":", 1)[1].strip() if ":" in nivel_func_texto else nivel_func_texto

        subcards = []

        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            total = int(d.get("total", 0) or 0)
            nombre_categoria = (d.get("categoria") or "").strip()
            nivel_data = nist_nivel_visual_por_pct(pct)

            nivel_score = nivel_data.get("score", "")
            nivel_texto = (nivel_data.get("nivel") or "").strip()
            nivel_nombre = nivel_texto.split(":", 1)[1].strip() if ":" in nivel_texto else nivel_texto

            gauge_html = gauge_svg_categoria(pct, nivel_data.get("color", "#2f6fb6"))

            subcards.append(f"""
            <div class="col-12 col-md-6 col-xl-4">
              <div class="nistdet-subcard h-100">

                <div class="nistdet-subcard-top">
                  <div class="text-center">
                    {gauge_html}
                  </div>
                </div>

                <div class="nistdet-subcard-body">
                  <div class="nistdet-row">
                    <div class="nistdet-label">Categoría</div>
                    <div class="nistdet-value fw-bold">{escape(cat_code)}</div>
                  </div>

                  <div class="nistdet-row">
                    <div class="nistdet-label">Nombre</div>
                    <div class="nistdet-value nistdet-value-wrap">{escape(nombre_categoria)}</div>
                  </div>

                  <div class="nistdet-row">
                    <div class="nistdet-label">% Cumplimiento</div>
                    <div class="nistdet-value fw-bold">{pct:.2f}%</div>
                  </div>

                  <div class="nistdet-row">
                    <div class="nistdet-label">Nivel de Madurez</div>
                    <div class="nistdet-value">
                      <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                        <span class="nivel-dot"
                              style="background-color:{nivel_data.get('color','#6c757d')} !important;"></span>
                        <span class="fw-bold">Nivel {nivel_score}</span>
                      </div>
                      <div class="text-muted small nistdet-value-wrap">
                        {escape(nivel_nombre)}
                      </div>
                    </div>
                  </div>

                  <div class="nistdet-row">
                    <div class="nistdet-label">Ítems</div>
                    <div class="nistdet-value fw-bold">{total}</div>
                  </div>

                  <div class="nistdet-row nistdet-row-actions">
                    <div class="nistdet-label">Acciones</div>
                    <div class="nistdet-value">
                      <div class="d-flex flex-wrap gap-2">
                        <a class="btn btn-sm btn-outline-primary rounded-pill"
                           href="{url_for('madurez_nist.detalle_categoria', run_id=run.id, func=func, cat_code=cat_code)}">
                          <i class="bi bi-list-check me-1"></i>Ver preguntas
                        </a>

                        <a class="btn btn-sm btn-outline-dark rounded-pill"
                           href="{url_for('madurez_nist.analisis_categoria', run_id=run.id, func=func, cat_code=cat_code)}">
                          <i class="bi bi-cpu me-1"></i>Análisis
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
            """)

        capitulo_cards.append(f"""
        <div class="nistdet-card p-4 mb-4">
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
            <div>
              <div class="nistdet-section-title">{escape(func)}</div>
              <div class="text-muted small">
                Resultado detallado por categorías del capítulo {escape(func)}.
              </div>
            </div>

            <div class="nistdet-capitulo-resumen">
              <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
                <span class="badge rounded-pill px-3 py-2"
                      style="background:{nivel_func.get('color','#6c757d')}; color:#fff;">
                  Nivel {nivel_func.get('score', 0)}
                </span>
                <span class="fw-bold text-dark">{pct_func:.2f}%</span>
              </div>
              <div class="small text-muted text-end mt-1">
                {escape(nivel_func_nombre)}
              </div>
            </div>
          </div>

          <div class="row g-3">
            {''.join(subcards)}
          </div>
        </div>
        """)

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Resultado de Madurez — NIST CSF 2.0</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento general: <b>{run.pct_general:.2f}%</b>
              · Nivel general: <b>{escape(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_nist.historial')}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_nist.home')}"
           class="btn nistdet-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>
      </div>

      {top_html}

      {''.join(capitulo_cards)}

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistdet-shell{{
        width:96%;
        max-width:1580px;
        margin:26px auto 24px auto;
      }}

      .nistdet-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nistdet-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistdet-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nistdet-header-overlay::before{{
        content:"📊";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistdet-header-text{{
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistdet-header-text::before{{
        content:"SGSI · Resultado NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistdet-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistdet-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistdet-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistdet-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistdet-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistdet-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .nistdet-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
      }}

      .nistdet-btn-success{{
        background:#198754;
        color:#ffffff !important;
        border:1px solid #198754;
      }}

      .nistdet-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
      }}

      .nistdet-card-title,
      .nistdet-section-title{{
        font-weight:950;
        color:#0b4a8f;
      }}

      .nistdet-section-title{{
        font-size:1rem;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .nistdet-radar-img-small{{
        max-width:290px;
        width:100%;
        height:auto;
        display:inline-block;
      }}

      .nistdet-exec-box{{
        min-height:310px;
        background:linear-gradient(180deg,rgba(248,250,252,.94),rgba(255,255,255,.98));
        border:1px solid rgba(63,134,214,.16);
        border-radius:16px;
        padding:18px;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.60);
      }}

      .nistdet-exec-text{{
        font-size:.96rem;
        line-height:1.65;
        color:#101827;
        white-space:normal;
      }}

      .nistdet-subcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 6px 18px rgba(15,23,42,.08);
      }}

      .nistdet-subcard-top{{
        border-bottom:1px solid rgba(0,0,0,.06);
        padding-bottom:8px;
        margin-bottom:10px;
      }}

      .nistdet-subcard-body{{
        display:flex;
        flex-direction:column;
        gap:6px;
      }}

      .nistdet-row{{
        display:grid;
        grid-template-columns:125px 1fr;
        gap:10px;
        align-items:start;
      }}

      .nistdet-label{{
        font-size:.82rem;
        font-weight:900;
        color:#334155;
      }}

      .nistdet-value{{
        font-size:.78rem;
        color:#0f172a;
      }}

      .nistdet-value-wrap{{
        word-break:break-word;
        white-space:normal;
      }}

      .nivel-dot{{
        width:12px;
        height:12px;
        border-radius:50%;
        display:inline-block;
        box-shadow:0 0 0 3px rgba(0,0,0,.06);
      }}

      @media (max-width:991.98px){{
        .nistdet-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistdet-header-card{{
          min-height:88px;
        }}

        .nistdet-title{{
          font-size:1.20rem;
        }}

        .nistdet-subtitle{{
          font-size:.68rem;
        }}

        .nistdet-radar-img-small{{
          max-width:255px;
        }}

        .nistdet-exec-box{{
          min-height:240px;
        }}

        .nistdet-row{{
          grid-template-columns:1fr;
          gap:3px;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Detalle NIST", content=content)


# ================
# PDF
# ================

@nist_madurez_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def detalle_pdf(run_id: int):
    run = NistMadurezRun.query.get_or_404(run_id)

    filename = f"NIST_CSF2_{(run.consecutivo or 'revision').replace(' ', '_')}.pdf"

    return send_file(
        _nist_build_pdf_run(run),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ================
# Categorias
# ================

@nist_madurez_bp.route("/detalle/<int:run_id>/categoria/<string:func>/<string:cat_code>", methods=["GET"])
@login_required
def detalle_categoria(run_id: int, func: str, cat_code: str):
    run = NistMadurezRun.query.get_or_404(run_id)

    func_u = (func or "").upper().strip()
    cat_u  = (cat_code or "").upper().strip()

    # Trae todas las respuestas de esa revisión, filtradas por función y categoría de la pregunta
    q = (
        db.session.query(NistMadurezRespuesta, NistMadurezPregunta)
        .join(NistMadurezPregunta, NistMadurezPregunta.id == NistMadurezRespuesta.pregunta_id)
        .filter(NistMadurezRespuesta.run_id == run.id)
        .filter(db.func.upper(NistMadurezPregunta.funcion) == func_u)
        .filter(db.func.upper(NistMadurezPregunta.categoria_codigo) == cat_u)
        .order_by(NistMadurezPregunta.orden.asc())
    )

    rows = []
    total_preguntas = 0

    for r, p in q.all():
        total_preguntas += 1

        qtext = p.pregunta_es or p.pregunta_en or ""
        estado = (r.estado or "").upper().strip()
        comentario = r.comentario or ""

        badge = {
            "SI": "success",
            "PARCIAL": "warning",
            "NO": "danger",
            "NA": "secondary"
        }.get(estado, "secondary")

        estado_texto = {
            "SI": "Sí",
            "PARCIAL": "Parcial",
            "NO": "No",
            "NA": "N/A"
        }.get(estado, estado)

        rows.append(f"""
        <tr>
          <td class="catdet-pregunta">{escape(qtext)}</td>
          <td class="text-center">
            <span class="badge bg-{badge} rounded-pill px-3 py-2">
              {escape(estado_texto)}
            </span>
          </td>
          <td class="catdet-comentario">{escape(comentario)}</td>
        </tr>
        """)

    content = f"""
    <div class="catdet-shell">

      <!-- CABECERA -->
      <div class="catdet-header-card">
        <div class="catdet-header-overlay">
          <div class="catdet-header-text">
            <h3 class="catdet-title m-0">Preguntas por Categoría — NIST CSF 2.0</h3>
            <div class="catdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Función: <b>{escape(func_u)}</b>
              · Categoría: <b>{escape(cat_u)}</b>
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="catdet-header-actions">
        <a href="{url_for('madurez_nist.detalle', run_id=run.id)}"
           class="btn catdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>
          Volver al Detalle
        </a>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="catdet-card p-4">

        <div class="catdet-resumen mb-3">
          <div class="catdet-resumen-title">Resumen de la categoría</div>
          <div class="catdet-resumen-text">
            Total de preguntas registradas: <b>{total_preguntas}</b>
          </div>
        </div>

        <div class="table-responsive catdet-table-wrap">
          <table class="table table-sm align-middle table-hover mb-0 catdet-table">
            <thead class="catdet-table-head">
              <tr>
                <th>Pregunta</th>
                <th class="text-center col-estado">Estado</th>
                <th>Comentario / Evidencia</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows) if rows else "<tr><td colspan='3' class='text-muted text-center py-4'>Sin registros.</td></tr>"}
            </tbody>
          </table>
        </div>

      </div>

    </div>

   <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .catdet-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .catdet-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .catdet-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .catdet-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        border-radius:18px;
        position:relative;
        z-index:1;
      }}

      .catdet-header-overlay::before{{
        content:"📂";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .catdet-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .catdet-header-text::before{{
        content:"SGSI · Detalle de Categoría NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .catdet-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .catdet-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .catdet-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .catdet-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .catdet-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .catdet-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .catdet-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .catdet-card.p-4{{
        padding:1.5rem !important;
      }}

      .catdet-resumen{{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        padding:14px 16px;
      }}

      .catdet-resumen-title{{
        font-weight:950;
        font-size:1rem;
        color:#0b4a8f;
        margin-bottom:4px;
      }}

      .catdet-resumen-text{{
        color:#44576b;
        font-size:.95rem;
      }}

      .catdet-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .catdet-table,
      .table{{
        width:100%;
        margin-bottom:0 !important;
        table-layout:fixed;
      }}

      .catdet-table-head th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .catdet-table th,
      .catdet-table td,
      .table tbody td{{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .catdet-table .col-estado{{
        width:140px;
      }}

      .catdet-pregunta{{
        min-width:380px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .catdet-comentario{{
        min-width:320px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table-hover tbody tr:hover,
      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .catdet-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .catdet-header-card{{
          min-height:88px;
        }}

        .catdet-title{{
          font-size:1.20rem;
        }}

        .catdet-subtitle{{
          font-size:.68rem;
        }}

        .catdet-table{{
          table-layout:auto;
        }}
      }}

      @media (max-width:768px){{
        .catdet-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .catdet-header-overlay::before{{
          margin:0;
        }}

        .catdet-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .catdet-title,
        .catdet-subtitle{{
          text-align:center;
        }}

        .catdet-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Preguntas por Categoría", content=content)

# ===================
# Analisis Categorias
# ===================

@nist_madurez_bp.route("/detalle/<int:run_id>/analisis/<string:func>/<string:cat_code>", methods=["GET", "POST"])
@login_required
def analisis_categoria(run_id: int, func: str, cat_code: str):
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de Madurez NIST CSF 2.0"):
        flash("No tiene permiso para acceder al análisis por categoría del módulo NIST CSF 2.0.", "danger")
        return redirect(url_for('menu'))

    run = NistMadurezRun.query.get_or_404(run_id)

    if user.role not in ("admin", "auditor"):
        if run.user_id and run.user_id != user.id:
            flash("No tiene permiso para acceder a esta revisión.", "danger")
            return redirect(url_for("madurez_nist.historial"))

    read_only = (user.role == "auditor")

    func_u = (func or "").upper().strip()
    cat_u  = (cat_code or "").upper().strip()

    modo_edicion = request.args.get("editar", "0") == "1"

    if read_only and modo_edicion:
        return redirect(
            url_for(
                "madurez_nist.analisis_categoria",
                run_id=run.id,
                func=func_u,
                cat_code=cat_u
            )
        )

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = (((resumen or {}).get(func_u, {}) or {}).get(cat_u, {}) or {})
    pct = float(d.get("pct", 0) or 0)
    cat_nombre = (d.get("categoria") or "").strip()

    ana = (
        NistMadurezCategoriaAnalisis.query
        .filter_by(run_id=run.id, funcion=func_u, categoria_codigo=cat_u)
        .first()
    )

    if request.method == "POST":
        if read_only:
            flash("El perfil Auditor no puede guardar cambios en el análisis por categoría.", "danger")
            return redirect(
                url_for(
                    "madurez_nist.analisis_categoria",
                    run_id=run.id,
                    func=func_u,
                    cat_code=cat_u
                )
            )

        estado_actual = (request.form.get("estado_actual") or "").strip()
        estado_req    = (request.form.get("estado_requerido") or "").strip()
        plan_editado  = _normalizar_plan_accion_nist_texto(
            (request.form.get("plan_accion_editado") or "").strip()
        )

        if not ana:
            ana = NistMadurezCategoriaAnalisis(
                run_id=run.id,
                funcion=func_u,
                categoria_codigo=cat_u
            )
            db.session.add(ana)

        ana.estado_actual = estado_actual
        ana.estado_requerido = estado_req
        ana.plan_accion_editado = plan_editado

        db.session.commit()
        flash("✅ Análisis guardado.", "success")
        return redirect(
            url_for(
                "madurez_nist.analisis_categoria",
                run_id=run.id,
                func=func_u,
                cat_code=cat_u
            )
        )

    estado_actual = (ana.estado_actual if ana else "") or ""
    estado_requerido = (ana.estado_requerido if ana else "") or ""

    plan_ai = _normalizar_plan_accion_nist_texto(
        (ana.plan_accion_ai if ana else "") or ""
    )
    plan_editado = _normalizar_plan_accion_nist_texto(
        (ana.plan_accion_editado if ana else "") or ""
    )

    plan_mostrar = plan_editado or plan_ai

    if read_only:
        toggle_btn_html = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                type="button"
                disabled
                title="El perfil Auditor no puede editar el análisis">
          <i class="bi bi-pencil-square me-2"></i>
          Editar
        </button>
        """
    else:
        toggle_btn_html = (
            f'''
            <a href="{url_for('madurez_nist.analisis_categoria', run_id=run.id, func=func_u, cat_code=cat_u)}"
               class="btn nistana-btn-main rounded-pill px-4 fw-bold">
              <i class="bi bi-eye me-2"></i>
              Ver modo lectura
            </a>
            '''
            if modo_edicion else
            f'''
            <a href="{url_for('madurez_nist.analisis_categoria', run_id=run.id, func=func_u, cat_code=cat_u, editar=1)}"
               class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi bi-pencil-square me-2"></i>
              Editar
            </a>
            '''
        )

    if modo_edicion and not read_only:
        panel_izquierdo = f"""
        <div class="col-12 col-lg-6">
          <div class="nistana-card p-4 h-100">
            <div class="nistana-card-title">✏️ Edición manual del análisis</div>
            <div class="text-muted small mb-3">
              Ajusta los textos generados y guarda los cambios.
            </div>

            <form method="POST">
              <div class="nistana-card-title">📌 Estado actual</div>
              <textarea class="form-control nistana-textarea"
                        name="estado_actual"
                        rows="8"
                        placeholder="Describe el estado actual...">{escape(estado_actual)}</textarea>

              <div class="nistana-card-title mt-3">🎯 Estado requerido</div>
              <textarea class="form-control nistana-textarea"
                        name="estado_requerido"
                        rows="7"
                        placeholder="Describe el estado objetivo...">{escape(estado_requerido)}</textarea>

              <div class="nistana-card-title mt-3">🛠 Plan de acción (editable)</div>
              <textarea class="form-control nistana-textarea"
                        name="plan_accion_editado"
                        rows="12"
                        placeholder="Puedes ajustar aquí el plan de acción...">{escape(plan_mostrar)}</textarea>

              <div class="d-flex justify-content-center mt-3">
                <button class="btn btn-primary rounded-pill px-5 fw-bold" type="submit">
                  <i class="bi bi-save2 me-2"></i>Guardar cambios
                </button>
              </div>
            </form>
          </div>
        </div>
        """

        panel_derecho = f"""
        <div class="col-12 col-lg-6">
          <div class="nistana-card p-4 h-100">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
              <div>
                <div class="nistana-card-title mb-0">🤖 Generación con IA</div>
                <div class="text-muted small mt-1">
                  La IA generará el estado actual, el estado requerido y el plan de acción
                  con base en el porcentaje de cumplimiento y la categoría evaluada.
                </div>
              </div>
            </div>

            <div class="text-center mt-4">
              <div class="nistana-ai-icon">
                <i class="bi bi-cpu"></i>
              </div>

              <div class="nistana-ai-title mt-2">
                Contenido asistido por IA
              </div>

              <div class="nistana-ai-text mt-2">
                Presiona el botón para generar o regenerar automáticamente el análisis
                de esta categoría.
              </div>

              <form method="POST"
                    action="{url_for('madurez_nist.analisis_categoria_generar', run_id=run.id, func=func_u, cat_code=cat_u)}"
                    class="m-0 mt-4">
                <button class="btn nistana-btn-success rounded-pill px-4 fw-bold" type="submit">
                  <i class="bi bi-magic me-2"></i>
                  Generar análisis (IA)
                </button>
              </form>
            </div>
          </div>
        </div>
        """

    else:
        panel_izquierdo = f"""
        <div class="col-12 col-lg-6">
          <div class="nistana-card p-4 h-100">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
              <div>
                <div class="nistana-card-title mb-0">📄 Análisis de la categoría</div>
                <div class="text-muted small mt-1">
                  Vista lista para consulta ejecutiva.
                </div>
              </div>
            </div>

            <div class="nistana-read-block">
              <div class="nistana-card-title">📌 Estado actual</div>
              <div class="nistana-read-box">
                {escape(estado_actual) if estado_actual else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
              </div>

              <div class="nistana-card-title mt-3">🎯 Estado requerido</div>
              <div class="nistana-read-box">
                {escape(estado_requerido) if estado_requerido else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
              </div>

              <div class="nistana-card-title mt-3">🛠 Plan de acción</div>
              <div class="nistana-read-box">
                {escape(plan_mostrar) if plan_mostrar else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
              </div>
            </div>
          </div>
        </div>
        """

        if read_only:
            panel_derecho = """
            <div class="col-12 col-lg-6">
              <div class="nistana-card p-4 h-100">
                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div>
                    <div class="nistana-card-title mb-0">🤖 Generación con IA</div>
                    <div class="text-muted small mt-1">
                      El perfil Auditor puede ver el análisis, pero no puede editarlo ni generarlo con IA.
                    </div>
                  </div>
                </div>

                <div class="nistana-ai-panel mt-3">
                  <div class="nistana-ai-icon">
                    <i class="bi bi-cpu"></i>
                  </div>
                  <div class="nistana-ai-title">Contenido asistido por IA</div>
                  <div class="nistana-ai-text">
                    La generación automática del análisis está bloqueada para el perfil Auditor.
                  </div>

                  <div class="mt-3">
                    <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled
                            title="El perfil Auditor no puede generar análisis con IA">
                      <i class="bi bi-magic me-2"></i>
                      Generar análisis (IA)
                    </button>
                  </div>
                </div>
              </div>
            </div>
            """
        else:
            panel_derecho = f"""
            <div class="col-12 col-lg-6">
              <div class="nistana-card p-4 h-100">
                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div>
                    <div class="nistana-card-title mb-0">🤖 Generación con IA</div>
                    <div class="text-muted small mt-1">
                      Usa este botón para generar o regenerar el análisis de la categoría.
                    </div>
                  </div>
                </div>

                <div class="nistana-ai-panel mt-3">
                  <div class="nistana-ai-icon">
                    <i class="bi bi-cpu"></i>
                  </div>
                  <div class="nistana-ai-title">Contenido asistido por IA</div>
                  <div class="nistana-ai-text">
                    La IA generará el estado actual, el estado requerido y el plan de acción
                    con base en el porcentaje de cumplimiento y la categoría evaluada.
                  </div>

                  <form method="POST"
                        action="{url_for('madurez_nist.analisis_categoria_generar', run_id=run.id, func=func_u, cat_code=cat_u)}"
                        class="m-0 mt-3">
                    <button class="btn nistana-btn-success rounded-pill px-4 fw-bold" type="submit">
                      <i class="bi bi-magic me-2"></i>
                      Generar análisis (IA)
                    </button>
                  </form>
                </div>
              </div>
            </div>
            """

    content = f"""
    <div class="nistana-shell">

      <div class="nistana-header-card">
        <div class="nistana-header-overlay">
          <div class="nistana-header-text">
            <h3 class="nistana-title m-0">Análisis por Categoría — NIST CSF 2.0</h3>
            <div class="nistana-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Función: <b>{escape(func_u)}</b>
              · Categoría: <b>{escape(cat_u)}</b>
              {" · Nombre: <b>" + escape(cat_nombre) + "</b>" if cat_nombre else ""}
              · % de cumplimiento: <b>{pct:.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistana-header-actions">
        <div class="d-flex flex-wrap justify-content-center gap-2">
          <a href="{url_for('madurez_nist.detalle', run_id=run.id)}"
             class="btn nistana-btn-main rounded-pill px-4 fw-bold">
            <i class="bi bi-arrow-left me-2"></i>
            Volver al Detalle
          </a>

          {toggle_btn_html}
        </div>
      </div>

      {"<div class='alert alert-info'>🔒 El perfil Auditor puede ver el análisis, pero no puede usar Editar ni Generar análisis (IA).</div>" if read_only else ""}

      <div class="row g-3">
        {panel_izquierdo}
        {panel_derecho}
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistana-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .nistana-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .nistana-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistana-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        border-radius:18px;
        position:relative;
        z-index:1;
      }}

      .nistana-header-overlay::before{{
        content:"🧠";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistana-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistana-header-text::before{{
        content:"SGSI · Análisis de Categoría NIST CSF 2.0";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistana-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistana-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistana-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistana-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistana-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistana-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .nistana-btn-success{{
        background:linear-gradient(135deg,#198754 0%,#20a866 100%);
        color:#ffffff !important;
        border:none;
        box-shadow:0 8px 18px rgba(25,135,84,.28);
      }}

      .nistana-btn-success:hover{{
        background:linear-gradient(135deg,#157347 0%,#1b9a5d 100%);
        color:#ffffff !important;
      }}

      .nistana-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistana-card.p-4{{
        padding:1.5rem !important;
      }}

      .nistana-card-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:1rem;
        color:#0b4a8f;
        margin-bottom:10px;
      }}

      .nistana-textarea{{
        border-radius:14px !important;
        border:1px solid #d9e3f0 !important;
        box-shadow:none !important;
        resize:vertical;
        background:#f8fafc;
      }}

      .nistana-textarea:focus{{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .nistana-read-box{{
        min-height:110px;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        padding:14px 16px;
        color:#243443;
        white-space:pre-wrap;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .nistana-ai-icon{{
        font-size:2.2rem;
        color:#0b4a8f;
        line-height:1;
      }}

      .nistana-ai-title{{
        font-weight:950;
        font-size:1.08rem;
        color:#0b4a8f;
      }}

      .nistana-ai-text{{
        color:#56697d;
        font-size:.95rem;
        line-height:1.5;
        max-width:420px;
        margin:0 auto;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      @media (max-width:991.98px){{
        .nistana-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistana-header-card{{
          min-height:88px;
        }}

        .nistana-title{{
          font-size:1.20rem;
        }}

        .nistana-subtitle{{
          font-size:.68rem;
        }}

        .nistana-read-box{{
          min-height:90px;
        }}
      }}

      @media (max-width:768px){{
        .nistana-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistana-header-overlay::before{{
          margin:0;
        }}

        .nistana-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistana-title,
        .nistana-subtitle{{
          text-align:center;
        }}

        .nistana-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Análisis NIST", content=content)


# =========================================================
# GENERAR ANÁLISIS IA POR CATEGORÍA
# =========================================================

