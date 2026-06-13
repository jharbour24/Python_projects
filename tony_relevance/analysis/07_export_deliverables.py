"""
Export the three deliverables to Word (.docx) and Excel (.xlsx).
Run from the repo root:  python3 tony_relevance/analysis/07_export_deliverables.py
"""

import sqlite3
import re
import textwrap
from pathlib import Path

import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE   = Path(__file__).resolve().parent.parent   # tony_relevance/
ROOT   = BASE.parent                               # Python_projects/
DB     = BASE / "tony_relevance.db"
OUT    = BASE / "outputs"
CHARTS = BASE / "charts"

# ── palette (mirrors the cream chart set) ──────────────────────────────────
BRICK  = RGBColor(0xA6, 0x43, 0x2C)
OLIVE  = RGBColor(0x4C, 0x5A, 0x38)
INK    = RGBColor(0x2B, 0x26, 0x20)
MUTED  = RGBColor(0x8C, 0x86, 0x78)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  WORD DOC  —  NIELSEN_2026.md  →  deliverables/Tony_Analysis.docx
# ══════════════════════════════════════════════════════════════════════════════

def _set_heading_style(para, level: int):
    """Apply a clean heading style — no need for named styles from a template."""
    run = para.runs[0] if para.runs else para.add_run(para.text)
    if level == 0:          # title
        run.font.size   = Pt(22)
        run.font.color.rgb = BRICK
        run.font.bold   = True
        para.alignment  = WD_ALIGN_PARAGRAPH.LEFT
    elif level == 1:        # H2
        run.font.size   = Pt(14)
        run.font.color.rgb = OLIVE
        run.font.bold   = True
        para.paragraph_format.space_before = Pt(16)
    elif level == 2:        # H3
        run.font.size   = Pt(12)
        run.font.color.rgb = INK
        run.font.bold   = True
        para.paragraph_format.space_before = Pt(10)


def _add_table_from_md(doc: Document, lines: list[str]):
    """Parse a Markdown pipe-table block and insert a Word table."""
    rows = [l for l in lines if l.startswith("|") and "---" not in l]
    if not rows:
        return
    cells_per_row = [
        [c.strip() for c in r.strip("|").split("|")]
        for r in rows
    ]
    ncols = max(len(r) for r in cells_per_row)
    tbl   = doc.add_table(rows=len(cells_per_row), cols=ncols)
    tbl.style = "Table Grid"

    for i, row_data in enumerate(cells_per_row):
        for j, cell_text in enumerate(row_data):
            if j >= ncols:
                break
            cell = tbl.cell(i, j)
            cell.text = cell_text
            run = cell.paragraphs[0].runs
            if i == 0:                          # header row — bold
                for r in run:
                    r.font.bold = True
                    r.font.color.rgb = OLIVE
            # compact font
            for r in cell.paragraphs[0].runs:
                r.font.size = Pt(9)

    doc.add_paragraph()     # breathing room after table


def _inline_md(para, text: str):
    """
    Add a paragraph run that strips light markdown (** bold, ` code).
    Keeps it simple — not a full MD parser.
    """
    # Split on **bold** or `code` markers
    token_re = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")
    parts = token_re.split(text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.font.bold = True
            run.font.color.rgb = INK
        elif part.startswith("`") and part.endswith("`"):
            run = para.add_run(part[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9)
            run.font.color.rgb = BRICK
        else:
            run = para.add_run(part)
    for run in para.runs:
        if not run.font.size:
            run.font.size = Pt(11)
            run.font.color.rgb = INK


def build_word_doc():
    md_path = OUT / "NIELSEN_2026.md"
    md_text = md_path.read_text()

    doc = Document()

    # Page margins — generous
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(3.0)

    # Default body font
    style = doc.styles["Normal"]
    style.font.name = "Palatino Linotype"
    style.font.size = Pt(11)

    # ── Cover block ──────────────────────────────────────────────────────────
    cover = doc.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = cover.add_run("ARE THE TONYS STILL RELEVANT?")
    r.font.size = Pt(24)
    r.font.bold = True
    r.font.color.rgb = BRICK

    sub = doc.add_paragraph()
    r2  = sub.add_run(
        "Nielsen viewership analysis updated through 2026 — findings, charts, and data"
    )
    r2.font.size = Pt(12)
    r2.font.color.rgb = MUTED
    doc.add_paragraph()

    # ── Embed charts ────────────────────────────────────────────────────────
    chart_files = sorted(CHARTS.glob("striking_*.png"))
    if chart_files:
        doc.add_heading("Charts", level=1)
        for cf in chart_files:
            try:
                doc.add_picture(str(cf), width=Inches(5.8))
                cap = doc.add_paragraph(cf.stem.replace("_", " ").title())
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in cap.runs:
                    run.font.size = Pt(8)
                    run.font.color.rgb = MUTED
            except Exception as e:
                doc.add_paragraph(f"[Chart could not be embedded: {cf.name} — {e}]")
        doc.add_page_break()

    # ── Parse markdown body ──────────────────────────────────────────────────
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # headings
        if line.startswith("### "):
            h = doc.add_paragraph()
            h.add_run(line[4:])
            _set_heading_style(h, 2)

        elif line.startswith("## "):
            h = doc.add_paragraph()
            h.add_run(line[3:])
            _set_heading_style(h, 1)

        elif line.startswith("# "):
            h = doc.add_paragraph()
            h.add_run(line[2:])
            _set_heading_style(h, 0)

        # horizontal rule
        elif line.startswith("---"):
            doc.add_paragraph("─" * 60).runs[0].font.color.rgb = MUTED

        # fenced code block
        elif line.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if code_lines:
                p = doc.add_paragraph()
                r = p.add_run("\n".join(code_lines))
                r.font.name = "Courier New"
                r.font.size = Pt(8.5)
                r.font.color.rgb = BRICK

        # pipe table — collect all consecutive pipe lines
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            _add_table_from_md(doc, table_lines)
            continue  # i already advanced

        # bullet
        elif line.startswith("- ") or line.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            _inline_md(p, line[2:])

        # numbered list
        elif re.match(r"^\d+\. ", line):
            p = doc.add_paragraph(style="List Number")
            _inline_md(p, re.sub(r"^\d+\. ", "", line))

        # blockquote
        elif line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.0)
            r = p.add_run(line[2:])
            r.font.italic = True
            r.font.size   = Pt(10)
            r.font.color.rgb = MUTED

        # blank line
        elif not line.strip():
            doc.add_paragraph()

        # normal body text
        else:
            p = doc.add_paragraph()
            _inline_md(p, line)

        i += 1

    out_path = OUT / "Tony_Analysis.docx"
    doc.save(str(out_path))
    print(f"  [word] saved → {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# 2.  EXCEL WORKBOOK  →  deliverables/Tony_Data.xlsx
# ══════════════════════════════════════════════════════════════════════════════

def build_excel():
    con = sqlite3.connect(DB)

    sheets = {
        "award_broadcasts":       "SELECT * FROM award_broadcasts ORDER BY award, ceremony_year",
        "audience_demographics":  "SELECT * FROM audience_demographics ORDER BY award, year",
        "tv_universe":            "SELECT * FROM tv_universe ORDER BY year",
        "best_musical_source":    None,   # from CSV
        "v_relevance (view)":     "SELECT * FROM v_relevance ORDER BY award, year",
    }

    out_path = OUT / "Tony_Data.xlsx"

    with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:

        for sheet_name, query in sheets.items():
            if query is None:
                # load from CSV
                csv = BASE / "sources" / "best_musical_source.csv"
                if csv.exists():
                    df = pd.read_csv(csv)
                else:
                    continue
            else:
                try:
                    df = pd.read_sql(query, con)
                except Exception as e:
                    print(f"  [excel] skipping {sheet_name}: {e}")
                    continue

            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            # Basic column-width formatting
            ws = writer.sheets[sheet_name[:31]]
            for col_cells in ws.columns:
                max_len = max(
                    (len(str(c.value)) if c.value is not None else 0)
                    for c in col_cells
                )
                ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 50)

            # Bold header row
            from openpyxl.styles import Font, PatternFill, Alignment
            hdr_fill  = PatternFill("solid", fgColor="2B2620")
            hdr_font  = Font(bold=True, color="F4EFE2", size=10)
            for cell in ws[1]:
                cell.font      = hdr_font
                cell.fill      = hdr_fill
                cell.alignment = Alignment(horizontal="center")

    con.close()
    print(f"  [excel] saved → {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# 3.  CHART INVENTORY  (already PNG — just list them)
# ══════════════════════════════════════════════════════════════════════════════

def list_charts():
    pngs = sorted(CHARTS.glob("striking_*.png"))
    print(f"\n  [charts] {len(pngs)} striking PNGs ready in {CHARTS}:")
    for p in pngs:
        print(f"    {p.name}  ({p.stat().st_size // 1024} KB)")
    return pngs


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\nBuilding deliverables …\n")
    build_word_doc()
    build_excel()
    list_charts()
    print("\nDone.\n")
