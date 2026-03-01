"""
亲健软著申请 - 源代码文档生成脚本
使用方法：在本地命令行中运行 python gen_source_doc.py
输出：亲健_源代码文档_软著.txt
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("backend/app/main.py", "亲健 API 应用入口"),
    ("backend/app/core/config.py", "应用配置 - 通过环境变量加载"),
    ("backend/app/core/database.py", "数据库引擎与会话管理"),
    ("backend/app/core/security.py", "安全模块：密码哈希 + JWT"),
    ("backend/app/models/__init__.py", "数据模型 - SQLAlchemy ORM"),
    ("backend/app/schemas/__init__.py", "Pydantic 请求/响应模型"),
    ("backend/app/api/deps.py", "API 依赖注入：获取当前用户"),
    ("backend/app/api/v1/auth.py", "认证接口：注册 + 登录"),
    ("backend/app/api/v1/pairs.py", "配对系统接口"),
    ("backend/app/api/v1/checkins.py", "打卡系统接口"),
    ("backend/app/api/v1/reports.py", "报告接口：日报/周报/月报 + 趋势查询"),
    ("backend/app/api/v1/tree.py", "关系树游戏化接口"),
    ("backend/app/api/v1/upload.py", "文件上传接口"),
    ("backend/app/ai/__init__.py", "AI 模块 - 硅基流动多模态客户端"),
    ("backend/app/ai/reporter.py", "AI 报告生成模块"),
    ("backend/alembic/env.py", "数据库迁移配置"),
    ("web/index.html", "Web 前端页面结构"),
    ("web/css/style.css", "CSS 设计系统与样式表"),
    ("web/js/api.js", "前端 API 客户端"),
    ("web/js/app.js", "前端应用主逻辑"),
]

output_lines = []
output_lines.append("软件名称：亲健青年亲密关系健康管理平台软件")
output_lines.append("版本号：V1.0")
output_lines.append("=" * 60)
output_lines.append("")

total = 0

for rel_path, desc in FILES:
    full_path = os.path.join(PROJECT_ROOT, rel_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        print(f"  跳过（不存在）: {rel_path}")
        continue

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    total += len(lines)

    output_lines.append(f"/* {'=' * 50}")
    output_lines.append(f"   文件：{rel_path}")
    output_lines.append(f"   说明：{desc}")
    output_lines.append(f"   {'=' * 50} */")
    output_lines.append("")
    output_lines.extend(lines)
    output_lines.append("")
    output_lines.append("")

out_path = os.path.join(PROJECT_ROOT, "亲健_源代码文档_软著.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"✅ 源代码文档已生成：{out_path}")
print(f"   源代码总行数：{total}")
print(f"   文档总行数：  {len(output_lines)}")
print(f"   约 {len(output_lines) // 50 + 1} 页（每页50行）")
