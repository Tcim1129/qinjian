# Maintenance Scripts

这些脚本是一次性修补或迁移工具，保留用于回溯历史改动，但不再放在仓库根目录。

使用约定：

- 从仓库根目录运行，例如 `python tools/maintenance/fix_api_root.py`
- 仅在确认目标文件需要补丁时运行
- 执行前先查看脚本内容，避免覆盖当前分支上的手动修改
