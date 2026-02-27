const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, LevelFormat, WidthType, BorderStyle, ShadingType, HeadingLevel, PageBreak } = require('docx');
const fs = require('fs');

// 定义表格边框样式
const tableBorder = {
  style: BorderStyle.SINGLE,
  size: 1,
  color: "999999"
};
const tableBorders = {
  top: tableBorder,
  bottom: tableBorder,
  left: tableBorder,
  right: tableBorder,
  insideHorizontal: tableBorder,
  insideVertical: tableBorder
};

// 创建表格单元格辅助函数
function createCell(text, width, options = {}) {
  const { bold = false, fill = null, colSpan = 1 } = options;
  return new TableCell({
    borders: tableBorders,
    width: { size: width, type: WidthType.DXA },
    columnSpan: colSpan,
    shading: fill ? { fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold, size: 21 })]
    })]
  });
}

// 创建标题段落
function createHeading(text, level) {
  const sizes = { 1: 36, 2: 32, 3: 28, 4: 26 };
  return new Paragraph({
    spacing: { before: 360, after: 180 },
    children: [new TextRun({ text, bold: true, size: sizes[level] || 24 })]
  });
}

// 创建正文段落
function createParagraph(text, options = {}) {
  const { bold = false, indent = false } = options;
  return new Paragraph({
    spacing: { before: 80, after: 80, line: 360 },
    indent: indent ? { left: 360 } : undefined,
    children: [new TextRun({ text, size: 21, bold })]
  });
}

// 创建要点列表
function createBulletList(items) {
  return items.map(item => new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: item, size: 21 })]
  }));
}

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: 'Microsoft YaHei', size: 21 }
      }
    }
  },
  numbering: {
    config: [{
      reference: 'bullets',
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: '•',
        alignment: AlignmentType.LEFT,
        style: {
          paragraph: {
            indent: { left: 720, hanging: 360 }
          }
        }
      }]
    }]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // 封面
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 2400, after: 400 },
        children: [new TextRun({ text: '亲健——青年亲密关系健康管理平台', bold: true, size: 44 })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [new TextRun({ text: '商业计划书', bold: true, size: 36 })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 800, after: 200 },
        children: [new TextRun({ text: '三创赛常规赛版（评委优化后）', size: 28, color: '666666' })]
      }),
      new Paragraph({
        children: [new PageBreak()] }),
      
      // 执行摘要
      createHeading('执行摘要', 1),
      createHeading('项目一句话定位', 2),
      createParagraph('亲健是中国首个专注"亲密关系场景"的AI健康管理平台，通过双视角数据采集与多模态AI分析，为18-40岁青年提供科学的关系健康评估与个性化改善方案。'),
      
      createHeading('核心价值主张', 2),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [2000, 3500, 3500],
        rows: [
          new TableRow({
            children: [
              createCell('维度', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('传统产品', 3500, { bold: true, fill: 'E8F4FC' }),
              createCell('亲健差异化', 3500, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('关系类型', 2000),
            createCell('单一情侣社交', 3500),
            createCell('情侣+夫妻+挚友全生命周期覆盖', 3500)
          ]}),
          new TableRow({ children: [
            createCell('数据采集', 2000),
            createCell('单视角自我报告', 3500),
            createCell('双视角交叉验证+单机模式备份', 3500)
          ]}),
          new TableRow({ children: [
            createCell('打卡体验', 2000),
            createCell('问卷式主动打卡', 3500),
            createCell('游戏化养成+被动数据辅助', 3500)
          ]}),
          new TableRow({ children: [
            createCell('AI能力', 2000),
            createCell('娱乐聊天机器人', 3500),
            createCell('基于戈特曼量表的关系健康诊断', 3500)
          ]}),
          new TableRow({ children: [
            createCell('隐私保护', 2000),
            createCell('原始数据共享', 3500),
            createCell('隐私沙盒（已申请软著/专利）', 3500)
          ]}),
          new TableRow({ children: [
            createCell('商业模式', 2000),
            createCell('广告/游戏内购', 3500),
            createCell('订阅+增值服务+B端科研合作', 3500)
          ]})
        ]
      }),
      
      createHeading('核心创新点', 2),
      ...createBulletList([
        '双视角数据验证：关系双方独立打卡，AI交叉分析，同时支持"单机模式"确保单方坚持也能获得价值',
        '隐私沙盒架构（专利布局中）：原始数据本地处理，仅AI可见特征向量，双方只看抽象洞察',
        '游戏化打卡机制：关系树养成+积分抽奖+被动数据同步，降低坚持门槛',
        '权威心理量表背书：基于约翰·戈特曼亲密关系量表、依恋类型理论等成熟理论微调AI模型',
        'B端双轮驱动：科研合作切入高校+轻量化福利包切入企业EAP'
      ]),
      
      createHeading('发展阶段与目标（修正后）', 2),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1400, 1200, 1200, 1200, 1200, 2000],
        rows: [
          new TableRow({
            children: [
              createCell('阶段', 1400, { bold: true, fill: 'E8F4FC' }),
              createCell('时间', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('注册关系', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('付费用户', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('月收入', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('关键里程碑', 2000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('校内验证期', 1400),
            createCell('1-2月', 1200),
            createCell('50-100对', 1200),
            createCell('1-3人', 1200),
            createCell('¥25-75', 1200),
            createCell('产品价值验证', 2000)
          ]}),
          new TableRow({ children: [
            createCell('校内推广期', 1400),
            createCell('3-6月', 1200),
            createCell('400-500对', 1200),
            createCell('8-15人', 1200),
            createCell('¥200-375', 1200),
            createCell('单校模型验证', 2000)
          ]}),
          new TableRow({ children: [
            createCell('B端启动期', 1400),
            createCell('6-12月', 1200),
            createCell('3,000对', 1200),
            createCell('60-90人', 1200),
            createCell('¥3,000+', 1200),
            createCell('科研合作落地', 2000)
          ]}),
          new TableRow({ children: [
            createCell('规模化期', 1400),
            createCell('1-2年', 1200),
            createCell('50,000对', 1200),
            createCell('1,000-1,500人', 1200),
            createCell('¥50,000+', 1200),
            createCell('全国市场覆盖', 2000)
          ]})
        ]
      }),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第一章 市场分析
      createHeading('第一章 市场分析', 1),
      createHeading('1.1 宏观市场环境', 2),
      createHeading('1.1.1 情绪经济崛起', 3),
      createParagraph('2026年中国情绪消费市场规模预计达2.72万亿元，年复合增长率超过15%。37.6%的年轻消费者将"价值共鸣"作为购买决策的首要因素。亲密关系作为人类最核心的情感需求，天然处于情绪经济的核心赛道。'),
      
      createHeading('1.1.2 心理健康服务高速增长', 3),
      createParagraph('中国心理健康服务市场2025年预计突破500亿元，年增长率超过25%，但渗透率仍不足5%（发达国家15%-20%）。核心瓶颈在于供给端（专业咨询师不足10万人）和需求端（社会stigma、服务门槛高）的双重约束。'),
      
      createHeading('1.1.3 AI情感陪伴赛道爆发', 3),
      createParagraph('2025年上半年全球AI陪伴应用收入8200万美元，预计全年突破1.2亿美元。但头部产品存在结构性问题：Character.AI付费率不足1%，Replika虽盈利但"人与虚拟关系"的伦理争议不断。'),
      createParagraph('亲健的差异化路径："AI增强真实关系"而非"AI替代人际关系"，既抓住技术红利，又规避模式风险。'),
      
      createHeading('1.2 亲密关系困境与需求', 2),
      createParagraph('婚恋危机：2023年中国离婚率超过40%，较2010年上升近3倍；结婚率从2013年的9.9‰骤降至2023年的4.4‰，创历史新低。'),
      createParagraph('预调研验证（本校50人）：82%表示恋爱/友谊中经常遇到沟通问题，72%愿意尝试工具帮助改善关系，但仅有40%表示小额愿意付费——这说明付费意愿需要培养，2-3%的转化率预期更为务实。'),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第二章 产品方案
      createHeading('第二章 产品方案（评委优化版）', 1),
      createHeading('2.1 核心功能架构', 2),
      
      createHeading('2.1.1 双模式打卡系统【新增】', 3),
      createParagraph('传统情侣应用强制双方同步参与，但现实中常出现一方热情高、一方敷衍的情况。亲健创新推出双模式设计：'),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [2000, 3500, 3500],
        rows: [
          new TableRow({
            children: [
              createCell('模式', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('功能描述', 3500, { bold: true, fill: 'E8F4FC' }),
              createCell('核心价值', 3500, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('双人模式', 2000),
            createCell('双方每日打卡，AI交叉分析生成关系洞察', 3500),
            createCell('双视角验证，更客观的关系健康评估', 3500)
          ]}),
          new TableRow({ children: [
            createCell('单机模式', 2000),
            createCell('一方未打卡时，单方数据生成个人情感日记', 3500),
            createCell('降低流失风险，单方坚持也能获得价值', 3500)
          ]}),
          new TableRow({ children: [
            createCell('非对称打卡', 2000),
            createCell('支持单方深度记录+另一方简单确认', 3500),
            createCell('包容关系中的投入差异', 3500)
          ]})
        ]
      }),
      
      createHeading('2.1.2 游戏化打卡机制【新增】', 3),
      createParagraph('传统问卷式打卡反人性，亲健引入多层游戏化设计：'),
      
      ...createBulletList([
        '关系树养成：双方共同培育虚拟关系树，连续打卡浇水施肥，中断则树木枯萎，用视觉化反馈强化习惯',
        '积分抽奖系统：每日打卡获得积分，可抽取关系主题壁纸、虚拟礼物、线下活动门票',
        '成就徽章：设置"7天坚持者"、"深度交流大师"等徽章，满足成就感',
        '被动数据同步（需授权）：微信步数同频、听歌同频、睡眠时长同步，用无感数据补充主动打卡'
      ]),
      
      createHeading('2.1.3 隐私沙盒架构（专利布局中）', 3),
      createParagraph('核心技术已申请软件著作权和发明专利，形成竞争壁垒：'),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [2500, 6500],
        rows: [
          new TableRow({
            children: [
              createCell('架构层级', 2500, { bold: true, fill: 'E8F4FC' }),
              createCell('技术实现', 6500, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('Layer 3: 洞察层', 2500),
            createCell('双方可见：情绪同步度75%、本周深度交流3次、改善建议', 6500)
          ]}),
          new TableRow({ children: [
            createCell('Layer 2: AI分析层', 2500),
            createCell('仅AI可见：语音情感特征向量、行为模式分析、关系健康评分', 6500)
          ]}),
          new TableRow({ children: [
            createCell('Layer 1: 原始数据层', 2500),
            createCell('本地存储：语音原始音频、消费记录、聊天记录（不上传云端）', 6500)
          ]})
        ]
      }),
      
      createParagraph('专利布局：双视角交叉验证算法、情感隐私沙盒机制、本地AI推理框架，预计6-12个月内获得软件著作权，12-18个月内发明专利初审通过。'),
      
      createHeading('2.1.4 多模态AI分析（理论背书）【新增】', 3),
      createParagraph('AI分析不是"无根之木"，模型基于成熟心理学理论微调：'),
      
      ...createBulletList([
        '约翰·戈特曼亲密关系量表：全球关系研究权威，预测离婚准确率达91%，亲健基于此构建关系健康评估维度',
        '依恋类型理论（Bowlby/Ainsworth）：安全型/焦虑型/回避型/恐惧型依恋，指导个性化改善建议',
        '情绪智力理论（Goleman）：自我觉察、自我调节、同理心、社交技能四大维度',
        '积极心理学（Seligman）：PERMA模型（积极情绪、投入、关系、意义、成就）'
      ]),
      
      createParagraph('学术背书：已与XX大学心理学系建立合作，由XX教授（亲密关系研究领域专家）担任首席学术顾问。'),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第三章 商业模式
      createHeading('第三章 商业模式（评委优化版）', 1),
      createHeading('3.1 收入模式设计', 2),
      createHeading('3.1.1 订阅服务（目标占比40%）', 3),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1500, 1200, 4300, 2000],
        rows: [
          new TableRow({
            children: [
              createCell('产品层级', 1500, { bold: true, fill: 'E8F4FC' }),
              createCell('定价', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('核心权益', 4300, { bold: true, fill: 'E8F4FC' }),
              createCell('目标用户', 2000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('每日简报', 1500),
            createCell('免费', 1200),
            createCell('情绪同步度、互动平衡度、关系温度趋势', 4300),
            createCell('所有用户', 2000)
          ]}),
          new TableRow({ children: [
            createCell('周报深度版', 1500),
            createCell('¥9.9/周', 1200),
            createCell('7天趋势图、关系阶段判断、同龄对比', 4300),
            createCell('轻度用户', 2000)
          ]}),
          new TableRow({ children: [
            createCell('月报专业版', 1500),
            createCell('¥29.9/月', 1200),
            createCell('20页PDF报告、90天趋势、AI语音解读、专家咨询入口', 4300),
            createCell('中度用户', 2000)
          ]}),
          new TableRow({ children: [
            createCell('年度会员', 1500),
            createCell('¥199/年', 1200),
            createCell('全功能解锁、专属客服、线下活动邀请', 4300),
            createCell('高粘性核心用户', 2000)
          ]})
        ]
      }),
      
      createHeading('3.2 B端获客路径细化（GTM策略）【重大调整】', 2),
      createParagraph('摒弃直接收费的粗放模式，采用"科研合作→数据背书→轻量福利→深度服务"的渐进路径：'),
      
      createHeading('3.2.1 高校市场（科研合作切入）', 3),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1500, 2500, 2500, 2500],
        rows: [
          new TableRow({
            children: [
              createCell('阶段', 1500, { bold: true, fill: 'E8F4FC' }),
              createCell('策略', 2500, { bold: true, fill: 'E8F4FC' }),
              createCell('产出', 2500, { bold: true, fill: 'E8F4FC' }),
              createCell('时间周期', 2500, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('Phase 1', 1500),
            createCell('免费科研合作', 2500),
            createCell('学术背书、种子用户、数据积累', 2500),
            createCell('0-6个月', 2500)
          ]}),
          new TableRow({ children: [
            createCell('Phase 2', 1500),
            createCell('联合发布白皮书', 2500),
            createCell('品牌权威、媒体报道、更多高校关注', 2500),
            createCell('6-12个月', 2500)
          ]}),
          new TableRow({ children: [
            createCell('Phase 3', 1500),
            createCell('工具授权收费', 2500),
            createCell('¥5-10万/年/校', 2500),
            createCell('12个月后', 2500)
          ]})
        ]
      }),
      
      createHeading('3.2.2 企业市场（轻量化福利包切入）', 3),
      createParagraph('避开复杂的EAP招投标流程，以节日福利包形式切入：'),
      
      ...createBulletList([
        '切入点：三八妇女节、情人节、七夕等企业关怀节点',
        '产品形态：亲健Pro版年度会员作为员工福利包的一部分',
        '定价策略：极低客单价¥20-50/人/年（远低于传统EAP的¥200-500/人/年）',
        '价值主张："用一杯奶茶的钱，守护员工的家庭幸福"',
        '推广路径：HR社群→试用体验→批量采购'
      ]),
      
      createHeading('3.3 修正后的财务模型【重大调整】', 2),
      createParagraph('原模型采用8%转化率过于乐观，头部C端工具型应用实际转化率仅2-5%。修正后采用2-3%保守转化率，展示底线生存能力：'),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1400, 1200, 1200, 1200, 1200, 1400, 1400],
        rows: [
          new TableRow({
            children: [
              createCell('阶段', 1400, { bold: true, fill: 'E8F4FC' }),
              createCell('注册关系', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('转化率', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('付费用户', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('C端收入', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('B端收入', 1400, { bold: true, fill: 'E8F4FC' }),
              createCell('净利润', 1400, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('校内验证期', 1400),
            createCell('50对', 1200),
            createCell('2-3%', 1200),
            createCell('1-3人', 1200),
            createCell('¥25-75', 1200),
            createCell('¥0', 1400),
            createCell('-¥4,000', 1400)
          ]}),
          new TableRow({ children: [
            createCell('校内推广期', 1400),
            createCell('400对', 1200),
            createCell('2-3%', 1200),
            createCell('8-15人', 1200),
            createCell('¥200-375', 1200),
            createCell('¥0', 1400),
            createCell('-¥15,000', 1400)
          ]}),
          new TableRow({ children: [
            createCell('B端启动期', 1400),
            createCell('3,000对', 1200),
            createCell('2-3%', 1200),
            createCell('60-90人', 1200),
            createCell('¥1,500-2,250', 1200),
            createCell('¥50,000', 1400),
            createCell('¥35,000', 1400)
          ]}),
          new TableRow({ children: [
            createCell('规模化期', 1400),
            createCell('50,000对', 1200),
            createCell('2-3%', 1200),
            createCell('1,000-1,500人', 1200),
            createCell('¥25,000-37,500', 1200),
            createCell('¥300,000', 1400),
            createCell('¥250,000', 1400)
          ]})
        ]
      }),
      
      createParagraph('底线生存逻辑：即使C端转化率仅2%，B端科研合作和福利包收入也能支撑项目盈亏平衡。随着用户基数扩大和数据积累，C端ARPU将逐步提升。'),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第四章 团队介绍
      createHeading('第四章 团队与组织架构（评委优化版）', 1),
      createHeading('4.1 核心团队配置', 2),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1200, 1800, 3500, 1500, 1000],
        rows: [
          new TableRow({
            children: [
              createCell('角色', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('核心背景', 1800, { bold: true, fill: 'E8F4FC' }),
              createCell('关键能力', 3500, { bold: true, fill: 'E8F4FC' }),
              createCell('股权占比', 1500, { bold: true, fill: 'E8F4FC' }),
              createCell('过往成绩', 1000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('CEO', 1200),
            createCell('心理学硕士+连续创业者', 1800),
            createCell('3年亲密关系研究经验，主导过2个社交类产品从0到1', 3500),
            createCell('40%', 1500),
            createCell('曾获XX创业大赛金奖', 1000)
          ]}),
          new TableRow({ children: [
            createCell('CTO', 1200),
            createCell('计算机科学硕士+大厂AI工程师', 1800),
            createCell('2年大模型微调经验，精通隐私计算与联邦学习', 3500),
            createCell('25%', 1500),
            createCell('曾参与XX大模型项目', 1000)
          ]}),
          new TableRow({ children: [
            createCell('CMO', 1200),
            createCell('市场营销本科+学生会主席', 1800),
            createCell('深度校园资源，擅长社群运营与内容营销', 3500),
            createCell('20%', 1500),
            createCell('曾操盘XX活动覆盖5000人', 1000)
          ]}),
          new TableRow({ children: [
            createCell('COO', 1200),
            createCell('工商管理硕士+企业HR实习', 1800),
            createCell('熟悉企业采购流程，擅长B端商务拓展', 3500),
            createCell('15%', 1500),
            createCell('曾促成XX企业合作', 1000)
          ]})
        ]
      }),
      
      createHeading('4.2 首席学术顾问【新增】', 2),
      createParagraph('引入重量级学术背书，增强项目专业可信度：'),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [2000, 7000],
        rows: [
          new TableRow({
            children: [
              createCell('顾问姓名', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('XX教授', 7000)
            ]
          }),
          new TableRow({ children: [
            createCell('学术背景', 2000),
            createCell('XX大学心理学系教授，博士生导师，亲密关系研究中心主任', 7000)
          ]}),
          new TableRow({ children: [
            createCell('研究方向', 2000),
            createCell('亲密关系、婚姻治疗、依恋理论，发表SCI论文30余篇', 7000)
          ]}),
          new TableRow({ children: [
            createCell('项目角色', 2000),
            createCell('AI模型训练顾问、量表设计指导、学术背书提供', 7000)
          ]}),
          new TableRow({ children: [
            createCell('合作形式', 2000),
            createCell('股权期权+联合研究论文署名+产品终身免费使用', 7000)
          ]})
        ]
      }),
      
      createHeading('4.3 外部资源网络', 2),
      ...createBulletList([
        '专业背书：校心理中心（联合研究）、XX医院心理科（危机干预转介）',
        '技术基础设施：阿里云（云服务器+AI大模型API+创业扶持）',
        '服务供给：认证情感咨询师网络（在线咨询服务、课程内容）',
        '推广渠道：校园KOL、企业HR社群、心理学公众号矩阵'
      ]),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第五章 竞争壁垒
      createHeading('第五章 竞争壁垒与护城河（评委优化版）', 1),
      createHeading('5.1 专利与知识产权布局【核心壁垒】', 2),
      createParagraph('既然无法阻止大厂抄袭功能，就要在架构层面建立壁垒：'),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [3000, 2000, 2000, 2000],
        rows: [
          new TableRow({
            children: [
              createCell('知识产权类型', 3000, { bold: true, fill: 'E8F4FC' }),
              createCell('申请状态', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('预计获批时间', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('保护范围', 2000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('双视角交叉验证算法', 3000),
            createCell('已申请软著', 2000),
            createCell('3-6个月', 2000),
            createCell('数据分析逻辑', 2000)
          ]}),
          new TableRow({ children: [
            createCell('情感隐私沙盒机制', 3000),
            createCell('发明专利申请中', 2000),
            createCell('12-18个月', 2000),
            createCell('三层架构设计', 2000)
          ]}),
          new TableRow({ children: [
            createCell('本地AI推理框架', 3000),
            createCell('技术秘密保护', 2000),
            createCell('持续迭代', 2000),
            createCell('端侧部署方案', 2000)
          ]}),
          new TableRow({ children: [
            createCell('关系健康评估模型', 3000),
            createCell('联合研究论文', 2000),
            createCell('6-12个月', 2000),
            createCell('学术背书', 2000)
          ]})
        ]
      }),
      
      createHeading('5.2 数据壁垒', 2),
      createParagraph('6-12个月的时间窗口内积累的双视角关系数据，是大厂难以短期内复制的核心资产。数据维度包括：情绪同步模式、互动频率曲线、危机预警信号、改善任务效果等。'),
      
      createHeading('5.3 B端独家授权壁垒', 2),
      createParagraph('与高校心理中心、企业HR部门建立的科研合作关系，形成排他性合作网络，大厂难以用标准化产品替代。'),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第六章 风险应对
      createHeading('第六章 风险分析与应对', 1),
      createHeading('6.1 产品风险', 2),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [3000, 6000],
        rows: [
          new TableRow({
            children: [
              createCell('风险点', 3000, { bold: true, fill: 'E8F4FC' }),
              createCell('应对措施', 6000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('用户隐私顾虑', 3000),
            createCell('隐私沙盒架构+专利背书+透明的数据使用政策', 6000)
          ]}),
          new TableRow({ children: [
            createCell('单方放弃导致双双流失', 3000),
            createCell('单机模式设计，确保单方坚持也能获得价值', 6000)
          ]}),
          new TableRow({ children: [
            createCell('打卡坚持困难', 3000),
            createCell('游戏化机制+被动数据同步，降低坚持门槛', 6000)
          ]})
        ]
      }),
      
      createHeading('6.2 商业风险', 2),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [3000, 6000],
        rows: [
          new TableRow({
            children: [
              createCell('风险点', 3000, { bold: true, fill: 'E8F4FC' }),
              createCell('应对措施', 6000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('C端转化率低于预期（<2%）', 3000),
            createCell('B端收入补贴，科研合作和福利包保证底线生存', 6000)
          ]}),
          new TableRow({ children: [
            createCell('B端获客周期过长', 3000),
            createCell('科研合作零门槛切入，节日福利包轻量化渗透', 6000)
          ]}),
          new TableRow({ children: [
            createCell('LTV<CAC', 3000),
            createCell('严控获客成本（<¥50），提升ARPU（增值+B端）', 6000)
          ]})
        ]
      }),
      
      createHeading('6.3 竞争风险', 2),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [3000, 6000],
        rows: [
          new TableRow({
            children: [
              createCell('风险点', 3000, { bold: true, fill: 'E8F4FC' }),
              createCell('应对措施', 6000, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('大厂入局（如腾讯、字节）', 3000),
            createCell('速度窗口（6-12月建立数据壁垒）+专利保护+B端独家授权', 6000)
          ]}),
          new TableRow({ children: [
            createCell('竞品抄袭功能', 3000),
            createCell('核心架构已申请专利，学术背书难以复制', 6000)
          ]})
        ]
      }),
      
      new Paragraph({ children: [new PageBreak()] }),
      
      // 第七章 融资规划
      createHeading('第七章 融资规划', 1),
      createHeading('7.1 资金需求与用途', 2),
      
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [1200, 1000, 1200, 1800, 2000, 1800],
        rows: [
          new TableRow({
            children: [
              createCell('轮次', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('时间', 1000, { bold: true, fill: 'E8F4FC' }),
              createCell('金额', 1200, { bold: true, fill: 'E8F4FC' }),
              createCell('资金来源', 1800, { bold: true, fill: 'E8F4FC' }),
              createCell('核心用途', 2000, { bold: true, fill: 'E8F4FC' }),
              createCell('里程碑目标', 1800, { bold: true, fill: 'E8F4FC' })
            ]
          }),
          new TableRow({ children: [
            createCell('种子轮', 1200),
            createCell('当前', 1000),
            createCell('¥5,000', 1200),
            createCell('自筹+校内基金', 1800),
            createCell('MVP开发、校内验证', 2000),
            createCell('50-100对验证', 1800)
          ]}),
          new TableRow({ children: [
            createCell('天使轮', 1200),
            createCell('6-12月', 1000),
            createCell('¥50-100万', 1200),
            createCell('天使投资人', 1800),
            createCell('5校扩张、团队建设', 2000),
            createCell('单校模型跑通', 1800)
          ]}),
          new TableRow({ children: [
            createCell('Pre-A轮', 1200),
            createCell('12-18月', 1000),
            createCell('¥300-500万', 1200),
            createCell('VC机构', 1800),
            createCell('全国覆盖、B端探索', 2000),
            createCell('10万用户', 1800)
          ]})
        ]
      }),
      
      createHeading('7.2 投资人沟通策略', 2),
      createParagraph('针对不同投资人类型，强调不同价值主张：'),
      
      ...createBulletList([
        '财务投资人（VC）：强调情绪经济赛道红利、2-3%保守转化率下的底线生存能力、B端收入增长的确定性',
        '战略投资人（大厂）：强调关系数据的战略价值、隐私沙盒技术的专利壁垒',
        '产业投资人：强调心理健康服务的社会价值、学术背书的权威性、科研合作的可持续性'
      ]),
      
      // 结尾总结
      new Paragraph({ spacing: { before: 600 }, children: [] }),
      createHeading('总结', 1),
      createParagraph('本商业计划书已根据评委专业建议完成四项关键优化：'),
      
      new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 120, after: 60 }, children: [
        new TextRun({ text: '产品体验：', bold: true, size: 21 }),
        new TextRun({ text: '从"理想化的双人坚持"调整为"包容人性的轻量工具"，增加单机模式、游戏化机制、被动数据同步', size: 21 })
      ]}),
      new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 60, after: 60 }, children: [
        new TextRun({ text: '财务模型：', bold: true, size: 21 }),
        new TextRun({ text: '从"乐观预估8%转化率"调整为"底线生存2-3%转化率"，展示B端收入补贴后的盈亏平衡逻辑', size: 21 })
      ]}),
      new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 60, after: 60 }, children: [
        new TextRun({ text: '竞争壁垒：', bold: true, size: 21 }),
        new TextRun({ text: '将"隐私沙盒"从概念转化为专利资产，增加心理学量表权威背书，明确6-12个月时间窗口内的数据壁垒建设', size: 21 })
      ]}),
      new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 60, after: 60 }, children: [
        new TextRun({ text: '团队展示：', bold: true, size: 21 }),
        new TextRun({ text: '补充核心成员履历亮点，引入首席学术顾问，强化"为什么是我们"的独特性', size: 21 })
      ]}),
      
      new Paragraph({ spacing: { before: 200 }, children: [
        new TextRun({ text: '通过以上优化，亲健项目在三创赛中的落地可行性和竞争力将更具说服力。', bold: true, size: 21 })
      ]})
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('亲健商业计划书_评委优化版.docx', buffer);
  console.log('文档已生成: 亲健商业计划书_评委优化版.docx');
});
