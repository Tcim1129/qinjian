"""扫描交付文档中的禁词和格式问题。"""

from pathlib import Path
import re

out_dir = Path("output/copyright")

docs = [
    "用户手册_提交稿.md",
    "设计说明书_提交稿.md",
    "源程序_提交稿_前30后30.txt",
    "在线申请表填写指南.md",
    "功能源码证据映射表.md",
]

forbidden_words = [
    "答辩",
    "路演",
    "比赛",
    "评委",
    "C:\\Users\\",
    "亲健web",
    "==============================",
]

leaks = 0
for doc in docs:
    p = out_dir / doc
    if not p.exists():
        continue
    content = p.read_text(encoding="utf-8")
    for word in forbidden_words:
        matches = [m.start() for m in re.finditer(re.escape(word), content)]
        if matches:
            print(f'[问题] 在 {doc} 中发现 {len(matches)} 处 "{word}"')
            leaks += len(matches)

if leaks == 0:
    print("全部干净，0 处禁词")
else:
    print(f"共 {leaks} 处需要修复")
