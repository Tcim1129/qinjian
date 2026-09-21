# 亲健小程序和 App 开发实施方案

## 项目概览

**目标**：基于现有 `web-vue3` 代码，使用 uni-app 框架开发小程序和 App

**技术选型**：uni-app (Vue 3) + 现有后端 API

**开发周期**：6-8 周

---

## 已完成

### 1. 账号准备
- [x] 微信小程序账号：`wx058aa6f57c35a917`（已有 `project.config.json`）
- [ ] Apple Developer 账号（$99/年）
- [ ] Google Play Developer 账号（$25 一次性）

### 2. 后端准备
- [x] FastAPI 后端（`backend/`）
- [x] 完整 RESTful API（`/api/v1/*`）
- [x] JWT 认证机制
- [x] CORS 配置支持跨域
- [x] 微信登录接口（后端已实现 `POST /api/v1/auth/wechat/login`，配置密钥即可用）

### 3. 前端资源
- [x] Vue 3 组件库（`web-vue3/src/components/`）
- [x] Pinia 状态管理（`web-vue3/src/stores/`）
- [x] 工具函数（`web-vue3/src/utils/`）
- [x] API 封装（`web-vue3/src/api/index.js`）

---

## 实施步骤

### 第 1 周：项目搭建与配置

#### 1.1 初始化 uni-app 项目

```bash
# 在项目根目录创建 qinjian-client
npx degit dcloudio/uni-preset-vue#vite qinjian-client
cd qinjian-client
npm install
```

#### 1.2 配置文件

**manifest.json**（已生成在 `qinjian-client/src/manifest.json`）
- 配置小程序 appid
- 配置 H5 端口和路由模式
- 配置 App 权限

**pages.json**（已生成在 `qinjian-client/src/pages.json`）
- 定义页面路由
- 配置 TabBar（首页、记录、简报、我的）
- 配置导航栏样式

**vite.config.js**（已生成）
- 配置 API 代理
- 配置开发服务器

#### 1.3 目录结构

```
qinjian-client/
├── src/ # 源码目录
│ ├── pages/ # 页面
│ │ ├── index/ # 欢迎页
│ │ ├── auth/ # 登录注册
│ │ ├── home/ # 首页
│ │ ├── checkin/ # 今日记录
│ │ ├── report/ # 简报
│ │ ├── pair/ # 关系管理
│ │ ├── timeline/ # 时间轴
│ │ └── profile/ # 我的
│ ├── components/ # 通用组件
│ ├── stores/ # Pinia 状态管理
│ ├── utils/ # 工具函数（request.js、config.js）
│ ├── static/ # 静态资源
│ ├── App.vue # 应用入口
│ ├── main.js # 主文件
│ ├── pages.json # 页面配置
│ ├── manifest.json # 应用配置
│ └── uni.scss # 全局样式变量
├── index.html # H5 入口
├── package.json
└── vite.config.js # 构建配置
```

---

### 第 2-3 周：核心页面迁移

#### 2.1 认证模块
- [ ] 登录页（邮箱登录 + 手机验证码）
- [ ] 注册页
- [ ] 微信授权登录（小程序专用）

**迁移要点**：
- 复用 `web-vue3/src/views/auth/LoginPage.vue` 的逻辑
- 使用 `uni.request` 替代 `axios`
- 使用 `uni.setStorageSync` 存储 token
- 小程序端使用 `uni.login` 获取微信 code

#### 2.2 首页
- [ ] 关系概览卡片
- [ ] 快速操作入口
- [ ] 今日安排展示

#### 2.3 今日记录
- [ ] 文字记录表单
- [ ] 情绪标签选择
- [ ] 图片上传（`uni.chooseImage`）
- [ ] 语音录制（`uni.getRecorderManager`）
- [ ] 语音转写展示

**迁移要点**：
- 复用 `web-vue3/src/views/checkin/CheckinPage.vue`
- 使用 uni-app 的 `<picker>` 组件选择情绪
- 使用 `uni.uploadFile` 上传文件

#### 2.4 简报页
- [ ] 日报/周报/月报切换
- [ ] 健康分展示
- [ ] 趋势图表（使用 uCharts）
- [ ] 建议动作列表

#### 2.5 关系管理
- [ ] 创建邀请码
- [ ] 输入邀请码建联
- [ ] 关系列表
- [ ] 关系详情（关系空间）

---

### 第 4 周：辅助功能

#### 4.1 时间轴
- [ ] 记录列表（按日期分组）
- [ ] 报告节点标记
- [ ] 归档摘要展示
- [ ] 下拉刷新、上拉加载

#### 4.2 我的
- [ ] 个人资料编辑
- [ ] 隐私设置
- [ ] 关于我们
- [ ] 退出登录

#### 4.3 其他页面
- [ ] 双视角（`/alignment`）
- [ ] 发前看看（`/message-simulation`）
- [ ] 缓和建议（`/repair-protocol`）

---

### 第 5 周：API 对接与状态管理

#### 5.1 API 封装

**创建 `utils/request.js`**（与已生成骨架一致）：

```javascript
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
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: reject
    })
  })
}
```

**创建 `api/index.js`**（复用 web-vue3 的 API 定义）：

```javascript
import { request } from '../utils/request'

export const authAPI = {
  login: (data) => request({ url: '/api/v1/auth/login', method: 'POST', data }),
  register: (data) => request({ url: '/api/v1/auth/register', method: 'POST', data }),
  wechatLogin: (code) => request({ url: '/api/v1/auth/wechat/login', method: 'POST', data: { code } })
}

export const checkinAPI = {
  create: (data) => request({ url: '/api/v1/checkins', method: 'POST', data }),
  list: (params) => request({ url: '/api/v1/checkins', params })
}

export const reportAPI = {
  get: (params) => request({ url: '/api/v1/reports', params })
}

// ... 其他 API
```

#### 5.2 Pinia 状态管理

移植 `web-vue3/src/stores/`：请求层从 `@/api`（axios 封装）改为本项目的 `utils/request.js`，本地存储改用 `uni.getStorageSync`

---

### 第 6 周：小程序专属功能

#### 6.1 微信登录

后端接口已就绪（`backend/app/api/v1/auth.py` 中的 `POST /auth/wechat/login`），无需新增代码。

**前端调用**：

```javascript
// 小程序端登录
uni.login({
  provider: 'weixin',
  success: async (res) => {
    const { code } = res
    const result = await authAPI.wechatLogin(code)
    uni.setStorageSync('token', result.access_token)
    uni.switchTab({ url: '/pages/home/home' })
  }
})
```

#### 6.2 消息推送（订阅消息）

```javascript
uni.requestSubscribeMessage({
  tmplIds: ['模板ID'],
  success: (res) => {
    console.log('订阅成功', res)
  }
})
```

#### 6.3 分享功能

```javascript
uni.showShareMenu({
  withShareTicket: true,
  menus: ['shareAppMessage', 'shareTimeline']
})

// 自定义分享内容
onShareAppMessage(() => {
  return {
    title: '邀请你加入亲健',
    path: '/pages/index/index?inviteCode=xxx'
  }
})
```

---

### 第 7 周：测试与优化

#### 7.1 测试清单

- [ ] 真机测试（iOS + Android）
- [ ] 小程序开发者工具测试
- [ ] 不同屏幕尺寸适配
- [ ] 弱网环境测试
- [ ] 性能优化（首屏加载、图片懒加载）

#### 7.2 优化要点

1. **分包加载**（pages.json）：
```json
{
  "subPackages": [
    {
      "root": "pages/advanced",
      "pages": ["alignment", "message-simulation", "repair-protocol"]
    }
  ]
}
```

2. **图片优化**：
   - 使用 WebP 格式
   - 配置 OSS 图片裁剪

3. **代码优化**：
   - 使用 `onReachBottom` 实现分页加载
   - 避免频繁 `setData`

---

### 第 8 周：发布上线

#### 8.1 小程序审核

1. **上传代码**：
   ```bash
   npm run build:mp-weixin
   # 使用微信开发者工具上传
   ```

2. **提交审核**：
   - 填写版本号、更新说明
   - 配置隐私政策 URL
   - 选择服务类目（社交 > 情感咨询）
   - 上传测试账号

3. **审核要点**：
   - 不能有"诊断""治疗"等医疗用语
   - 不能自动共享用户隐私内容
   - 必须有明确的隐私政策和用户协议
   - 内容合规（情感类审核较严）

#### 8.2 App 打包（HBuilderX）

1. 配置证书
2. 云打包
3. 提交应用市场

---

## 后端配置（接口已就绪）

微信登录接口已在 `backend/app/api/v1/auth.py` 中实现（`POST /auth/wechat/login`），用 code 换取 openid，首次登录自动创建用户，无需新增接口，只需配置密钥：

| 变量 | 说明 |
|------|------|
| `WECHAT_APPID` | 小程序 AppID（`wx058aa6f57c35a917`） |
| `WECHAT_SECRET` | 小程序密钥，在微信公众平台生成 |

```bash
# backend/.env
WECHAT_APPID=wx058aa6f57c35a917
WECHAT_SECRET=你的小程序密钥
```

---

## 成本估算

| 项目 | 费用 |
|------|------|
| 微信小程序账号 | ¥300/年（企业）或 ¥0（个人） |
| Apple Developer | $99/年（¥700） |
| Google Play | $25 一次性（¥180） |
| HTTPS 证书 | ¥0-500/年（Let's Encrypt 免费） |
| **总计** | **¥880-1380/年** |

---

## 注意事项

1. **合规要求**：
   - 必须有《隐私政策》《用户协议》
   - 情感类小程序审核严格，避免"诊断""治疗"等医疗用语
   - 用户内容必须可控，防止违规内容

2. **技术限制**：
   - 小程序包大小限制 2MB（主包）+ 20MB（分包）
   - 不支持 DOM/BOM 操作
   - 部分 npm 包不兼容

3. **开发建议**：
   - 优先开发小程序（周期短、用户习惯好）
   - 使用条件编译处理平台差异（`#ifdef MP-WEIXIN`）
   - H5 端作为 Web 版的补充，不是替代

---

## 下一步行动

1. [ ] 安装 HBuilderX 或使用 VSCode + uni-app 插件
2. [ ] 初始化 uni-app 项目（`qinjian-client` 已创建骨架）
3. [ ] 迁移登录页和首页（2-3 天）
4. [ ] 对接后端 API 并测试（1 天）
5. [ ] 逐步迁移其他页面（按优先级）
6. [ ] 申请小程序测试号并真机测试

---

## 参考文档

- [uni-app 官方文档](https://uniapp.dcloud.net.cn/)
- [微信小程序开发文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
- [Pinia 在 uni-app 中的使用](https://pinia.vuejs.org/)
- [uCharts 图表库](https://www.ucharts.cn/)

---

**生成时间**：2026-09-18
**文档版本**：v1.0
**维护者**：亲健开发团队
