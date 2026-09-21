# 亲健小程序和 App 重构规划

**文档版本**: v1.0
**日期**: 2026-09-18
**状态**: 规划草案

## 一、现状评估

### 1.1 代码位置

- **旧版小程序/App**: 在 `codex/software-track-materials` 分支（与 main 独立历史）
- **当前 Web**: 在 main 分支的 `web-vue3/`
- **后端**: 在 main 分支的 `backend/`（已演进到 9 月，支持 agent/skills）

### 1.2 技术栈对比

| 端 | 技术栈 | 页面数 | 最后更新 | 状态 |
|---|---|---|---|---|
| **Web** | Vue 3.5 + Vite + Pinia + Vue Router 4 | 26 页 | 2026-09 | 活跃开发 |
| **旧小程序** | 原生小程序（WXML/WXSS/JS） | 18 页 | 2026-03 | 停滞 6 个月 |
| **旧 App** | uni-app（Vue 3 + Vuex，2022 年版本） | 7 页 | 2026-03 | 停滞 6 个月 |

### 1.3 Web 架构分析（复用基础）

**目录结构**:
```
web-vue3/src/
├── api/ # 后端接口封装
├── assets/ # 静态资源
├── components/ # 8 个公共组件
├── router/ # Vue Router 路由
├── stores/ # 4 个 Pinia stores (user, home, checkin, report)
├── utils/ # 40+ 工具模块（含 38 个单元测试）
└── views/ # 26 个页面组件
```

**核心依赖**:
- vue 3.5.13（Composition API）
- pinia 2.3.0（状态管理）
- axios 1.7.9（HTTP 请求）
- lucide-vue-next（图标）

**可直接复用的模块**:
- `stores/` — Pinia stores（user/checkin/report/home）
- `utils/auth.js` — 登录态、token 管理
- `utils/checkinForm.js` — 打卡表单逻辑
- `utils/reportContent.js` — 报告数据处理
- `utils/relationshipSpaces.js` — 关系空间逻辑
- `utils/experienceMode.js` — 演示模式
- `api/` 目录 — 后端接口适配器

**需要适配的模块**:
- `utils/realtimeVoice.js` — 实时语音（Web API → 小程序/uni-app API）
- `utils/voiceDraft.js` — 语音草稿存储
- `router/` — Vue Router → 小程序 switchTab/navigateTo 或 uni-app pages.json

### 1.4 功能差距清单

**旧小程序已有（18 页）**: home, login, checkin, discover, pair, report, profile, tree, milestone, crisis + discover 子页面（longdistance, attachment-test, health-test, community, challenges, courses, experts, membership）

**旧 App 已有（7 页）**: index, auth, checkin, discover, pair, report, profile

**Web 当前有但两端都缺的核心功能**:

| 功能 | Web 页面 | 优先级 | 说明 |
|---|---|---|---|
| **智能体对话** | ChatPage | P0 | 核心新功能，Agent/Skills 分析 |
| **发前看看** | MessageSimulationPage | P0 | 消息预演 |
| **缓和建议** | RepairProtocolPage | P0 | 修复协议 |
| **双视角** | AlignmentPage | P0 | 视角对齐 |
| **时间轴** | TimelinePage | P0 | 记录回看 |
| **隐私中心** | PrivacySecurityPage | P0 | 隐私设置、审计 |
| **关系空间** | RelationshipSpacesPage | P1 | 关系详情、星图 |
| **智能体主页** | RelationshipAgentPage | P1 | Agent 能力展示 |
| **判断说明** | MethodologyPage | P2 | 方法论说明 |
| **等待确认** | PairWaitingPage | P2 | 关系确认等待 |

## 二、重构方案

### 2.1 技术选型建议

**推荐方案：uni-app（Vue 3 + Composition API）**

**理由**:
1. **一套代码三端复用**（Web + 小程序 + App）
2. **Vue 3 生态统一** — 与 web-vue3 技术栈一致，stores 与纯逻辑 utils 可移植，涉及浏览器 API 的部分需改造
3. **成熟生态** — HBuilderX IDE、官方插件、组件库丰富
4. **跨端 API 统一** — uni.request、uni.getStorageSync 等跨平台
5. **小程序原生能力完整** — wx.login、订阅消息、分享等全支持

**架构对比**:

| 方案 | 优点 | 缺点 | 评分 |
|---|---|---|---|
| **uni-app** | 三端统一、Vue 3 生态、CLI 与 HBuilderX 均可 | 浏览器 API 需条件编译 | 5/5 |
| 原生小程序 + 原生 App | 性能最优、能力完整 | 开发成本 3x、无法复用 Web 代码 | 2/5 |
| Taro | React 生态、多端支持 | 需重写（Vue → React）、学习成本高 | 3/5 |
| 只做小程序 | 开发快、微信生态 | 无 App、iOS 用户无法使用 | 3/5 |

### 2.2 目标架构

```
qinjian-client/ # uni-app CLI 项目根目录
├── src/ # 源码目录（CLI 工程约定）
│ ├── pages/ # 页面（26+ 页）
│ │ ├── index/ # 首页
│ │ ├── auth/ # 登录
│ │ ├── checkin/ # 打卡
│ │ ├── report/ # 报告
│ │ ├── pair/ # 关系管理
│ │ ├── profile/ # 我的
│ │ └── chat/ agent/ timeline/ 等 # 新增页，见功能差距清单
│ ├── components/ # 公共组件（从 Web 移植）
│ ├── stores/ # Pinia stores（移植后改造请求/存储层）
│ ├── utils/ # 工具函数（纯逻辑可直接复用）
│ │ ├── request.js # 统一请求封装（uni.request）
│ │ ├── config.js # API 地址等配置
│ │ ├── checkinForm.js
│ │ ├── reportContent.js
│ │ └── ...
│ ├── static/ # 静态资源
│ ├── App.vue
│ ├── main.js
│ ├── manifest.json # 应用配置（appid、权限、图标）
│ ├── pages.json # 页面路由、tabBar
│ └── uni.scss # 全局样式变量
├── index.html # H5 入口
├── package.json
└── vite.config.js
```

### 2.3 关键技术方案

#### 2.3.1 状态管理

**移植 Web 的 Pinia stores**（请求层与本地存储改为 uni API）:
```javascript
import { defineStore } from 'pinia'
import { get } from '../utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    profile: null,
    pairs: []
  }),
  actions: {
    async fetchProfile() {
      this.profile = await get('/api/v1/auth/me')
    }
  }
})
```

#### 2.3.2 API 请求适配

**统一封装 uni.request**（axios 依赖 XMLHttpRequest，小程序没有该对象，不能直接用）:

```javascript
// utils/request.js
import config from './config'

export function request(options) {
  const token = uni.getStorageSync('token')
  return new Promise((resolve, reject) => {
    uni.request({
      url: config.apiBaseUrl + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(res)
      },
      fail: reject
    })
  })
}
```

H5 端若坚持用 axios，需要接入 axios 的 uni-app 适配器；统一到 uni.request 最省事。

#### 2.3.3 路由适配

| Web (Vue Router) | uni-app | 说明 |
|---|---|---|
| `router.push('/checkin')` | `uni.navigateTo({ url: '/pages/checkin/index' })` | 页面跳转 |
| `<router-link to="/report">` | `<navigator url="/pages/report/index">` | 声明式导航 |
| `router.replace()` | `uni.redirectTo()` | 重定向 |
| tabBar 路由 | `pages.json` tabBar 配置 + `uni.switchTab()` | 底部 tab |

**迁移策略**: 封装统一路由工具
```javascript
// utils/router.js
export const navigateTo = (path) => {
  // #ifdef H5
  router.push(path)
  // #endif
  // #ifdef MP-WEIXIN || APP-PLUS
  uni.navigateTo({ url: path })
  // #endif
}
```

#### 2.3.4 微信登录

**小程序端**（直接调用）:
```javascript
// pages/auth/index.vue
async onWechatLogin() {
  const { code } = await uni.login({ provider: 'weixin' })
  const data = await post('/api/v1/auth/wechat/login', {
    code,
    nickname: userInfo.nickName,
    avatar_url: userInfo.avatarUrl
  })
  uni.setStorageSync('token', data.access_token)
}
```

**后端已就绪** — `/auth/wechat/login` 接口已实现（需配置 WECHAT_APPID/WECHAT_SECRET）

#### 2.3.5 语音功能适配

| Web | 小程序 | uni-app App |
|---|---|---|
| `navigator.mediaDevices` | `wx.getRecorderManager()` | `uni.getRecorderManager()` |
| WebRTC | 不支持（用录音+上传） | 不支持（用录音+上传） |

**统一封装**:
```javascript
// utils/voiceRecorder.js
export const startRecord = () => {
  // #ifdef H5
  return navigator.mediaDevices.getUserMedia({ audio: true })
  // #endif
  // #ifdef MP-WEIXIN || APP-PLUS
  const recorder = uni.getRecorderManager()
  recorder.start()
  return recorder
  // #endif
}
```

## 三、分阶段实施计划

### 阶段 0：环境搭建（1 周）

**目标**: uni-app 项目初始化 + 代码迁移基础

**任务清单**:
- [x] 创建 uni-app CLI 项目（`npx degit dcloudio/uni-preset-vue#vite`，骨架已完成）
- [x] 配置 manifest.json（小程序 appid、权限）
- [x] 配置 pages.json（路由、tabBar）
- [ ] 安装依赖：pinia、sass（请求统一走 uni.request，不引入 axios）
- [ ] 从 Web 移植 `stores/`、`utils/`（请求与存储改为 uni API）
- [ ] 验证 Pinia 在 uni-app 中可用
- [ ] 开发环境：`npm run dev:mp-weixin` + 微信开发者工具

**交付物**:
- uni-app 项目构建通过（H5 + 小程序）
- Pinia store 在小程序中读写正常
- request 封装可成功请求后端 /auth/login

---

### 阶段 1：核心页面迁移（3 周）

**目标**: P0 核心流程打通（登录 → 打卡 → 报告 → 智能体）

#### Week 1: 基础页面（登录、首页、我的）

**页面**:
- [ ] LoginPage（登录页）
  - 邮箱/手机登录
  - 微信一键登录（小程序）
  - 演示模式入口
- [ ] HomePage（首页）
  - 今日记录入口
  - 关系摘要卡片
  - 趋势图表
- [ ] ProfilePage（我的）
  - 个人信息
  - 设置入口

**技术要点**:
- 从 Web 复制 LoginPage.vue、HomePage.vue、ProfilePage.vue
- 适配小程序/App 的布局（去掉 `<router-link>`，改用 `<navigator>`）
- 微信登录调用 `uni.login()` + 后端 `/auth/wechat/login`
- 测试 stores/user.js 的登录态同步

**验收标准**:
- 小程序可微信登录 + 邮箱登录
- App 可邮箱登录
- 登录后首页显示用户昵称和关系摘要
- "我的"页面个人信息展示正常

#### Week 2: 打卡 + 关系管理

**页面**:
- [ ] CheckinPage（今日打卡）
  - 文字记录
  - 情绪标签
  - 图片/语音上传
- [ ] PairPage（关系管理）
  - 创建邀请码
  - 输入邀请码
  - 关系列表
- [ ] PairWaitingPage（等待确认）

**技术要点**:
- 复用 `utils/checkinForm.js`
- 图片选择：`uni.chooseImage()`
- 语音录制：`uni.getRecorderManager()`
- 上传接口：`/upload/image`、`/upload/transcribe`

**验收标准**:
- 可完成一次完整打卡（文字 + 图片）
- 可创建邀请码并复制
- 可输入邀请码并加入关系

#### Week 3: 报告 + 智能体对话

**页面**:
- [ ] ReportPage（关系报告）
  - 日报/周报/月报
  - 健康分趋势
- [ ] ChatPage（智能体对话，新增）
  - 会话界面
  - 技能调用展示
  - 长期记忆

**技术要点**:
- 复用 `utils/reportContent.js`、`utils/chatHistory.js`
- 图表渲染：使用 uCharts（uni-app 插件）
- Agent API：`POST /agent/sessions`（创建会话）、`POST /agent/sessions/{id}/chat`（对话）、`/agent/skill/*`（技能分析）

**验收标准**:
- 报告页可查看日报、周报
- 智能体对话可发送消息并收到回复
- 技能调用有 loading 提示

---

### 阶段 2：P0 功能补齐（2 周）

**目标**: 消息预演、缓和建议、双视角、时间轴、隐私中心

#### Week 4: 预演 + 修复

**页面**:
- [ ] MessageSimulationPage（发前看看）
  - 输入待发送消息
  - 风险评估
  - 改写建议
- [ ] RepairProtocolPage（缓和建议）
  - 风险等级展示
  - 修复步骤
  - 禁忌事项
- [ ] AlignmentPage（双视角）
  - 我方视角
  - 对方视角
  - 误读点

**技术要点**:
- API：`POST /agent/simulate-message`（消息预演）、`GET /crisis/protocol`（缓和建议）、`GET /insights/alignment/latest` + `POST /insights/alignment/generate`（双视角）
- 复用 `utils/requestSceneReply.js`

**验收标准**:
- 可输入消息并获得风险评估
- 缓和建议根据风险等级显示对应步骤
- 双视角展示我方/对方理解差异

#### Week 5: 时间轴 + 隐私

**页面**:
- [ ] TimelinePage（时间轴）
  - 记录条目
  - 报告节点
  - 归档摘要
- [ ] PrivacySecurityPage（隐私与安全）
  - 同步策略设置
  - 审计记录
  - 删除申请

**技术要点**:
- 复用 `utils/timelineCalendar.js`
- API：`GET /insights/timeline/archive`（时间轴）、`GET /privacy/audit/me`、`POST /privacy/delete-request`（隐私）

**验收标准**:
- 时间轴按时间倒序显示记录
- 可设置"本机优先"/"同步到账号"
- 可查看审计记录

---

### 阶段 3：P1 功能 + 发布准备（3 周）

#### Week 6-7: 关系空间 + 扩展功能

**页面**:
- [ ] RelationshipSpacesPage（关系空间列表）
- [ ] RelationshipAgentPage（智能体主页）
- [ ] DiscoverPage（发现）+ 子页面
  - LongDistancePage（异地）
  - MilestonesPage（纪念日）
  - HealthTestPage（体检）
  - AttachmentPage（依恋测试）
  - CommunityPage（技巧）
  - ChallengesPage（任务）
  - CoursesPage（课程）
  - ExpertsPage（专家）
  - MembershipPage（会员）
- [ ] MethodologyPage（判断说明）

**验收标准**:
- 所有 Web 页面功能对齐
- 小程序 18 页 → 26+ 页
- App 7 页 → 26+ 页

#### Week 8: 发布准备

**小程序发布清单**:
- [ ] 真实域名配置（生产环境 HTTPS）
- [ ] 微信后台配置
  - [ ] 服务器域名白名单
  - [ ] 业务域名
  - [ ] appid: wx058aa6f57c35a917
- [ ] 后端环境变量
  - [ ] WECHAT_APPID
  - [ ] WECHAT_SECRET
- [ ] 隐私合规
  - [ ] 《用户隐私保护指引》
  - [ ] 用户协议页面
  - [ ] 隐私政策页面
- [ ] 内容安全
  - [ ] 接入 msgSecCheck（文本审核）
- [ ] 功能测试
  - [ ] 微信登录
  - [ ] 打卡 + 图片上传
  - [ ] 智能体对话
  - [ ] 订阅消息授权
- [ ] 提审材料
  - [ ] 类目资质（社交/工具类）
  - [ ] 测试账号
  - [ ] 功能截图

**App 发布清单**:
- [ ] manifest.json 配置
  - [ ] 真实 uni-app appid
  - [ ] 应用图标（1024x1024）
  - [ ] 启动图
  - [ ] 权限说明文案
- [ ] 推送配置（uni-push 或个推）
- [ ] iOS
  - [ ] Apple Developer 账号
  - [ ] 证书和描述文件
  - [ ] App Store Connect 配置
  - [ ] 隐私清单
- [ ] Android
  - [ ] 签名证书
  - [ ] App 备案
  - [ ] 各应用市场账号（华为/小米/OPPO/vivo/应用宝）
- [ ] 上架材料
  - [ ] 软著证书
  - [ ] 隐私政策 URL
  - [ ] 用户协议 URL
  - [ ] 应用介绍和截图

---

### 阶段 4：优化与迭代（持续）

**性能优化**:
- [ ] 分包加载（小程序 2MB 限制）
- [ ] 图片懒加载
- [ ] 首屏优化

**体验优化**:
- [ ] 骨架屏
- [ ] 下拉刷新
- [ ] 上拉加载更多
- [ ] 错误边界

**监控与反馈**:
- [ ] 小程序数据分析
- [ ] App 崩溃监控（Sentry）
- [ ] 用户反馈入口

## 四、技术风险与应对

| 风险 | 影响 | 应对方案 |
|---|---|---|
| **uni-app 与 Vue 3 兼容性** | 部分 Composition API 特性不支持 | 使用 uni-app 官方推荐的 Vue 3 写法，避免实验性 API |
| **小程序 2MB 包体积限制** | 功能多导致超限 | 启用分包加载，按功能模块拆分（主包 + 发现分包 + 扩展分包） |
| **Web 组件样式在小程序不兼容** | 部分 CSS 特性失效 | 使用 uni-app 兼容的样式（rpx、flex），避免 Grid（部分场景）|
| **实时语音在小程序无法使用 WebRTC** | 语音对话功能降级 | 改用录音 + 上传 + 转写的异步模式 |
| **iOS 审核严格** | 社交/情感类目可能被拒 | 准备审核说明，强调"记录工具"而非"社交软件"，准备测试账号 |
| **后端 API 变更** | 旧前端调不通新接口 | 先跑一遍接口回归测试，补全缺失的端点或适配器 |

## 五、资源与时间估算

### 5.1 人力需求

**最小团队**（1 人全栈）:
- 前端开发（uni-app + 小程序/App 调试）
- 后端联调（微信登录、订阅消息）
- 设计适配（响应式布局、图标）

**总工作量**: 9 周（约 2.5 个月）

### 5.2 时间线

| 阶段 | 周数 | 里程碑 |
|---|---|---|
| 阶段 0：环境搭建 | 1 周 | uni-app 项目跑通 |
| 阶段 1：核心页面 | 3 周 | 登录 → 打卡 → 报告 → 智能体 |
| 阶段 2：P0 功能 | 2 周 | 预演、修复、双视角、时间轴、隐私 |
| 阶段 3：P1 + 发布 | 3 周 | 关系空间、扩展功能、发布准备 |
| 阶段 4：优化迭代 | 持续 | 性能、体验、监控 |

**最快上线**: 6 周（只做 P0 核心流程）
**完整功能**: 9 周（对齐 Web 全部功能）

### 5.3 成本估算

| 项目 | 费用 | 说明 |
|---|---|---|
| 小程序账号 | ¥300/年 | 企业主体（已有 appid: wx058aa6f57c35a917） |
| Apple Developer | $99/年（¥700） | iOS 发布必需 |
| Google Play | $25（¥180） | 仅海外 Android 上架需要；国内应用市场免费 |
| 服务器 HTTPS 证书 | ¥0-500/年 | Let's Encrypt 免费或付费证书 |
| uni-app 云服务（可选） | ¥0-1000/月 | uni-push、uni统计 |
| **总计** | **¥1200-2000** | 首年启动成本 |

## 六、关键决策点

### 6.1 是否保留原生小程序？

**建议**: 不保留，全部用 uni-app 重构

**理由**:
1. 原生小程序已停滞 6 个月，技术债务大
2. uni-app 可同时输出小程序 + App，开发效率高 3 倍
3. Vue 3 生态统一，Web/小程序/App 共享 stores 和 utils

### 6.2 先做小程序还是 App？

**建议**: 小程序优先，App 并行开发

**理由**:
1. 小程序审核快（1-3 天），App 需 1-2 周
2. 微信生态用户基数大，小程序触达率高
3. uni-app 同一套代码，小程序跑通后 App 只需调整配置和打包

### 6.3 是否需要 UI 组件库？

**建议**: 可选，优先自研（复用 Web 组件）

**可选方案**:
- uView Plus（uni-app Vue 3 组件库）
- uni-ui（官方组件库）
- 自研（从 Web 移植，保持设计一致性）

**推荐**: 先用自研（保持品牌一致），复杂组件（日历、图表）用插件。

## 七、下一步行动

### 立即可做（本周）

1. **确认技术选型** — uni-app（Vue 3）
2. **创建 uni-app 项目** — CLI 初始化（骨架已完成）
3. **复制 Web 代码** — stores/utils/api 目录移植
4. **配置开发环境** — 微信开发者工具联调
5. **跑通登录流程** — 微信登录 + 后端对接

### 需要决策（本周）

- [ ] 是否删除旧分支的 miniprogram 和 qinjian-app？（建议：保留作参考，不再开发）
- [ ] 新项目放在 main 分支的哪里？（建议：`qinjian-client/` 或 `client-uniapp/`）
- [ ] 是否与 web-vue3 合并为 monorepo？（建议：先独立，稳定后再合并）

### 资源协调

- [ ] 申请或确认 Apple Developer 账号
- [ ] 准备域名和 HTTPS 证书（生产环境）
- [ ] 后端配置 WECHAT_APPID/WECHAT_SECRET
- [ ] 准备隐私政策和用户协议文档

---

配套文档：开发实施方案见 [`小程序和App开发实施方案.md`](./小程序和App开发实施方案.md)，接口与页面清单以该文档为准。
