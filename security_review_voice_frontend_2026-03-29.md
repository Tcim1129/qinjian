# 代码安全审查与语音前端核对（2026-03-29）

## 执行摘要

本次审查重点覆盖了语音相关前后端链路，以及与其直接相邻的认证、上传与前端渲染面。

- 未发现语音上传链路上的明显未授权访问或任意文件读取问题；上传接口有登录校验、类型白名单、magic bytes 校验，私有上传默认通过签名 URL 访问。
- 发现 1 个中风险安全问题：实时语音 WebSocket 设计为把 JWT 放进 URL 查询串。
- 发现 2 个低风险安全问题：前端部署层未看到 CSP；语音转录接口会把内部异常原样返回给客户端。
- 语音前端“实时说话转写”功能当前没有打通。结论不是“浏览器兼容性不好”，而是代码链路本身缺口较大。

## 安全发现

### S-01 中风险：实时语音 WebSocket 计划通过 URL 查询串传递 JWT

- 位置：
  - `web/js/api.js:720-735`
- 证据：
  - `socketUrl.searchParams.set('token', this.token);`
- 影响：
  - 一旦后端 WebSocket 路由补齐并上线，Bearer Token 会进入浏览器开发者工具、反向代理日志、错误采集、抓包记录或截图中，泄露后可直接冒用用户身份直到令牌过期。
- 修复建议：
  - 不要在 URL 中传 JWT。
  - 改为短时效一次性 WS ticket，或在握手后首条消息里传递临时凭证并立即失效。
  - 如果必须做浏览器 WebSocket 鉴权，优先使用后端签发的短时票据，而不是长期 API Token。

### S-02 低风险：当前检查到的部署配置未提供 CSP，前端又大量依赖 `innerHTML`

- 位置：
  - `nginx.conf:1-7`
  - `web/js/app.js:170-172`
  - `web/js/app.js:266-270`
- 证据：
  - Nginx 仅设置了 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`，未见 `Content-Security-Policy`。
  - 前端存在 `safeSetHtml` / `openModal` 等 `innerHTML` 写入点。
- 影响：
  - 当前代码里多数渲染点做了转义，但一旦后续引入未转义内容或出现存储型/DOM 型 XSS，缺少 CSP 会让问题更容易升级为令牌窃取与任意脚本执行。
- 修复建议：
  - 在 Nginx 或边缘层增加 CSP。
  - 收敛 `innerHTML` 使用范围，优先改为 `textContent` / `createElement`。
  - 由于前端持有登录令牌，建议把 CSP 视为必备的第二道防线。

### S-03 低风险：语音转录接口把内部异常细节直接返回给客户端

- 位置：
  - `backend/app/api/v1/upload.py:296-300`
- 证据：
  - `raise HTTPException(status_code=500, detail=f"转录失败：{str(e)}")`
- 影响：
  - 可能把上游 AI 服务报错、文件处理细节或内部路径信息暴露给前端。
  - 同时会把本应返回 4xx 的受控错误统一包装成 500，不利于客户端正确处理。
- 修复建议：
  - 保留并透传 `HTTPException`。
  - 其他异常只记录到服务端日志，返回统一错误文案，例如“转录暂时不可用，请稍后重试”。

## 语音前端现状

### F-01 高优先级：实时语音输入前端没有真正接通

- 位置：
  - `web/index.html:456-472`
  - `web/js/app.js:1279-1568`
  - `web/js/app.js:4226-4249`
  - `backend/app/api/v1/__init__.py:4-16`
  - `backend/app/api/v1/__init__.py:34-50`
- 证据：
  - 语音陪伴面板只有 `agent-send-btn` 和 `agent-replay-btn`，没有 `agent-voice-btn` / `agent-voice-status`。
  - `toggleAgentVoiceInput()` 已实现，但代码库里没有任何调用或事件绑定。
  - 前端会连接 `/agent/asr/realtime`，但当前路由装配里没有任何 WebSocket router。
  - 实际导入 `backend/app/main.py` 后检查路由，结果为 0 条 WebSocket 路由。
- 结论：
  - “实时麦克风说话 -> 实时转写 -> 自动发给 Agent” 这条链路现在是未完成状态。
  - 所以你问的“语音功能的前端是不是没好”，答案是：`是，至少实时语音这部分没接完。`

### F-02 当前可用的“语音”能力只有两类

- 语音附件上传：
  - `web/index.html:423-437`
  - `web/js/app.js:2216-2234`
  - 作用是选择本地音频文件、做本地元信息分析、提交 `voice_url`。
- 浏览器朗读上一条回复：
  - `web/js/app.js:1612-1624`
  - 这是浏览器 `speechSynthesis` 朗读文本，不是服务端 TTS，也不是实时语音对话。

### F-03 上传音频转文字接口存在，但前端没有使用

- 位置：
  - `backend/app/api/v1/upload.py:233-294`
- 说明：
  - 后端有 `/api/v1/upload/transcribe`。
  - 前端代码中未发现对该接口的调用。
- 结论：
  - 即便不做 WebSocket 实时识别，当前前端也没有接“上传音频后转文字再进入 Agent”的降级方案。

## 正向观察

- 上传接口要求登录：`backend/app/api/v1/upload.py:85-148`
- 上传文件做了 MIME 白名单和 magic bytes 校验：`backend/app/api/v1/upload.py:24-35`、`backend/app/api/v1/upload.py:92-99`、`backend/app/api/v1/upload.py:125-132`
- 私有上传默认走签名访问而不是公开静态目录：`backend/app/main.py:121-123`、`backend/app/services/upload_access.py:47-56`
- 生产环境有弱密钥与弱数据库密码拦截：`backend/app/main.py:71-83`

## 建议的修复顺序

1. 先补齐实时语音功能链路。
   - 前端补 `agent-voice-btn` / `agent-voice-status`
   - 给按钮绑定 `toggleAgentVoiceInput`
   - 后端新增并注册 `/agent/asr/realtime` WebSocket 路由
2. 同步修正 WebSocket 鉴权方案。
   - 去掉 URL 查询串 JWT
   - 改成短时效票据
3. 给前端部署层补 CSP，并审计高频 `innerHTML` 渲染点。
4. 收敛 `/upload/transcribe` 的异常返回，避免信息泄露。
