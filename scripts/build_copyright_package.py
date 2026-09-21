"""Build copyright documents from an edited manuscript and current source files.

Source export preserves comments, identifiers and license notices. It omits empty
print lines and expands tabs for layout; it does not rewrite program content.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from PIL import Image

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output/copyright_work"
STAGE = WORK / "package"
MANUSCRIPT = ROOT / "docs/copyright/设计说明书.md"
NAME = "亲健（基于生成式 AI 的泛亲密关系智能感知与维系系统）"
VERSION = "V1.0"
ROWS_PER_PAGE = 50
PRINT_COLUMNS = 88


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def set_font(style, name="宋体", size=12):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attribute in list(fonts.attrib):
        if attribute.rsplit("}", 1)[-1].lower().endswith("theme"):
            del fonts.attrib[attribute]
    for key in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn("w:" + key), name)


def field(paragraph, instruction):
    node = OxmlElement("w:fldSimple")
    node.set(qn("w:instr"), instruction)
    paragraph._p.append(node)


def new_document(source=False):
    doc = Document()
    for border in list(doc.styles.element.iter(qn("w:pBdr"))):
        border.getparent().remove(border)
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2.25), Cm(2.05)
    if not source:
        section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.1)
    section.header_distance = section.footer_distance = Cm(0.9)
    doc.core_properties.title = NAME + " " + VERSION
    doc.core_properties.author = "亲健"
    doc.core_properties.last_modified_by = "亲健"
    doc.core_properties.comments = ""
    set_font(doc.styles["Normal"])
    normal = doc.styles["Normal"].paragraph_format
    normal.line_spacing = Pt(17)
    normal.space_after = Pt(2)
    normal.first_line_indent = Pt(24)
    normal.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.widow_control = True
    for key, size in (("Title", 16), ("Heading 1", 14), ("Heading 2", 12)):
        style = doc.styles[key]
        set_font(style, "宋体", size)
        style.font.bold = True
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(6 if key != "Title" else 0)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = Pt(18)
    for name in ("Header", "Footer"):
        set_font(doc.styles[name], size=8.5)
        doc.styles[name].paragraph_format.first_line_indent = Pt(0)
        doc.styles[name].paragraph_format.space_after = Pt(0)
    header = section.header.paragraphs[0]
    header.text = NAME + "  " + VERSION + "\t"
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header.paragraph_format.tab_stops.add_tab_stop(Cm(16.8), WD_TAB_ALIGNMENT.RIGHT)
    header.add_run("第 ")
    field(header, "PAGE")
    header.add_run(" 页 / 共 ")
    field(header, "NUMPAGES")
    header.add_run(" 页")
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    if source:
        set_font(doc.styles["Normal"], "宋体", 10.5)
        normal.first_line_indent = Pt(0)
        normal.alignment = WD_ALIGN_PARAGRAPH.LEFT
        normal.space_before = normal.space_after = Pt(0)
        normal.line_spacing = Pt(13)
        normal.widow_control = False
        normal.keep_with_next = False
    return doc


def add_table(doc, lines):
    data = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in lines if not re.match(r"^\|[\s:|\-]+\|$", line.strip())]
    cols = len(data[0])
    table = doc.add_table(rows=1, cols=cols)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    if data[0][0] == "请求":
        widths = [1.4, 8.2, 7.2]
    elif data[0][0] == "数据表":
        widths = [5.2, 6.0, 5.6]
    elif cols == 2:
        widths = [5.7, 11.1]
    else:
        widths = [4.0, 6.2, 6.6]
    for col, width in zip(table.columns, widths):
        col.width = Cm(width)
    props = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement("w:" + edge)
        for k, v in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
            b.set(qn("w:" + k), v)
        borders.append(b)
    props.append(borders)
    for i, values in enumerate(data):
        row = table.rows[0] if i == 0 else table.add_row()
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trpr.append(OxmlElement("w:tblHeader"))
        for column, (cell, value, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement("w:tcMar")
            padding = "45" if data[0][0] == "请求" else "75"
            for edge, amount in (("top", padding), ("bottom", padding), ("left", "90"), ("right", "90")):
                e = OxmlElement("w:" + edge)
                e.set(qn("w:w"), amount)
                e.set(qn("w:type"), "dxa")
                margins.append(e)
            pr.append(margins)
            if i == 0:
                shade = OxmlElement("w:shd")
                shade.set(qn("w:fill"), "EEEEEE")
                pr.append(shade)
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(12.5 if data[0][0] == "请求" else 14)
            p.paragraph_format.keep_with_next = i == 0
            center_value = column == 0 and data[0][0] not in ("字段", "数据表")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 or center_value else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(value)
            run.font.name = "宋体"
            run.font.size = Pt(10.5)
            run.font.bold = i == 0
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = Pt(3)


def build_design():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    doc = new_document()
    lines = text.splitlines()
    i = 0
    first_chapter = True
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            add_table(doc, block)
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=2)
        elif line.startswith("## "):
            if first_chapter:
                p = doc.add_paragraph("目录", style="Title")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(24)
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Pt(0)
                field(p, 'TOC \\o "1-1" \\h \\z')
                doc.add_section(WD_SECTION_START.NEW_PAGE)
                first_chapter = False
                heading = doc.add_heading(line[3:], level=1)
            else:
                heading = doc.add_heading(line[3:], level=1)
                heading.paragraph_format.page_break_before = False
        elif re.match(r"^!\[.*\]\(.*\)$", line):
            match = re.match(r"^!\[(.*)\]\((.*)\)$", line)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.line_spacing = 1
            p.paragraph_format.keep_with_next = True
            picture_path = MANUSCRIPT.parent / match.group(2)
            with Image.open(picture_path) as picture:
                picture_width = 16.8 if picture.width > picture.height else 7.5
            p.add_run().add_picture(str(picture_path), width=Cm(picture_width))
            p = doc.add_paragraph(match.group(1))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Pt(0)
            for run in p.runs:
                run.font.size = Pt(10.5)
        elif line.startswith("# "):
            p = doc.add_paragraph(line[2:], style="Title")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith(("版本号：", "文档名称：", "著作权人：", "开发完成日期：")):
            p = doc.add_paragraph(line)
            p.paragraph_format.first_line_indent = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif re.match(r"^表\s*\d+\s", line):
            p = doc.add_paragraph(line)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = Pt(15)
            for run in p.runs:
                run.font.size = Pt(10.5)
        else:
            p = doc.add_paragraph(line)
            next_line = next((value.strip() for value in lines[i + 1:] if value.strip()), "")
            if next_line.startswith("!["):
                p.paragraph_format.keep_with_next = False
        i += 1
    output = STAGE / "设计说明书_提交稿.docx"
    doc.save(output)
    return {"path": str(output.relative_to(ROOT)), "manuscript_sha256": sha256(text.encode()),
            "characters": len(text), "tables": len(doc.tables)}


def print_chunks(line):
    expanded = line.expandtabs(4)
    if not expanded.strip():
        return []
    chunks, part, width = [], "", 0
    for char in expanded:
        increment = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if part and width + increment > PRINT_COLUMNS:
            chunks.append(part)
            part, width = "", 0
        part += char
        width += increment
    if part:
        chunks.append(part)
    assert "".join(chunks) == expanded
    return chunks


def source_files():
    files = []
    for root in (ROOT / "backend/app", ROOT / "web-vue3/src"):
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in {".py", ".js", ".ts", ".vue", ".css"}:
                continue
            if any(part in {"__pycache__", "node_modules", "dist", "tests", "__tests__"} for part in p.parts):
                continue
            if any(part in p.name for part in (".test.", ".spec.")):
                continue
            files.append(p)
    main = ROOT / "backend/app/main.py"
    groups = ["backend/app/core/", "backend/app/models/", "backend/app/schemas/",
              "backend/app/api/", "web-vue3/src/", "backend/app/ai/", "backend/app/services/"]
    def order(path):
        name = path.relative_to(ROOT).as_posix()
        group = next((i for i, prefix in enumerate(groups) if name.startswith(prefix)), -1)
        return group, name
    return [main] + sorted((p for p in files if p != main), key=order)


def build_source():
    rows, locations, manifest = [], [], []
    total_lines = 0
    for path in source_files():
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")
        if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}", content):
            raise ValueError("Potential credential in source file: " + str(path.relative_to(ROOT)))
        original = content.splitlines()
        start = len(rows)
        for number, line in enumerate(original, 1):
            chunks = print_chunks(line)
            for chunk_id, chunk in enumerate(chunks):
                rows.append(chunk)
                locations.append({"file": path.relative_to(ROOT).as_posix(), "line": number, "part": chunk_id})
        total_lines += len(original)
        manifest.append({"file": path.relative_to(ROOT).as_posix(), "sha256": sha256(raw),
                         "physical_source_lines": len(original), "print_rows": len(rows) - start,
                         "first_print_row": start + 1, "last_print_row": len(rows)})
    pages = [rows[i:i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]
    selected = list(range(len(pages))) if len(pages) <= 60 else list(range(30)) + list(range(len(pages) - 30, len(pages)))
    doc = new_document(source=True)
    page_map = []
    for physical_page, page_index in enumerate(selected, 1):
        page = pages[page_index]
        for line_index, line in enumerate(page):
            p = doc.add_paragraph(line)
            if physical_page > 1 and line_index == 0:
                p.paragraph_format.page_break_before = True
        start, end = page_index * ROWS_PER_PAGE, page_index * ROWS_PER_PAGE + len(page) - 1
        page_map.append({"submission_page": physical_page, "whole_source_page": page_index + 1,
                         "print_rows": len(page), "start": locations[start], "end": locations[end]})
    output = STAGE / "源程序_提交稿_前30后30.docx"
    doc.save(output)
    (WORK / "源程序完整排版文本.txt").write_text("\n".join(rows), encoding="utf-8")
    (WORK / "源程序提交文本.txt").write_text("\f\n".join("\n".join(pages[n]) for n in selected), encoding="utf-8")
    info = {"source_roots": ["backend/app", "web-vue3/src"], "files": manifest,
            "physical_source_lines": total_lines, "printed_rows": len(rows), "whole_source_pages": len(pages),
            "submission_pages": page_map, "normalization": "UTF-8 decode; tabs expanded to 4 columns; whitespace-only print lines omitted; long lines wrapped by display width. Comments, license notices and identifiers preserved.",
            "source_file_order": "entry point; remaining app-root files; core; models; schemas; API; browser client; model integration; services. Each group is sorted by relative path.",
            "repository_source_files_modified": False}
    (WORK / "源码导出核对.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(output.relative_to(ROOT)), "files": len(manifest), "physical_source_lines": total_lines,
            "whole_source_pages": len(pages), "submission_pages": len(selected), "last_page_rows": len(pages[-1])}


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    result = {"software_name": NAME, "version": VERSION, "design": build_design(), "source": build_source()}
    (WORK / "生成记录.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
