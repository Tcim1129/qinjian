#!/usr/bin/env python3
"""快速部署脚本 - 复制修改的文件"""
import shutil
import os

# 自动查找源目录和目标目录
desktop = r'C:\Users\colour\Desktop'
src_dir = None
dst_dir = None

# 遍历桌面目录
for item in os.listdir(desktop):
    full_path = os.path.join(desktop, item)
    if not os.path.isdir(full_path):
        continue
    
    # 检查子目录
    for sub in os.listdir(full_path):
        sub_full = os.path.join(full_path, sub)
        if not os.path.isdir(sub_full):
            continue
        if '副本' in sub or 'copy' in sub.lower():
            src_backend = os.path.join(sub_full, 'backend')
            dst_backend = os.path.join(full_path, 'backend')
            if os.path.isdir(src_backend) and os.path.isdir(dst_backend):
                src_dir = src_backend
                dst_dir = dst_backend
                print(f'找到源目录: {sub_full}')
                print(f'目标目录: {full_path}')
                break
    if src_dir:
        break

if not src_dir:
    print('未找到包含 "副本" 的源目录')
    print('请手动指定路径：')
    print('  源目录: C:\\Users\\colour\\Desktop\\项目名\\副本\\backend')
    print('  目标目录: C:\\Users\\colour\\Desktop\\项目名\\backend')
    exit(1)

# 要复制的文件
files = [
    'app/main.py',
    'app/api/v1/__init__.py',
    'app/api/v1/agent.py',
    'app/api/v1/auth.py',
    'app/api/v1/checkins.py',
    'app/api/v1/pairs.py',
    'app/api/v1/reports.py',
    'app/api/v1/upload.py',
    'app/api/v1/ws.py',
    'app/models/__init__.py',
    'app/schemas/__init__.py',
    'app/services/__init__.py',
    'alembic/env.py',
    'app/services/crisis_processor.py',
    'app/services/relationship_intelligence.py',
    'app/ai/asr.py',
    'app/core/config.py',
    'requirements.txt',
    '.env.example',
]

print(f'\n开始复制文件...')
copied = 0
not_found = 0

for f in files:
    src_file = os.path.join(src_dir, f)
    dst_file = os.path.join(dst_dir, f)
    
    if os.path.exists(src_file):
        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        shutil.copy2(src_file, dst_file)
        print(f'✅ {f}')
        copied += 1
    else:
        print(f'⚠️ 未找到: {f}')
        not_found += 1

print(f'\n完成！复制 {copied} 个文件，跳过 {not_found} 个')
print('\n下一步：提交到 Git 并部署到服务器')
print('  git add .')
print('  git commit -m "sync: 同步修改的文件"')
print('  git push origin main')
