# 亲健 全量安全审查与修复记录

日期：2026-03-29

## 已修复

### 1. 实时语音鉴权从长期 JWT URL 参数改为短时票据

- 新增短时 `realtime_asr` 票据签发与校验。
- 前端不再把长期登录令牌放进 WebSocket URL。
- 新增 `/api/v1/agent/asr/ws-ticket` 与 `/api/v1/agent/asr/realtime`。

影响：
- 降低 Bearer Token 出现在代理日志、截图、报错记录和历史地址栏中的风险。

### 2. 实时语音前后端链路补齐

- 前端补上 `agent-voice-btn` 和状态提示。
- 绑定实际点击事件。
- 后端补上实时 ASR WebSocket 桥接。
- Nginx 补上 WebSocket 反向代理升级配置。

影响：
- 语音陪伴不再是“前端残留代码”，而是能实际建立链路并完成转写。

### 3. 登录枚举与内部错误泄露收敛

- 登录失败统一返回“邮箱或密码错误”。
- 登录邮箱统一做 `strip + lower` 归一化。
- 验证码存储配置错误不再直接回显内部异常。

影响：
- 降低账号枚举与内部配置暴露风险。

### 4. 语音转录错误响应收敛

- 转录异常不再把底层错误直接返回前端。
- 对明确的参数/文件错误仍保留 4xx。
- 非预期错误改为通用服务不可用响应并记录日志。

影响：
- 降低模型供应商、内部堆栈和环境细节泄露风险。

### 5. 关系联系人信息最小化展示

- 配对响应不再返回伴侣邮箱/手机号。
- 前端展示退化为备注名、系统昵称或通用标签。
- 激活后的关系不再在主要界面继续展示邀请码。

影响：
- 降低关系对象联系方式在前端界面和接口载荷中的不必要暴露。

### 6. 上传签名使用独立密钥入口

- 上传签名新增 `UPLOAD_SIGNING_KEY`，未配置时再回退 `SECRET_KEY`。

影响：
- 方便后续分离 JWT 密钥与文件访问签名密钥，减少单点密钥复用。

### 7. 部署侧浏览器安全头增强

- 新增 `Permissions-Policy`
- 新增过渡型 `Content-Security-Policy`

影响：
- 提升默认浏览器侧防护基线。

### 8. 仓库内已跟踪环境文件脱敏

- `backend/.env`
- `backend/.env.local`

处理：
- 已改为占位符，不再保留真实密钥。

注意：
- 这些密钥应视为已泄露，必须在真实环境中立即轮换。

## 已补验证

- `python -m compileall app`
- `python -m pytest tests/test_auth_security.py tests/test_pairs_security.py tests/test_upload_access.py tests/test_main_openapi.py tests/test_agent_realtime_ws.py`

结果：
- 17 项测试全部通过。

## 剩余风险

### 1. 前端仍大量依赖 `innerHTML` 和内联事件

当前已通过转义和过渡型 CSP 降低风险，但尚未完成彻底的 DOM 安全重构。

建议后续：
- 去掉内联 `onclick`
- 引入统一模板渲染或可信 DOM 构建
- 在可行时将 CSP 收紧到不依赖 `'unsafe-inline'`

### 2. 已跟踪密钥虽然已脱敏，但历史提交若包含真实值仍需处理

如果这些密钥曾进入 Git 历史、备份、CI 日志或协作渠道，还需要：
- 轮换真实密钥
- 检查部署平台变量
- 必要时清理历史与审计访问日志
