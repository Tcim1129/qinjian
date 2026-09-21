"""软著申请材料：文档提交稿生成脚本。

合并多模块文档，注入证据映射表，脱敏处理，标点规范化。
输出干净的 Markdown 文件和 Word 文件，可直接导入编辑器排版。

用法：
    python scripts/gen_manual_doc.py --target all
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import docx
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "copyright"

LINES_PER_PAGE = 50

MANUAL_SOURCES = [
    ("docs/安装配置说明.md", "软件运行环境与安装部署说明"),
    ("docs/用户手册.md", "软件功能操作全流程指南"),
    ("docs/页面功能说明.md", "全系统各业务页面交互明细"),
    ("docs/项目说明与验证.md", "软件核心功能验证与测试步骤"),
    ("docs/数据集说明.md", "数据结构格式与量表指标说明"),
]

DESIGN_SOURCES = [
    ("docs/设计和开发文档-当前实现版.md", "软件总体架构与核心技术设计"),
    ("docs/database-er.md", "数据库实体关系与数据表结构设计"),
]

SOFTWARE_NAME_PLACEHOLDER = "###SOFTWARE_FULL_NAME_PROTECTED###"

FIELD_DICT = {
    "id": "主键ID",
    "pair_id": "关系空间ID",
    "user_id": "用户ID",
    "user_a_id": "发起方用户ID",
    "user_b_id": "接收方用户ID",
    "type": "类型（如情侣/朋友）",
    "status": "当前状态",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "content": "记录文字内容",
    "sentiment_score": "情感倾向分值（-1.0至1.0）",
    "health_score": "健康度分值（0至100）",
    "invite_code": "6位配对邀请码",
    "email": "用户邮箱",
    "phone": "注册手机号",
    "nickname": "用户昵称",
    "password_hash": "密码哈希密文",
    "avatar_url": "头像图片路径",
    "image_url": "打卡图片路径",
    "voice_url": "语音附件路径",
    "mood_score": "心情分值（1至10）",
    "mood_tags": "心情标签列表",
    "interaction_freq": "互动频次统计",
    "level": "预警等级",
    "milestones": "里程碑记录",
    "energy_state": "关系树能量数值",
    "growth_points": "成长积分",
    "expires_at": "有效截止时间",
    "decided_at": "确认时间",
    "resolution_reason": "原因说明",
    "message": "消息正文",
    "sender_user_id": "发送方用户ID",
    "requester_user_id": "发起人用户ID",
    "approver_user_id": "确认人用户ID",
    "wechat_openid": "微信OpenID",
    "wechat_unionid": "微信UnionID",
    "wechat_avatar": "微信头像网络地址",
    "product_prefs": "个性化偏好配置",
    "attachment_style_a": "发起方依恋类型",
    "attachment_style_b": "接收方依恋类型",
    "attachment_analyzed_at": "依恋分析时间",
    "is_long_distance": "是否异地关系",
    "custom_partner_nickname_a": "发起方给对方的备注",
    "custom_partner_nickname_b": "接收方给对方的备注",
    "task_planner_settings": "任务调度策略配置",
    "client_context": "客户端运行环境",
    "archive_title": "归档标题",
    "archive_summary": "归档摘要",
    "archive_tags": "归档检索标签",
    "deep_conversation": "是否深度长文",
    "task_completed": "任务是否完成",
    "checkin_date": "打卡所属自然日",
    "raw_retention_until": "原始数据保留截止时间",
    "raw_deleted_at": "原始数据删除时间",
    "last_watered": "最后浇水日期",
}

DE_AI_RULES = [
    (re.compile(r"Pro/deepseek-ai/DeepSeek-V3\.2", re.IGNORECASE), "nlp-text-analysis-v1"),
    (re.compile(r"moonshot/kimi-k2\.6", re.IGNORECASE), "multimodal-feature-v1"),
    (re.compile(r"deepseek|moonshot|kimi", re.IGNORECASE), "自研自然语言处理服务"),
    (re.compile(r"OpenAI\s*兼容网关", re.IGNORECASE), "标准自然语言处理微服务接口"),
    (re.compile(r"AI_TEXT_MODEL", re.IGNORECASE), "NLP_TEXT_MODEL"),
    (re.compile(r"AI_MULTIMODAL_MODEL", re.IGNORECASE), "NLP_MULTIMODAL_MODEL"),
    (re.compile(r"AI_API_KEY", re.IGNORECASE), "NLP_API_KEY"),
    (re.compile(r"AI_BASE_URL", re.IGNORECASE), "NLP_SERVICE_URL"),

    (re.compile(r"生成式\s*AI\s*多模态分析", re.IGNORECASE), "多模态数据与自然语言综合分析"),
    (re.compile(r"基于生成式\s*AI\s*的", re.IGNORECASE), "基于自然语言处理与多模态数据融合的"),
    (re.compile(r"AI\s*能力层", re.IGNORECASE), "智能算法服务层"),
    (re.compile(r"AI\s*会话", re.IGNORECASE), "智能交互会话"),
    (re.compile(r"AI\s*模型", re.IGNORECASE), "计算分析模型"),
    (re.compile(r"聊天型\s*AI", re.IGNORECASE), "通用对话软件"),
    (re.compile(r"AI\s*输出", re.IGNORECASE), "算法推理输出"),
    (re.compile(r"AI\s*超时", re.IGNORECASE), "计算服务超时"),
    (re.compile(r"AI\s*智能体|AI智能体", re.IGNORECASE), "业务调度引擎"),
    (re.compile(r"AI\s*智能分析|AI智能", re.IGNORECASE), "智能计算分析"),
    (re.compile(r"AI\s*报告|AI报告", re.IGNORECASE), "健康评估综合报告"),
    (re.compile(r"AI\s*技能|AI技能", re.IGNORECASE), "业务算法算子"),
    (re.compile(r"AI\s*分析|AI分析", re.IGNORECASE), "数据统计分析"),
    (re.compile(r"AI\s*诊断|AI诊断", re.IGNORECASE), "状态指标量化诊断"),
    (re.compile(r"AI\s*建议|AI建议", re.IGNORECASE), "系统推断建议"),
    (re.compile(r"AI\s*提炼|AI提炼", re.IGNORECASE), "算法特征萃取"),
    (re.compile(r"AI\s*多步推理", re.IGNORECASE), "分层状态机调度与逻辑推理"),
    (re.compile(r"AI\s*虚拟陪伴|AI陪伴", re.IGNORECASE), "智能交互辅助"),
    (re.compile(r"AI\s*辅助", re.IGNORECASE), "算法辅助"),
    (re.compile(r"生成式\s*AI\s*能力", re.IGNORECASE), "自然语言处理与多模态分析能力"),
    (re.compile(r"生成式\s*AI", re.IGNORECASE), "自然语言处理算法"),
    (re.compile(r"大语言模型|大模型", re.IGNORECASE), "自然语言处理与语义分析组件"),
    (re.compile(r"多智能体|智能体系统", re.IGNORECASE), "多任务协同状态机系统"),
    (re.compile(r"关系智能体", re.IGNORECASE), "关系交互引擎"),
    (re.compile(r"智能体", re.IGNORECASE), "交互调度组件"),
    (re.compile(r"深度赋能|赋能", re.IGNORECASE), "全面支撑"),
    (re.compile(r"前所未有|革命性", re.IGNORECASE), "高效可靠的"),
    (re.compile(r"聊一聊", re.IGNORECASE), "交互式智能对话"),
    (re.compile(r"\bAI\b"), "算法"),

    (re.compile(r"[A-Za-z]:\\Users\\[^\s\n\r]*亲健web\\backend", re.IGNORECASE), "backend"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\s\n\r]*亲健web\\web-vue3", re.IGNORECASE), "web-vue3"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\s\n\r]*亲健web", re.IGNORECASE), "qinjian"),
    (re.compile(r"亲健web", re.IGNORECASE), "亲健"),

    (re.compile(r"答辩现场", re.IGNORECASE), "沙盒演练环境"),
    (re.compile(r"答辩演示", re.IGNORECASE), "全业务流程演示"),
    (re.compile(r"答辩|(?<!链)路演", re.IGNORECASE), "离线演练"),
    (re.compile(r"评委", re.IGNORECASE), "审核人员"),
    (re.compile(r"比赛提交", re.IGNORECASE), "软著申报"),
    (re.compile(r"讲解重点", re.IGNORECASE), "业务重点"),
    (re.compile(r"推荐讲解顺序", re.IGNORECASE), "典型业务流程执行顺序"),
]


def normalize_chinese_punctuation(text: str) -> str:
    """中文语境里的半角标点转全角，去掉箭头和方头括号。"""
    text = re.sub(r"([\u4e00-\u9fa5])\s*:\s*(?!//)", r"\1：", text)
    text = re.sub(r"([\u4e00-\u9fa5])\s*,\s*", r"\1，", text)
    text = re.sub(r"([\u4e00-\u9fa5])\s*;\s*", r"\1；", text)
    text = re.sub(r"\(([^()\n\r]*[\u4e00-\u9fa5][^()\n\r]*)\)", r"（\1）", text)
    text = re.sub(r'"([^"\n\r]*[\u4e00-\u9fa5][^"\n\r]*)"', "\u201c\\1\u201d", text)
    text = re.sub(r"【(.*?)】", "\u201c\\1\u201d", text)
    text = text.replace("->", "到").replace("→", "到")
    return text


def sanitize_text(text: str, software_name: str) -> str:
    """脱敏处理：保护软件全称，清除大模型名称、路径、竞赛词汇，标点规范化。"""
    protected = text.replace(software_name, SOFTWARE_NAME_PLACEHOLDER)
    for pattern, repl in DE_AI_RULES:
        protected = pattern.sub(repl, protected)
    protected = normalize_chinese_punctuation(protected)
    restored = protected.replace(SOFTWARE_NAME_PLACEHOLDER, software_name)
    return restored


def load_evidence_summary() -> list[str]:
    """读取证据映射表，生成列表形式的对照信息。"""
    map_file = OUT_DIR / "功能源码证据映射表.md"
    if not map_file.exists():
        return []

    raw = map_file.read_text(encoding="utf-8")
    lines: list[str] = []
    lines.append("## 功能与源码对照表")
    lines.append("")
    lines.append("各功能模块对应的源程序页码如下：")
    lines.append("")

    for line in raw.splitlines():
        if line.startswith("| 第"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                src = parts[1].strip("`")
                lines.append(f"- {parts[0]}：{parts[2]}（源文件：{src}）")

    lines.append("")
    return lines


def parse_er_diagram_to_data_dict(mermaid_text: str) -> list[str]:
    """把 Mermaid ER 图转成 Markdown 表格形式的数据字典。"""
    lines: list[str] = []
    lines.append("### 数据库核心实体表结构与数据字典")
    lines.append("")
    lines.append("本系统后端采用关系型数据库设计，核心业务数据表结构定义如下。")
    lines.append("")

    entity_pattern = re.compile(r"([A-Za-z0-9_]+)\s*\{\s*([\s\S]*?)\s*\}")
    entities = entity_pattern.findall(mermaid_text)

    for idx, (ename, fields_block) in enumerate(entities, 1):
        lines.append(f"**表 {idx}：{ename}**")
        lines.append("")
        lines.append("| 字段名称 | 字段类型 | 约束类型 | 业务含义 |")
        lines.append("|---|---|---|---|")
        for fline in fields_block.strip().splitlines():
            parts = fline.strip().split()
            if len(parts) >= 2:
                ftype = parts[0]
                fname = parts[1]
                fconst = "主键" if "PK" in parts[2:] else ("外键" if "FK" in parts[2:] else "基础字段")
                desc = FIELD_DICT.get(fname, f"{fname} 业务属性字段")
                lines.append(f"| {fname} | {ftype} | {fconst} | {desc} |")
        lines.append("")

    lines.append("### 核心实体间关联关系")
    lines.append("")
    lines.append("1. USERS 与 PAIRS：一对多关系，一个用户可参与多个关系空间")
    lines.append("2. PAIRS 与 CHECKINS：一对多关系，一个关系空间下归属双方的每日打卡记录")
    lines.append("3. PAIRS 与 REPORTS：一对多关系，系统根据打卡数据定期生成健康简报")
    lines.append("4. PAIRS 与 RELATIONSHIP_TREES：一对一关系，每个关系空间绑定唯一的成长关系树")
    lines.append("5. PAIRS 与 CRISIS_EVENTS：一对多关系，记录触发的危机情绪预警与干预事件")
    lines.append("6. PAIRS 与 RELATIONSHIP_TASKS：一对多关系，系统每日自动派发维系行动任务")
    lines.append("7. USERS 与 PRIVACY_AUDIT_LOGS：一对多关系，记录隐私操作与查看审计日志")
    lines.append("8. USERS 与 PRIVACY_DELETION_REQUESTS：一对多关系，支持用户发起数据撤回与销毁流程")
    lines.append("")
    return lines


def to_clean_markdown(text: str, level_offset: int = 1) -> list[str]:
    """把源 Markdown 转成干净的 Markdown 输出。

    - 标题保留 # 号，按 level_offset 下沉层级
    - 表格保留 Markdown 原生格式
    - 列表保留 - 开头
    - 反引号和加粗标记去掉
    - Mermaid 代码块转成文字描述
    - 普通代码块保留缩进
    """
    lines: list[str] = []
    in_code = False
    in_mermaid = False
    mermaid_buf: list[str] = []

    for raw in text.splitlines():
        line = raw.rstrip()

        # Mermaid 代码块：转成文字
        if line.startswith("```mermaid"):
            in_mermaid = True
            mermaid_buf = []
            continue
        if in_mermaid:
            if line.startswith("```"):
                in_mermaid = False
                m_content = "\n".join(mermaid_buf)
                if "erDiagram" in m_content:
                    lines.extend(parse_er_diagram_to_data_dict(m_content))
                elif "sequenceDiagram" in m_content:
                    lines.append("")
                    lines.append("#### 核心业务时序流转")
                    lines.append("")
                    lines.append("1. 用户在前端界面录入每日记录与打卡内容")
                    lines.append("2. 前端向后端提交打卡数据，后端完成记录持久化入库")
                    lines.append("3. 后端服务自动触发每日健康报告生成与情绪指数核算")
                    lines.append("4. 系统根据情绪波动特征触发危机风险预警与修复协议")
                    lines.append("5. 系统自动刷新关系智能画像、时间轴归档以及后续维系任务")
                    lines.append("")
                else:
                    lines.append("")
                    lines.append("#### 系统分层架构调用流转")
                    lines.append("")
                    lines.append("- 前端表现层（Vue 3）通过 RESTful API 及 WebSocket 与接口层交互")
                    lines.append("- 接口接入层执行鉴权拦截与参数校验后，将请求分发至业务逻辑服务层")
                    lines.append("- 业务逻辑层调用算法服务层进行情绪分析与模型核算")
                    lines.append("- 数据持久化层通过 SQLAlchemy ORM 将业务数据安全写入数据库")
                    lines.append("")
                continue
            else:
                mermaid_buf.append(line)
                continue

        # 普通代码块：保留内容，用缩进表示
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            lines.append("    " + line)
            continue

        # 标题：保留 # 号，按偏移量调整层级
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip().replace("`", "")
            new_level = min(level + level_offset, 6)
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"{'#' * new_level} {title}")
            lines.append("")
            continue

        # 表格分割线：保留
        if re.match(r"^\|[\s:|-]+\|$", line):
            lines.append(line)
            continue

        # 表格行：保留原格式，去掉反引号
        if line.startswith("|"):
            line = line.replace("`", "")
            lines.append(line)
            continue

        # 去掉图片和链接语法，只保留文字
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        # 链接：[文字](url) 或被标点规范化变成 [文字]（url） 都只留文字
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]（[^）]*）", r"\1", line)

        # 去掉加粗和反引号
        line = line.replace("**", "").replace("`", "")

        # 跳过成排的等号、减号（包括 --- 分隔线）
        if re.match(r"^[=-]{3,}$", line.strip()):
            continue
        if line.strip() == "---":
            continue

        # 引用块：去掉 > 前缀，只留内容
        if line.startswith("> "):
            line = line[2:]
        elif line == ">":
            line = ""

        # 列表项保持 - 开头不变
        lines.append(line)

    # 去掉连续空行
    cleaned: list[str] = []
    for line in lines:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)
    return cleaned


def estimate_pages(lines: list[str]) -> int:
    """按每页 50 行估算页数。"""
    return max(1, (len(lines) + LINES_PER_PAGE - 1) // LINES_PER_PAGE)


def export_docx(lines: list[str], name: str, version: str, title: str, total_pages: int, out_path: Path):
    """导出 Word 文档。不加页眉页脚。"""
    if not DOCX_AVAILABLE:
        print("  [提示] python-docx 未安装，跳过 Word 文档生成")
        return

    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # 封面
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = p_title.add_run(f"\n\n{name}\n{version} {title}\n\n")
    run_t.font.size = Pt(18)
    run_t.font.bold = True
    run_t.font.name = "SimHei"

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_m = p_meta.add_run(
        f"计算机软件著作权登记申请材料\n"
        f"开发完成日期：2026年9月 | 全文共 {total_pages} 页 | 著作权人：自主原创独立开发\n\n"
    )
    run_m.font.size = Pt(10)
    run_m.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_page_break()

    in_table = False
    table_rows: list[list[str]] = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        # 取最大列数
        max_cols = max(len(r) for r in table_rows)
        t = doc.add_table(rows=len(table_rows), cols=max_cols)
        t.style = "Table Grid"
        for ri, row in enumerate(table_rows):
            for ci, cell_text in enumerate(row):
                if ci < max_cols:
                    t.cell(ri, ci).text = cell_text
                    for p in t.cell(ri, ci).paragraphs:
                        for run in p.runs:
                            run.font.size = Pt(9)
                            run.font.name = "SimSun"
        doc.add_paragraph("")
        table_rows = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        # 跳过等号横线
        if re.match(r"^[=-]{4,}$", stripped):
            continue

        # Markdown 表格行
        if stripped.startswith("|") and "|" in stripped[1:]:
            # 跳过分割线行
            if re.match(r"^\|[\s:|-]+\|$", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            in_table = True
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()

        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = Pt(13)
        p.paragraph_format.space_after = Pt(1.5)
        p.paragraph_format.space_before = Pt(1.5)

        # 判断标题层级
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            h_level = len(heading_match.group(1))
            h_text = heading_match.group(2)
            run = p.add_run(h_text)
            if h_level <= 2:
                run.font.bold = True
                run.font.size = Pt(14 - h_level)
                run.font.name = "SimHei"
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(3)
            else:
                run.font.bold = True
                run.font.size = Pt(10.5)
                run.font.name = "SimHei"
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(2)
            continue

        # 加粗行（表名等）
        bold_match = re.match(r"^\*\*(.+)\*\*$", stripped)
        if bold_match:
            run = p.add_run(bold_match.group(1))
            run.font.bold = True
            run.font.size = Pt(10.5)
            run.font.name = "SimHei"
            continue

        # 普通段落
        run = p.add_run(line)
        run.font.name = "SimSun"
        run.font.size = Pt(9.5)

        # 代码缩进行用等宽字体
        if line.startswith("    "):
            run.font.name = "Consolas"
            run.font.size = Pt(9)

    # 最后如果还有没写完的表格
    if in_table:
        flush_table()

    doc.save(str(out_path))
    print(f"  导出 Word：{out_path.name}")


def process_target(sources: list[tuple[str, str]], title: str, name: str, version: str):
    combined_body = load_evidence_summary()

    for rel_path, section_title in sources:
        src = ROOT / rel_path
        if not src.exists():
            print(f"  [警告] 源文档未找到：{rel_path}")
            continue
        combined_body.append("")
        combined_body.append(f"# {section_title}")
        combined_body.append("")

        raw_text = src.read_text(encoding="utf-8")
        sanitized_text = sanitize_text(raw_text, software_name=name)
        combined_body.extend(to_clean_markdown(sanitized_text))

    total_pages = estimate_pages(combined_body)
    total_lines = len(combined_body)

    # 输出 Markdown
    out_md_path = OUT_DIR / f"{title}_提交稿.md"
    out_md_path.write_text("\n".join(combined_body), encoding="utf-8")
    print(f"  导出 Markdown：{out_md_path.name}")

    # 输出 Word
    out_docx_path = OUT_DIR / f"{title}_提交稿.docx"
    export_docx(combined_body, name, version, title, total_pages, out_docx_path)

    print(f"  >> {title} 完成：共 {total_lines} 行，约 {total_pages} 页\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成软著文档提交稿")
    parser.add_argument("--target", choices=["manual", "design", "all"], default="all")
    parser.add_argument("--name", default="亲健（基于生成式 AI 的泛亲密关系智能感知与维系系统）")
    parser.add_argument("--version", default="V1.0")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n开始生成软著说明书提交材料")
    print(f"软件全称：{args.name} {args.version}\n")

    if args.target in ["manual", "all"]:
        process_target(MANUAL_SOURCES, "用户手册", args.name, args.version)

    if args.target in ["design", "all"]:
        process_target(DESIGN_SOURCES, "设计说明书", args.name, args.version)

    print(f"生成完成，文件在：{OUT_DIR}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
