from pathlib import Path
import re

# 1. docs/用户手册.md: 将 【】 替换为中文双引号 “”
p_man = Path("docs/用户手册.md")
t_man = p_man.read_text(encoding="utf-8")
t_man = re.sub(r"【(.*?)】", r"“\1”", t_man)
p_man.write_text(t_man, encoding="utf-8")
print("docs/用户手册.md 更新完毕：方头括号已全部替换为标准中文双引号")

# 2. docs/设计和开发文档-当前实现版.md: 去除箭头与方头括号
p_des = Path("docs/设计和开发文档-当前实现版.md")
t_des = p_des.read_text(encoding="utf-8")
t_des = t_des.replace("“记录 -> 评估 -> 干预 -> 修复 -> 回看”", "“从日常记录到状态评估，再到沟通干预、矛盾修复以及历史周期回看”")
t_des = t_des.replace("“记录 → 评估 → 干预 → 修复 → 回看”", "“从日常记录到状态评估，再到沟通干预、矛盾修复以及历史周期回看”")
t_des = t_des.replace("记录 -> 评估 -> 干预 -> 修复 -> 回看", "从日常记录到状态评估，再到沟通干预、矛盾修复以及历史周期回看")
t_des = t_des.replace("记录 → 评估 → 干预 → 修复 → 回看", "从日常记录到状态评估，再到沟通干预、矛盾修复以及历史周期回看")
t_des = re.sub(r"【(.*?)】", r"“\1”", t_des)
p_des.write_text(t_des, encoding="utf-8")
print("docs/设计和开发文档-当前实现版.md 更新完毕：箭头与方头括号已替换为自然中文")

# 3. docs/数据集说明.md: 去除箭头与方头括号
p_dat = Path("docs/数据集说明.md")
t_dat = p_dat.read_text(encoding="utf-8")
t_dat = t_dat.replace("“建立关系 -> 日常记录 -> 智能整理 -> 干预建议 -> 回看归档”", "“从关系建立到日常记录，再到智能指标整理、干预建议派发以及时间轴归档”")
t_dat = t_dat.replace("“建立关系 → 日常记录 → 智能整理 → 干预建议 → 回看归档”", "“从关系建立到日常记录，再到智能指标整理、干预建议派发以及时间轴归档”")
t_dat = t_dat.replace("建立关系 -> 日常记录 -> 智能整理 -> 干预建议 -> 回看归档", "从关系建立到日常记录，再到智能指标整理、干预建议派发以及时间轴归档")
t_dat = t_dat.replace("建立关系 → 日常记录 → 智能整理 → 干预建议 → 回看归档", "从关系建立到日常记录，再到智能指标整理、干预建议派发以及时间轴归档")
t_dat = re.sub(r"【(.*?)】", r"“\1”", t_dat)
p_dat.write_text(t_dat, encoding="utf-8")
print("docs/数据集说明.md 更新完毕：箭头已替换为自然中文")

# 4. docs/页面功能说明.md: 检查并替换箭头与方头括号
p_pg = Path("docs/页面功能说明.md")
t_pg = p_pg.read_text(encoding="utf-8")
t_pg = t_pg.replace("“输邀请码立即成功”，而是“加入预览 -> 发起加入请求 -> 对方确认后生效”", "“输入邀请码立即成功”，而是“从加入预览到发起申请，再经由对端确认后正式生效”")
t_pg = t_pg.replace("“输邀请码立即成功”，而是“加入预览 → 发起加入请求 → 对方确认后生效”", "“输入邀请码立即成功”，而是“从加入预览到发起申请，再经由对端确认后正式生效”")
t_pg = re.sub(r"【(.*?)】", r"“\1”", t_pg)
p_pg.write_text(t_pg, encoding="utf-8")
print("docs/页面功能说明.md 更新完毕：自然中文更新成功")
