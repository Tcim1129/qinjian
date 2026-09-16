import test from 'node:test'
import assert from 'node:assert/strict'
import {
  AGREEMENT_BLOCK_MESSAGE,
  LOGIN_LEGAL_NOTICE,
  canEnterService,
} from './complianceAgreement.js'

test('blocks service entry until the user accepts the agreement', () => {
  assert.deepEqual(canEnterService(false), {
    allowed: false,
    message: AGREEMENT_BLOCK_MESSAGE,
  })

  assert.deepEqual(canEnterService(true), {
    allowed: true,
    message: '',
  })
})

test('agreement notice covers mainland China minor and privacy safeguards', () => {
  const noticeText = [
    LOGIN_LEGAL_NOTICE.title,
    LOGIN_LEGAL_NOTICE.intro,
    ...LOGIN_LEGAL_NOTICE.documents.flatMap((document) => [
      document.title,
      ...document.sections.flatMap((section) => [
        section.heading,
        ...section.items,
      ]),
    ]),
  ].join('\n')

  assert.match(noticeText, /中华人民共和国大陆地区/)
  assert.match(noticeText, /未成年人/)
  assert.match(noticeText, /虚拟亲属、虚拟伴侣/)
  assert.match(noticeText, /不满十四周岁/)
  assert.match(noticeText, /父母或者其他监护人/)
  assert.match(noticeText, /个人信息/)
})

test('agreement notice follows platform-style agreement structure', () => {
  const noticeText = [
    LOGIN_LEGAL_NOTICE.title,
    LOGIN_LEGAL_NOTICE.intro,
    ...LOGIN_LEGAL_NOTICE.highlights,
    ...LOGIN_LEGAL_NOTICE.laws.flatMap((item) => [item.title, item.reason]),
    ...LOGIN_LEGAL_NOTICE.documents.flatMap((document) => [
      document.title,
      ...document.sections.flatMap((section) => [
        section.heading,
        ...section.items,
      ]),
    ]),
  ].join('\n')

  assert.equal(LOGIN_LEGAL_NOTICE.documents.length, 3)
  assert.deepEqual(
    LOGIN_LEGAL_NOTICE.documents.map((document) => document.id),
    ['service', 'privacy', 'minor'],
  )
  assert.match(noticeText, /重点阅读|审慎阅读|充分理解/)
  assert.match(noticeText, /儿童/)
  assert.match(noticeText, /十四周岁以上不满十八周岁|14周岁以上不满18周岁/)
  assert.match(noticeText, /单独同意/)
  assert.match(noticeText, /投诉|反馈|举报/)
  assert.match(noticeText, /更新|变更/)
  assert.match(noticeText, /删除|复制|注销/)
  assert.match(noticeText, /第三方/)
  assert.match(noticeText, /留存|保存期限/)
})

test('agreement notice enumerates the key mainland legal basis', () => {
  const lawTitles = LOGIN_LEGAL_NOTICE.laws.map((item) => item.title).join('\n')

  assert.ok(LOGIN_LEGAL_NOTICE.laws.length >= 10)
  assert.match(lawTitles, /民法典/)
  assert.match(lawTitles, /未成年人保护法/)
  assert.match(lawTitles, /网络安全法/)
  assert.match(lawTitles, /数据安全法/)
  assert.match(lawTitles, /个人信息保护法/)
  assert.match(lawTitles, /未成年人网络保护条例/)
  assert.match(lawTitles, /网络数据安全管理条例/)
  assert.match(lawTitles, /互联网用户账号信息管理规定/)
  assert.match(lawTitles, /移动互联网应用程序信息服务管理规定/)
  assert.match(lawTitles, /网络信息内容生态治理规定/)
  assert.match(lawTitles, /生成式人工智能服务管理暂行办法/)
  assert.match(lawTitles, /互联网信息服务深度合成管理规定/)
  assert.match(lawTitles, /人工智能生成合成内容标识办法/)
  assert.match(lawTitles, /可能影响未成年人身心健康的网络信息分类办法/)
  assert.match(lawTitles, /人工智能拟人化互动服务管理暂行办法/)
})

test('each legal document has enough section coverage for login entry notice', () => {
  for (const document of LOGIN_LEGAL_NOTICE.documents) {
    assert.ok(document.title.length >= 4)
    assert.ok(document.sections.length >= 4)
  }
})
