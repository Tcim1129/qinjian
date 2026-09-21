"""Check generated artifacts against the current manuscript and source snapshot."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pdfplumber
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pypdf import PdfReader

from build_copyright_package import MANUSCRIPT, NAME, PRINT_COLUMNS, ROOT, ROWS_PER_PAGE, STAGE, VERSION, WORK, print_chunks


def compact(text):
    return re.sub(r"\s+", "", text)


def main():
    manifest = json.loads((WORK / "源码导出核对.json").read_text(encoding="utf-8"))
    full_rows = []
    for item in manifest["files"]:
        raw = (ROOT / item["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"], item["file"] + " changed"
        for line in raw.decode("utf-8-sig").splitlines():
            chunks = print_chunks(line)
            if line.strip():
                assert "".join(chunks) == line.expandtabs(4)
            full_rows.extend(chunks)
    assert len(full_rows) == manifest["printed_rows"]
    all_pages = [full_rows[i:i + ROWS_PER_PAGE] for i in range(0, len(full_rows), ROWS_PER_PAGE)]
    page_indices = [row["whole_source_page"] - 1 for row in manifest["submission_pages"]]
    expected_indices = list(range(30)) + list(range(len(all_pages) - 30, len(all_pages))) if len(all_pages) > 60 else list(range(len(all_pages)))
    assert page_indices == expected_indices
    expected_pages = [all_pages[i] for i in expected_indices]
    expected_rows = [line for page in expected_pages for line in page]
    source_doc = Document(STAGE / "源程序_提交稿_前30后30.docx")
    assert [p.text for p in source_doc.paragraphs] == expected_rows, "DOCX source content drift"
    source_pdf_path = STAGE / "源程序_提交稿_前30后30.pdf"
    source_pdf = PdfReader(source_pdf_path)
    assert len(source_pdf.pages) == len(expected_pages) == 60
    counts = []
    with pdfplumber.open(source_pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            body = page.crop((45, 58, 550, 770))
            actual = body.extract_text(x_tolerance=1, y_tolerance=2) or ""
            expected = "\n".join(expected_pages[i])
            if compact(actual) != compact(expected):
                (WORK / f"page-{i+1}-extracted.txt").write_text(actual, encoding="utf-8")
                raise AssertionError(f"PDF source content mismatch at page {i+1}")
            count = len([line for line in actual.splitlines() if line.strip()])
            assert count == len(expected_pages[i]), (i + 1, count, len(expected_pages[i]))
            counts.append(count)
    design_path = STAGE / "设计说明书_提交稿.docx"
    design = Document(design_path)
    manuscript_items = []
    for line in MANUSCRIPT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or re.match(r"^\|[\s:|\-]+\|$", line):
            continue
        if line.startswith("|"):
            manuscript_items.extend(cell.strip() for cell in line.strip("|").split("|"))
        elif line.startswith("!["):
            manuscript_items.append(re.match(r"^!\[(.*)\]", line).group(1))
        else:
            manuscript_items.append(re.sub(r"^#{1,3} ", "", line))
    document_items = []
    for element in design.element.body:
        if element.tag.endswith("}p"):
            paragraph = Paragraph(element, design)
            value = paragraph.text
            if paragraph.style.name.lower().startswith("toc") or value == "目录":
                continue
            if value.strip():
                document_items.append(value)
        elif element.tag.endswith("}tbl"):
            document_items.extend(cell.text for row in Table(element, design).rows for cell in row.cells)
    assert document_items == manuscript_items, "Design DOCX differs from edited manuscript"
    text = "\n".join([p.text for p in design.paragraphs] + [c.text for t in design.tables for row in t.rows for c in row.cells])
    for bad in ["截图预留", "待补充", "去AI", "去 AI", "AIGC", "工业级", "业务属性字段", "基础字段", "自研自然语言处理服务", "6 位", "6位", "65,700"]:
        assert bad not in text, bad
    assert "10 位" in text
    assert "本人" not in text or "本人审计" in text
    assert len(design.tables) == 8
    assert len(design.inline_shapes) == 7
    assert len(design.sections) == 2
    chapters = [p for p in design.paragraphs if p.style.name == "Heading 1"]
    assert len(chapters) == 13
    assert all(not p.paragraph_format.page_break_before for p in chapters[1:])
    with ZipFile(design_path) as z:
        xml = z.read("word/document.xml").decode()
        assert "w:ins " not in xml and "w:del " not in xml
        assert "word/comments.xml" not in z.namelist()
    design_pdf = PdfReader(STAGE / "设计说明书_提交稿.pdf")
    design_rows = []
    design_bodies = []
    with pdfplumber.open(STAGE / "设计说明书_提交稿.pdf") as pdf:
        for index, page in enumerate(pdf.pages):
            body = page.crop((45, 55, 550, 788)).extract_text() or ""
            design_bodies.append(body)
            count = len([line for line in body.splitlines() if line.strip()])
            assert count > 0, "Blank design page"
            design_rows.append(count)
    design_pdf_body = compact("\n".join(design_bodies))
    for paragraph in design.paragraphs:
        if paragraph.style.name.lower().startswith("toc"):
            continue
        assert compact(paragraph.text) in design_pdf_body, "Design PDF lost paragraph: " + paragraph.text[:70]
    toc = [p.text.rsplit("\t", 1) for p in design.paragraphs if p.style.name.lower().startswith("toc")]
    assert len(toc) == 13
    for title, number in toc:
        body = design_bodies[int(number) - 1]
        assert compact(title) in compact(body), (title, number)
    assert sum(len(page.images) for page in design_pdf.pages) == 7
    illustrated_pages = [i + 1 for i, page in enumerate(design_pdf.pages) if page.images]
    plain_body_pages = [i + 1 for i in range(1, len(design_pdf.pages)) if i + 1 not in illustrated_pages]
    assert all(design_rows[i - 1] >= 30 for i in plain_body_pages), "Plain body page below 30 rows"
    # Table cells can wrap on the same visual row as neighbouring cells. Compare
    # their character coverage as well as the exact DOCX content checked above.
    missing = Counter(compact("".join(document_items))) - Counter(design_pdf_body)
    assert not missing, "Design PDF missing manuscript characters: " + repr(missing)
    for pdf in (design_pdf, source_pdf):
        fonts = {str(font.get_object().get("/BaseFont")) for page in pdf.pages
                 for font in page["/Resources"].get_object()["/Font"].get_object().values()}
        assert fonts and all("SimSun" in name for name in fonts), fonts
        for index, page in enumerate(pdf.pages, 1):
            page_text = compact(page.extract_text())
            assert compact(NAME + VERSION) in page_text
            assert f"第{index}页/共{len(pdf.pages)}页" in page_text
    for doc in (design, source_doc):
        header = doc.sections[0].header.paragraphs[0].text
        assert NAME in header and VERSION in header
    assert design.styles["Normal"].font.size.pt == 12
    assert design.styles["Normal"].paragraph_format.first_line_indent.pt == 24
    assert source_doc.styles["Normal"].font.size.pt == 10.5
    source_indent = source_doc.styles["Normal"].paragraph_format.first_line_indent
    assert source_indent is None or source_indent.pt == 0
    for table in design.tables:
        assert table.alignment == WD_TABLE_ALIGNMENT.CENTER
        assert all(cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER for cell in table.rows[0].cells)
    result = {"source_snapshot_files": len(manifest["files"]),
              "source_snapshot_hashes_match": True,
              "source_docx_matches_current_source": True,
              "source_pdf_all_pages_match_docx": True,
              "correct_first_30_and_last_30_pages": True,
              "source_pdf_pages": len(source_pdf.pages),
              "source_print_rows_per_page": counts,
              "design_pdf_pages": len(design_pdf.pages),
              "design_docx_matches_manuscript": True,
              "design_pdf_contains_all_manuscript_text": True,
              "design_print_rows_per_page": design_rows,
              "design_tables": len(design.tables),
              "screenshots": 7,
              "toc_page_numbers_verified": True,
              "chapters_flow_continuously": True,
              "short_pages": [i+1 for i, count in enumerate(design_rows) if count < 30],
              "plain_body_pages_at_least_30_rows": True,
              "illustrated_pages": illustrated_pages,
              "short_page_note": "Only the contents page and screenshot pages have fewer than 30 extracted text rows; images are not counted as text rows. No universal acceptance claim.",
              "all_pdf_fonts_simsun": True,
              "design_body_size_pt": 12,
              "source_body_size_pt": 10.5,
              "design_first_line_indent_pt": 24,
              "tables_and_headers_centered": True,
              "manual_visual_review": "Recorded separately; this script does not establish visual quality.",
              "runtime_business_test": "Not part of this document-only verification."}
    (WORK / "核对结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
