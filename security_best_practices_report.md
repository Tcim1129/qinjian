# 亲健项目安全审计报告

审计日期：2026-03-22

## 执行摘要

本次对 `backend`、`web`、`miniprogram`、`qinjian-app`、部署脚本与容器编排进行了面向实战的安全审计与修复。已完成的修复覆盖权限绕过、硬编码凭据、弱默认密钥、弱邀请码、敏感字段暴露、客户端令牌持久化以及已知漏洞依赖等问题。

本轮修复后，后端测试 `20/20` 通过，`pip-audit` 结果为 `No known vulnerabilities found`，关键 Python 文件语法编译通过。报告中不展示任何真实密钥、密码或令牌内容。

## 高危问题

### QJ-001 部署脚本存在硬编码凭据与未知主机自动信任

影响：可直接导致服务器凭据泄露，且在中间人攻击场景下被接管部署链路。

状态：已修复

修复位置：

- `deploy_expect.exp:4`
- `deploy_expect.exp:22`
- `deploy_expect.exp:23`
- `deploy_expect.exp:24`
- `deploy_expect.exp:25`
- `deploy_manual.py:7`
- `deploy_manual.py:14`
- `deploy_manual.py:17`
- `deploy_manual.py:22`
- `deploy_manual.py:23`
- `deploy_current_workspace.py:75`
- `deploy_current_workspace.py:76`
- `remote_exec.py:12`
- `remote_exec.py:13`
- `remote_recover_compose.py:13`
- `remote_recover_compose.py:14`

处理结果：

- 移除了部署脚本中的硬编码主机、账号、口令。
- 统一改为从 `QJ_REMOTE_*` 环境变量读取敏感信息。
- SSH 主机校验改为 `RejectPolicy`，不再自动信任未知指纹。

### QJ-002 任务接口存在对象级越权风险

影响：同一关系内的用户可读取、完成或反馈不属于自己的任务，属于典型的对象级授权缺陷。

状态：已修复

修复位置：

- `backend/app/api/v1/tasks.py:47`
- `backend/app/api/v1/tasks.py:51`
- `backend/app/api/v1/tasks.py:78`
- `backend/app/api/v1/tasks.py:267`
- `backend/app/api/v1/tasks.py:304`

处理结果：

- 增加任务可见性判断，仅允许查看共享任务或本人所属任务。
- 增加操作者校验，阻断对伴侣专属任务的完成与反馈写入。

### QJ-003 生产配置存在弱默认密钥与弱默认数据库口令

影响：攻击者可利用公开默认值直接构造 JWT、撞库数据库连接或在误配置环境下完成提权。

状态：已修复

修复位置：

- `docker-compose.yml:8`
- `docker-compose.yml:28`
- `docker-compose.yml:29`
- `backend/wait-for-db.sh:17`
- `backend/app/main.py:62`
- `backend/app/main.py:76`
- `backend/app/main.py:78`
- `backend/app/core/config.py:14`

处理结果：

- `docker-compose.yml` 不再回落到公开弱口令，未提供 `DB_PASSWORD`/`SECRET_KEY` 时直接失败。
- `wait-for-db.sh` 移除弱默认数据库密码。
- 生产态新增 `SECRET_KEY` 长度下限校验，不足 32 字节拒绝启动。
- 访问令牌有效期从 7 天收紧为 24 小时。

### QJ-004 配对邀请码熵值过低，易被穷举

影响：原 6 位纯数字邀请码被批量枚举的成本过低，可导致未授权配对或恶意撞码。

状态：已修复

修复位置：

- `backend/app/api/v1/pairs.py:22`
- `backend/app/api/v1/pairs.py:25`
- `backend/app/api/v1/pairs.py:90`
- `backend/app/models/__init__.py:116`
- `backend/alembic/versions/2026_03_22_0009_harden_pair_invite_code.py:15`
- `backend/alembic/versions/2026_03_22_0009_harden_pair_invite_code.py:38`

处理结果：

- 邀请码升级为 10 位高熵字母数字组合，并排除易混淆字符。
- 入库字段长度同步扩容为 12。
- 加入时统一做 `strip().upper()` 标准化处理。

### QJ-005 DEBUG 管理员兜底逻辑可导致越权

影响：旧逻辑在调试场景下可能让普通登录用户获得管理能力，属于高危权限边界错误。

状态：已修复

修复位置：

- `backend/app/api/v1/admin.py:103`
- `backend/app/api/v1/admin.py:108`
- `backend/app/api/v1/admin.py:110`

处理结果：

- 移除了“未配置管理员邮箱时放开权限”的调试兜底行为。
- 当前仅允许显式配置的管理员邮箱集合进入管理接口。

### QJ-006 后端依赖存在已知漏洞

影响：JWT、上传链路和框架依赖存在公开漏洞时，容易被用于伪造令牌、绕过校验或扩大攻击面。

状态：已修复

修复位置：

- `backend/requirements.txt:1`
- `backend/requirements.txt:4`
- `backend/requirements.txt:9`
- `backend/requirements.txt:11`
- `backend/app/core/security.py:25`
- `backend/app/core/security.py:38`

处理结果：

- 将 JWT 实现从 `python-jose` 切换为 `PyJWT==2.12.0`，同时移除不必要的 `ecdsa` 依赖链。
- 升级 `fastapi` 与 `python-multipart`。
- 删除未使用的 `requests` 直接依赖。
- 新增令牌必需声明校验，拒绝无效/畸形令牌。

## 中风险问题

### QJ-007 认证响应暴露第三方身份标识

影响：客户端不需要直接持有 `wechat_openid`/`wechat_unionid`，继续暴露会扩大隐私泄露面。

状态：已修复

修复位置：

- `backend/app/api/v1/auth.py:36`
- `backend/app/api/v1/auth.py:38`
- `backend/app/schemas/__init__.py:58`
- `web/js/app.js:994`
- `qinjian-app/qingjian app/pages/profile/index.vue:243`

处理结果：

- 服务端响应改为只下发 `wechat_bound` 布尔值。
- 前端展示逻辑已从原始标识字段切换到 `wechat_bound`。

### QJ-008 请求模型允许额外字段，存在批量赋值/越权扩展面

影响：宽松请求模型会让未预期字段混入接口处理流程，增加越权写入和未来回归风险。

状态：已修复

修复位置：

- `backend/app/schemas/__init__.py:9`
- `backend/app/schemas/__init__.py:16`
- `backend/app/schemas/__init__.py:82`

处理结果：

- 引入统一的 `RequestModel`，对请求体统一设置 `extra = forbid`。
- 关键写接口模型已切换到严格模式。

### QJ-009 客户端令牌长期落盘，存在本地泄露风险

影响：本地存储中的令牌、用户信息与配对摘要一旦被提取，将扩大账号接管与隐私泄露范围。

状态：已修复

修复位置：

- `web/js/api.js:13`
- `web/js/api.js:15`
- `web/js/api.js:84`
- `miniprogram/app.js:9`
- `miniprogram/app.js:32`
- `qinjian-app/qingjian app/utils/api.js:26`
- `qinjian-app/qingjian app/utils/api.js:29`
- `qinjian-app/qingjian app/utils/session.js:6`
- `qinjian-app/qingjian app/utils/session.js:10`

处理结果：

- Web 端令牌从 `localStorage` 收紧为 `sessionStorage`，并兼容清理旧令牌。
- 小程序与 uni-app 登录态改为运行期内存态，并在启动时清理旧版持久化敏感数据。

### QJ-010 密码与令牌策略偏弱

影响：较短密码和松散的 JWT 结构会增加撞库、口令爆破与令牌混淆的成功概率。

状态：已修复

修复位置：

- `backend/app/api/v1/auth.py:33`
- `backend/app/api/v1/auth.py:65`
- `backend/app/api/v1/auth.py:321`
- `backend/app/core/security.py:25`
- `backend/app/core/security.py:38`
- `web/js/app.js:1625`
- `miniprogram/pages/login/login.js:311`
- `qinjian-app/qingjian app/pages/profile/index.vue:162`

处理结果：

- 注册与改密口令长度统一提升到至少 8 位。
- JWT 增加 `type`、`iat`、`nbf`、`exp` 并在解码时校验必需声明。
- 各端输入提示已同步到 8 位口令要求。

## 低风险与复核结论

### QJ-011 API 文档与主机访问面已收紧

状态：已修复

修复位置：

- `backend/app/core/config.py:15`
- `backend/app/core/config.py:56`
- `backend/app/main.py:8`
- `backend/app/main.py:106`
- `backend/app/main.py:127`

处理结果：

- OpenAPI/Docs 默认关闭，仅 DEBUG 或显式开启时开放。
- 引入 `TrustedHostMiddleware`，限制可接受主机头。
- 健康检查接口不再暴露应用名称等额外信息。

### QJ-012 前端 `innerHTML` 使用点已复核

状态：已复核，当前未确认为可利用漏洞

复核结论：

- `web/js/app.js` 与 `web/js/handmade.js` 中大量模板拼接路径对用户可控字段已统一走 `escapeHtml`。
- 本轮未发现直接将外部可控原文无转义写入 DOM 的已证实漏洞。
- 该区域仍建议在后续前端重构时持续向组件化渲染迁移，降低维护复杂度。

## 验证结果

已执行验证：

- `cd backend && python -m pip_audit -r requirements.txt`
  - 结果：`No known vulnerabilities found`
- `cd backend && python -m pytest tests`
  - 结果：`20 passed in 1.82s`
- `python -m py_compile deploy_manual.py deploy_current_workspace.py remote_exec.py remote_recover_compose.py backend/app/core/security.py backend/app/main.py backend/tests/test_auth_security.py`
  - 结果：通过

## 结论

本轮已完成可直接验证的高危与中低危问题修复，当前仓库代码路径中未再发现已知依赖漏洞，关键权限边界、部署密钥处理和客户端令牌留存面均已明显收紧。若需要，我可以继续下一步补一份“上线前安全检查清单”，专门覆盖环境变量、数据库迁移、密钥轮换与部署流程。
