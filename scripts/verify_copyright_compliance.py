"""软著材料合规性自检脚本。"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "copyright"

LINES_PER_PAGE = 50

def verify():
    print("==================================================")
    print("      亲健软著全套交付材料自检报告")
    print("==================================================")

    # 1. 主要功能字数检查
    guide_path = OUT_DIR / "在线申请表填写指南.md"
    guide_text = guide_path.read_text(encoding="utf-8")

    blocks = re.findall(r"```text\n(一、系统概述[\s\S]*?)\n```", guide_text)
    if blocks:
        func_content = blocks[0].strip()
        char_count = len(func_content)
        chinese_count = len(re.findall(r"[\u4e00-\u9fa5]", func_content))
        status1 = "通过" if 500 <= char_count <= 1300 else "不通过"
        print(f"1. 主要功能字符数：{char_count} 字符（含汉字 {chinese_count} 字） [{status1}]")
        print(f"   （要求：500 ~ 1300 字）")
    else:
        print("1. 主要功能文本提取异常")

    # 2. 源码提交稿页码检查
    src_txt = (OUT_DIR / "源程序_提交稿_前30后30.txt").read_text(encoding="utf-8")
    page_headers = re.findall(r"第 (\d+) 页 / 共 60 页", src_txt)
    pages_found = [int(p) for p in page_headers]

    expected_pages = list(range(1, 61))
    is_pages_ok = (pages_found == expected_pages)
    status2 = "通过" if is_pages_ok else "不通过"
    print(f"2. 源码提交稿页码连续性：共 {len(pages_found)} 页 [{status2}]")

    # 3. 源码开源 License 头脱敏
    license_hits = re.findall(r"(?i)(mit\s+license|apache\s+license|gnu\s+general|copyright\s*\(c\)\s*\d{4}|license\s*:\s*mit)", src_txt)
    status3 = "通过" if len(license_hits) == 0 else "不通过"
    print(f"3. 源码 License 脱敏：残留 {len(license_hits)} 处 [{status3}]")

    # 4. 用户手册行数/页数（从 .md 文件读取）
    man_md = OUT_DIR / "用户手册_提交稿.md"
    des_md = OUT_DIR / "设计说明书_提交稿.md"

    man_lines = len(man_md.read_text(encoding="utf-8").splitlines()) if man_md.exists() else 0
    des_lines = len(des_md.read_text(encoding="utf-8").splitlines()) if des_md.exists() else 0

    man_pages = max(1, (man_lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE)
    des_pages = max(1, (des_lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE)

    status4 = "通过" if man_pages >= 15 else "不通过"
    status5 = "通过" if des_pages >= 15 else "不通过"
    print(f"4. 用户手册：{man_lines} 行，约 {man_pages} 页 [{status4}]")
    print(f"5. 设计说明书：{des_lines} 行，约 {des_pages} 页 [{status5}]")

    # 5. 商业模型名称脱敏
    full_docs = ""
    for p in [man_md, des_md]:
        if p.exists():
            full_docs += p.read_text(encoding="utf-8") + "\n"
    deep_hits = re.findall(r'(?i)deepseek|moonshot|kimi|openai\s*兼容', full_docs)
    status6 = "通过" if len(deep_hits) == 0 else "不通过"
    print(f"6. 商业模型名称脱敏：残留 {len(deep_hits)} 处 [{status6}]")

    # 6. DOCX 文件完整性
    docx_files = [
        "源程序_提交稿_前30后30.docx",
        "用户手册_提交稿.docx",
        "设计说明书_提交稿.docx"
    ]
    docx_ok = all((OUT_DIR / f).exists() for f in docx_files)
    print(f"7. Word 文件完整性：{'全部存在' if docx_ok else '缺失'} [{'通过' if docx_ok else '不通过'}]")

    # 7. 格式检查：确认没有旧格式残留
    issues = []
    for p in [man_md, des_md]:
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        if "  · " in content:
            issues.append(f"{p.name} 含中圆点")
        if re.search(r"^-{10,}$", content, re.MULTILINE):
            issues.append(f"{p.name} 含长横线分割")
        if "第 " in content and " 页 / 共 " in content:
            issues.append(f"{p.name} 含页眉")
    status7 = "通过" if not issues else "不通过"
    if issues:
        for i in issues:
            print(f"   - {i}")
    print(f"8. 格式清洁度（无中圆点、无横线、无页眉）：[{status7}]")

    print("==================================================")
    all_pass = all([
        blocks and 500 <= char_count <= 1300,
        is_pages_ok,
        len(license_hits) == 0,
        man_pages >= 15,
        des_pages >= 15,
        len(deep_hits) == 0,
        docx_ok,
        not issues,
    ])
    if all_pass:
        print("       全部通过")
    else:
        print("       有检查项未通过，请检查上方输出")
    print("==================================================")

if __name__ == "__main__":
    verify()
