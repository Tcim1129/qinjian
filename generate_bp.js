const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, PageOrientation, LevelFormat,
        HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// 定义边框样式
const border = { style: BorderStyle.SINGLE, size: 1, color: "666666" };
const borders = { top: border, bottom: border, left: border, right: border };

// 创建表格单元格的辅助函数
function createCell(text, width, options = {}) {
    const { bold = false, shading = null, rowSpan = 1, colSpan = 1 } = options;
    return new TableCell({
        borders,
        width: { size: width, type: WidthType.DXA },
        shading: shading ? { fill: shading, type: ShadingType.CLEAR } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rowSpan,
        columnSpan: colSpan,
        children: [new Paragraph({
            children: [new TextRun({ text, bold, size: 21 })]
        })]
    });
}

// 创建文档
const doc = new Document({
    styles: {
        default: { document: { run: { font: "宋体", size: 24 } } },
        paragraphStyles: [
            { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 36, bold: true, font: "黑体" },
                paragraph: { spacing: { before: 400, after: 200 }, alignment: AlignmentType.CENTER, outlineLevel: 0 } },
            { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 28, bold: true, font: "黑体" },
                paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 } },
            { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 24, bold: true, font: "黑体" },
                paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
            { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 24, bold: true, font: "宋体" },
                paragraph: { spacing: { before: 150, after: 80 }, outlineLevel: 3 } },
        ]
    },
    numbering: {
        config: [
            { reference: "bullets",
                levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        ]
    },
    sections: [{
        properties: {
            page: {
                size: { width: 11906, height: 16838 },
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
            }
        },
        headers: {
            default: new Header({ children: [new Paragraph({
                children: [new TextRun({ text: "亲健——青年亲密关系AI健康管理平台商业计划书", size: 18, color: "888888" })],
                alignment: AlignmentType.CENTER
            })] })
        },
        footers: {
            default: new Footer({ children: [new Paragraph({
                children: [
                    new TextRun({ text: "第 ", size: 20 }),
                    new TextRun({ children: [PageNumber.CURRENT], size: 20 }),
                    new TextRun({ text: " 页", size: 20 })
                ],
                alignment: AlignmentType.CENTER
            })] })
        },
        children: [
            // 封面
            new Paragraph({ spacing: { before: 2000 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "亲健", bold: true, size: 72, font: "黑体" })]
            }),
            new Paragraph({ spacing: { before: 300 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "——青年亲密关系AI健康管理平台", size: 32, font: "黑体" })]
            }),
            new Paragraph({ spacing: { before: 200 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "商业计划书", size: 36, font: "黑体" })]
            }),
            new Paragraph({ spacing: { before: 100 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "（省赛一等奖优化版）", size: 28, font: "楷体" })]
            }),
            new Paragraph({ spacing: { before: 3000 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "2025年2月", size: 24, font: "宋体" })]
            }),
            new Paragraph({ children: [new PageBreak()] }),

            // 第一章 执行摘要
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第一章 执行摘要")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.1 项目定位")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.1.1 核心定义")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健项目以"亲密关系健康管理"为核心定位，开创性地将人工智能技术与权威心理学理论深度融合，构建面向18-40岁青年群体的专业化服务平台。这一市场定位的精准性体现在三个维度：", 
                    size: 24 
                })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "场景聚焦", bold: true, size: 24 }), new TextRun({ text: "——深耕情侣、夫妻、挚友三类核心人际关系，形成差异化竞争壁垒；", size: 24 })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "技术驱动", bold: true, size: 24 }), new TextRun({ text: "——通过数据驱动的预防性干预，实现关系健康的主动管理；", size: 24 })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "平台化设计", bold: true, size: 24 }), new TextRun({ text: "——为后续B端服务拓展预留充足空间，使C端用户积累转化为企业级服务的核心资产。", size: 24 })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.1.2 目标用户")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健的目标用户群体覆盖18-40岁青年，基于深刻的用户行为洞察进行精细化分层运营：", 
                    size: 24 
                })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "18-25岁高校学生群体", bold: true, size: 24 }), new TextRun({ text: "处于亲密关系探索期，对轻量化、游戏化的关系管理工具接受度高，适合以免费试用+社交裂变快速获取种子用户；", size: 24 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "26-35岁年轻职场人群", bold: true, size: 24 }), new TextRun({ text: "面临工作压力与亲密关系维护的双重挑战，对高效、专业的关系改善方案付费意愿更强，适合以专业报告+专家咨询提升客单价；", size: 24 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "36-40岁已婚人群", bold: true, size: 24 }), new TextRun({ text: "进入关系深度经营阶段，对夫妻沟通、育儿协作等场景的专业指导需求迫切，适合以家庭账户+育儿专题增强用户粘性。", size: 24 })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.1.3 核心价值")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健的核心价值主张建立在"科学评估"与"个性化改善"两大支柱之上。科学性体现在：引入约翰·戈特曼（John Gottman）的亲密关系研究理论作为底层框架；采用双视角数据采集机制，打破传统单一方自我报告的局限性。个性化体现在：AI系统基于双视角数据为每对关系生成定制化的改善任务推送，形成从认知唤醒到行为改变的完整干预链条。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.2 核心理念")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.2.1 AI增强真实关系")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "2025年上半年全球AI陪伴应用收入达到8200万美元，但头部产品存在结构性困境：Character.AI付费率不足1%，Replika虽盈利却深陷"人与虚拟关系"的伦理争议。这些产品的共同特征是将AI定位为"关系替代者"，用户与虚拟角色建立情感连接，反而可能削弱真实人际关系的能力和质量。", 
                    size: 24 
                })]
            }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健选择差异化路径——"AI增强真实关系"，将技术能力聚焦于真实人际关系的诊断与改善支持。双视角数据验证机制确保AI的介入始终以促进真实互动为目标；隐私沙盒架构从技术上杜绝了原始数据的单方获取可能；改善任务系统推送的具体行动均需双方线下完成。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.2.2 解决高期待-低能力的关系焦虑")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "当代青年群体面临的"高期待-低能力"困境是亲健产品设计的核心问题导向。从社会文化维度来看，浪漫爱情理想的媒体传播与亲密关系教育的社会缺位形成张力；从代际比较维度来看，当代青年对情感满足、个人成长、平等对话等关系质量维度的要求显著提高，但实际的关系经营技能却未能同步发展。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.3 核心创新点")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.3.1 双视角数据验证")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "双视角数据验证是亲健最具技术壁垒的核心创新，其创新性体现在数据采集方法论的根本变革。传统的关系评估工具依赖单一主体自我报告，存在显著的主观偏差；亲健的双视角机制要求关系双方独立、同步完成每日打卡，AI系统对双方数据进行交叉比对，计算"情绪同步度"（双方情绪评分差的绝对值）、"互动平衡度"（双方主动性评分的比值）等衍生指标，识别关系投入的不对称性与互动模式。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.3.2 隐私沙盒架构")] }),
            new Paragraph({
                children: [new TextRun({ text: "隐私沙盒架构是亲健回应用户核心顾虑的关键设计，分为三个层次：", size: 24 })]
            }),
            
            // 表1：隐私沙盒架构
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1500, 2500, 2500, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("层级", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("功能定位", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("数据内容", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("访问权限", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 1", 1500),
                            createCell("原始数据层：本地存储，不上传", 2500),
                            createCell("语音原始音频、详细文字记录、消费记录", 2500),
                            createCell("仅用户本人", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 2", 1500),
                            createCell("AI分析层：仅AI可见特征向量", 2500),
                            createCell("语音情感特征向量、行为模式标签、关系健康评分", 2500),
                            createCell("仅AI系统", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 3", 1500),
                            createCell("洞察层：双方可见抽象洞察", 2500),
                            createCell("情绪同步度75%、本周深度交流3次、改善建议", 2500),
                            createCell("关系双方", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表1：隐私沙盒三层架构", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("1.3.3 心理学理论底座")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健的AI模型微调建立在权威心理学理论的坚实基础之上。约翰·戈特曼被誉为"婚姻教皇"，其"爱情实验室"研究通过对40,000余对伴侣的纵向追踪，识别出预测关系成败的关键行为模式。", 
                    size: 24 
                })]
            }),

            // 表2：理论来源
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2000, 3500, 3546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("理论来源", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("核心贡献", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("产品化应用", 3546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("戈特曼"四骑士"理论", 2000),
                            createCell("批评、蔑视、防御、stonewalling预测关系危机", 3500),
                            createCell("AI风险识别特征与温和预警机制", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("戈特曼"5:1积极比例"", 2000),
                            createCell("稳定关系需5次积极互动抵消1次消极互动", 3500),
                            createCell(""互动平衡度"核心指标设计", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("依恋类型理论", 2000),
                            createCell("安全型/焦虑型/回避型/恐惧型依恋模式", 3500),
                            createCell("差异化改善建议推送", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("情绪聚焦疗法（EFT）", 2000),
                            createCell("情绪调节与关系改变技术", 3500),
                            createCell("改善任务内容设计", 3546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表2：心理学理论底座与产品应用", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.4 发展阶段与目标")] }),
            new Paragraph({ children: [new TextRun({ text: "表3：亲健四阶段发展目标与财务预测", size: 20, color: "666666" })] }),
            
            // 表3：发展阶段目标
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 900, 1100, 1100, 1100, 1100, 2346],
                rows: [
                    new TableRow({
                        children: [
                            createCell("阶段", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("时间", 900, { bold: true, shading: "D5E8F0" }),
                            createCell("注册关系", 1100, { bold: true, shading: "D5E8F0" }),
                            createCell("付费用户", 1100, { bold: true, shading: "D5E8F0" }),
                            createCell("月收入", 1100, { bold: true, shading: "D5E8F0" }),
                            createCell("净利润", 1100, { bold: true, shading: "D5E8F0" }),
                            createCell("关键里程碑", 2346, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内验证期", 1400),
                            createCell("1-2月", 900),
                            createCell("50-100对", 1100),
                            createCell("4-8人", 1100),
                            createCell("¥100-200", 1100),
                            createCell("-¥22,000", 1100),
                            createCell("产品价值验证", 2346),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内推广期", 1400),
                            createCell("3-6月", 900),
                            createCell("400-500对", 1100),
                            createCell("32-40人", 1100),
                            createCell("¥800-1,000", 1100),
                            createCell("-¥30,000", 1100),
                            createCell("单校模型验证", 2346),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("B端启动期", 1400),
                            createCell("6-12月", 900),
                            createCell("3,000对", 1100),
                            createCell("240人", 1100),
                            createCell("¥12,000+", 1100),
                            createCell("¥100,000", 1100),
                            createCell("整体盈亏平衡", 2346),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("规模化期", 1400),
                            createCell("1-2年", 900),
                            createCell("50,000对", 1100),
                            createCell("4,000人", 1100),
                            createCell("¥200,000+", 1100),
                            createCell("¥1,000,000+", 1100),
                            createCell("全国市场覆盖", 2346),
                        ]
                    }),
                ]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第二章 市场分析
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第二章 市场分析")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 宏观市场环境")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.1.1 情绪经济崛起")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "情绪经济作为新兴消费形态，正在重塑中国消费市场的结构特征。根据市场研究数据，2026年中国情绪消费市场规模预计达到2.72万亿元，年复合增长率超过15%。37.6%的年轻消费者将"价值共鸣"作为购买决策的首要因素，显著高于价格敏感度（21.3%）与品牌知名度（18.7%）。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.1.2 心理健康服务高速增长")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "中国心理健康服务市场正处于高速成长期，2025年市场规模预计突破500亿元，年增长率超过25%，但渗透率仍不足5%，与发达国家15%-20%的水平存在显著差距。核心瓶颈在于：供给端，专业心理咨询师不足10万人，且分布高度集中于一线城市；需求端，社会stigma（病耻感）导致大量潜在用户不愿寻求专业帮助。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.1.3 AI情感陪伴赛道爆发")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "AI情感陪伴应用在2025年迎来爆发式增长，上半年全球收入达到8200万美元，预计全年突破1.2亿美元。但头部产品的结构性问题为后来者提供了差异化空间：Character.AI付费率不足1%，商业模式高度依赖广告；Replika虽实现盈利，但"人与虚拟关系"的伦理争议不断。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 亲密关系困境与需求")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.2.1 婚恋危机")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "中国正经历深刻的婚恋结构转型。2023年离婚率超过40%，较2010年上升近3倍；结婚率从2013年的9.9‰骤降至2023年的4.4‰，创历史新低。这一趋势的背后是"高期待-低能力"的普遍落差——当代青年对亲密关系的质量期待空前提高，但实际的关系经营能力却未同步提升。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.2.2 友谊淡化")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "社交媒体时代的人际关系呈现出"连接增加、深度减少"的悖论特征。80%的大学生表示有亲密朋友但"感觉关系在淡化"——"点赞之交"取代深度对话，碎片化即时通讯降低了主动联系的动机，地理分散与时间挤压使友谊维护更加困难。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.2.3 预调研验证")] }),
            new Paragraph({ children: [new TextRun({ text: "亲健团队在本校开展的50人预调研为产品设计提供了实证基础：", size: 24 })] }),
            
            // 表4：预调研
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [3500, 2500, 3046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("调研问题", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("结果", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("产品启示", 3046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("恋爱/友谊中遇到过沟通问题？", 3500),
                            createCell("82%"经常"或"有时"", 2500),
                            createCell("沟通辅助是核心痛点", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("希望有工具帮助改善关系？", 3500),
                            createCell("72%"愿意尝试"", 2500),
                            createCell("需求真实存在", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("能接受每天2分钟记录？", 3500),
                            createCell("85%"可以接受"", 2500),
                            createCell("轻量化设计可行", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("愿意为关系改善付费？", 3500),
                            createCell("40%"小额愿意"", 2500),
                            createCell("付费意愿需培养", 3046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表4：亲健预调研核心发现", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.3 校内市场验证场景")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("2.3.1 市场容量测算")] }),
            
            // 表5：市场容量
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2000, 1500, 1500, 4046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("人群细分", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("规模", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("占比", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("特征分析", 4046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("在校生总数", 2000),
                            createCell("15,000人", 1500),
                            createCell("100%", 1500),
                            createCell("—", 4046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("情侣（含暧昧期）", 2000),
                            createCell("4,500人", 1500),
                            createCell("30%", 1500),
                            createCell("主打人群：痛点感知强、互动频率高", 4046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("有亲密朋友者", 2000),
                            createCell("12,000人", 1500),
                            createCell("80%", 1500),
                            createCell("测试人群：市场教育成本低", 4046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("可触达率", 2000),
                            createCell("~70%", 1500),
                            createCell("—", 1500),
                            createCell("3,150对潜在用户", 4046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表5：校内市场容量测算", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第三章 竞品分析
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第三章 竞品分析")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 直接竞品：情侣社交赛道")] }),
            
            // 表6：直接竞品
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1500, 1500, 3500, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("产品", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("用户规模", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("核心问题", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健差异化优势", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("小恩爱", 1500),
                            createCell("3000万", 1500),
                            createCell("功能堆砌（47个二级功能），缺乏AI分析，7日留存降至28%", 3500),
                            createCell("极简设计+AI洞察+价值导向", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Between", 1500),
                            createCell("2500万", 1500),
                            createCell("本土化不足，ARPU仅$0.5/月，已退出中国市场主流", 3500),
                            createCell("深度本土化+技术-政策-文化三位一体", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("微爱", 1500),
                            createCell("5000万下载", 1500),
                            createCell("定位追踪引发隐私争议，评分跌至3.2分", 3500),
                            createCell("健康导向而非监控导向", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表6：直接竞品对比分析", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 间接竞品：心理健康与AI陪伴赛道")] }),
            
            // 表7：间接竞品
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1500, 2000, 3000, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("产品", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("模式", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("核心问题", 3000, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健差异化路径", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Soul", 1500),
                            createCell("陌生人社交", 2000),
                            createCell("关系悖论：匹配成功即用户流失，年流失率>60%", 3000),
                            createCell("服务"经营关系"而非"寻找关系"", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Replika", 1500),
                            createCell("AI虚拟陪伴", 2000),
                            createCell("无法解决真实关系困境，人机关系脆弱", 3000),
                            createCell("服务真实人际关系", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("壹心理", 1500),
                            createCell("专业心理咨询", 2000),
                            createCell("单次300-800元，决策周期长，转化率低", 3000),
                            createCell("轻量化+预防性+日常化", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表7：间接竞品对比分析", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 功能矩阵对比")] }),
            
            // 表8：功能矩阵
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1800, 1000, 1000, 1000, 1000, 1000, 1200, 1046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("功能维度", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("小恩爱", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("Between", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("Soul", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("Replika", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("壹心理", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健", 1200, { bold: true, shading: "E8F5E9" }),
                            createCell("差异", 1046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("情侣关系支持", 1800),
                            createCell("✅", 1000),
                            createCell("✅", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("—", 1046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("夫妻关系支持", 1800),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("独有", 1046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("挚友关系支持", 1800),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("独有", 1046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("双视角互动记录", 1800),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("独有", 1046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("AI关系健康分析", 1800),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("真实关系", 1046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("隐私沙盒保护", 1800),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("❌", 1000),
                            createCell("✅", 1200),
                            createCell("独有", 1046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表8：功能矩阵全面对比", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第四章 产品方案
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第四章 产品方案")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 核心功能架构")] }),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("4.1.1 关系类型选择系统")] }),
            new Paragraph({
                children: [new TextRun({ text: "亲健的用户首次使用流程经过精心设计，三步完成onboarding：", size: 24 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "Step 1：选择关系类型", bold: true, size: 24 }), new TextRun({ text: "。三种选项对应差异化设计：👫 情侣（恋爱中）侧重互动频率、深度交流、情感表达；💑 夫妻（已婚）侧重家务分工、育儿协作、二人世界时间；👭 挚友（闺蜜/兄弟）侧重主动联系、深度分享、共同体验。", size: 24 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "Step 2：邀请对方绑定", bold: true, size: 24 }), new TextRun({ text: "。生成6位数字绑定码，对方输入即完成关系确认，避免复杂的账号注册与权限设置。", size: 24 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "Step 3：开始每日打卡", bold: true, size: 24 }), new TextRun({ text: "。晚21:00推送提醒，2分钟内完成，将行为门槛控制在可接受范围内。", size: 24 })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("4.1.2 双视角/单机兼容打卡")] }),
            
            // 表9：打卡流程
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1200, 3500, 1800, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("步骤", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("问题设计", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("数据类型", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("分析价值", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Step 1", 1200),
                            createCell("今天心情如何？😊😐😢😠", 3500),
                            createCell("情绪评分（1-4分）", 1800),
                            createCell("个人情绪基线，关系情绪传染检测", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Step 2", 1200),
                            createCell("今天和TA互动多吗？", 3500),
                            createCell("互动频率+主动性", 1800),
                            createCell("互动平衡度，关系投入差异识别", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Step 3", 1200),
                            createCell("今天有深度交流吗？（30分钟以上）", 3500),
                            createCell("深度交流布尔值", 1800),
                            createCell("关系质量核心指标，危机预警信号", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Step 4", 1200),
                            createCell("今日任务完成了吗？", 3500),
                            createCell("任务完成率", 1800),
                            createCell("行为改变追踪，干预效果评估", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表9：双视角打卡流程设计", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 隐私沙盒架构")] }),
            
            // 表10：隐私沙盒详细
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1500, 2500, 2500, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("层级", 1500, { bold: true, shading: "D5E8F0" }),
                            createCell("核心机制", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("技术实现", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("用户价值", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 1", 1500),
                            createCell("原始数据层：本地存储，不上传", 2500),
                            createCell("设备端加密存储，任何网络传输均不发生", 2500),
                            createCell("绝对隐私保障，消除数据泄露风险", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 2", 1500),
                            createCell("AI分析层：仅AI可见特征向量", 2500),
                            createCell("端侧MiniCPM-V提取特征，差分隐私添加噪声（ε=1-8）", 2500),
                            createCell("AI有效分析，但任何人无法还原原始内容", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Layer 3", 1500),
                            createCell("洞察层：双方可见抽象洞察", 2500),
                            createCell("云端Qwen2.5-VL推理，输出聚合指标与建议", 2500),
                            createCell("有价值但不可逆向，促进共同行动", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表10：隐私沙盒三层架构详解", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.3 AI关系健康报告")] }),
            
            // 表11：订阅产品
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1800, 1200, 3500, 2546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("产品层级", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("定价", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("核心内容", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("目标用户", 2546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("每日简报（免费）", 1800),
                            createCell("¥0", 1200),
                            createCell("情绪同步度、互动平衡度、关系温度趋势、风险信号、明日建议", 3500),
                            createCell("所有注册用户，培养使用习惯", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("周报深度版", 1800),
                            createCell("¥9.9/周", 1200),
                            createCell("7天趋势图、关系阶段判断、同龄对比、改善方案", 3500),
                            createCell("轻度用户，首次付费转化", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("月报专业版", 1800),
                            createCell("¥29.9/月", 1200),
                            createCell("90天趋势、个性化计划、AI语音解读、专家咨询入口", 3500),
                            createCell("中度用户，高价值服务", 2546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("年度会员", 1800),
                            createCell("¥199/年", 1200),
                            createCell("全功能解锁、专属客服、线下活动邀请", 3500),
                            createCell("高粘性核心用户，提升LTV", 2546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表11：分层订阅产品设计", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.4 游戏化改善任务")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: ""关系树"成长体系是亲健游戏化机制的核心载体。用户完成打卡和任务获得积分，推动关系树从种子→萌芽→幼苗→小树→大树→森林的成长，视觉化进度反馈强化行为动机。", 
                    size: 24 
                })]
            }),
            
            // 表12：任务库
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 3500, 1400, 1400, 1306],
                rows: [
                    new TableRow({
                        children: [
                            createCell("关系类型", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("任务示例", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("积分", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("完成验证", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("难度", 1306, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("情侣", 1400),
                            createCell("睡前说晚安、每周一次约会、写一封情书", 3500),
                            createCell("5-30分", 1400),
                            createCell("双方确认", 1400),
                            createCell("初级-高级", 1306),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("夫妻", 1400),
                            createCell("分担一项家务、安排二人世界时间、感谢对方", 3500),
                            createCell("5-30分", 1400),
                            createCell("双方确认", 1400),
                            createCell("初级-高级", 1306),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("挚友", 1400),
                            createCell("每周主动联系一次、分享一个秘密、一起运动", 3500),
                            createCell("5-30分", 1400),
                            createCell("单方确认", 1400),
                            createCell("初级-高级", 1306),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表12：差异化任务库设计", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第五章 技术架构
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第五章 技术架构与数据壁垒")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 大模型选型策略")] }),
            
            // 表13：大模型选型
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 2200, 1300, 2500, 1646],
                rows: [
                    new TableRow({
                        children: [
                            createCell("部署位置", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("模型", 2200, { bold: true, shading: "D5E8F0" }),
                            createCell("参数", 1300, { bold: true, shading: "D5E8F0" }),
                            createCell("核心优势", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("应用场景", 1646, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("端侧", 1400),
                            createCell("MiniCPM-V 2.6", 2200),
                            createCell("2.8B", 1300),
                            createCell("手机NPU可运行，数据不出设备", 2500),
                            createCell("语音情感分析、文本特征提取", 1646),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("云端", 1400),
                            createCell("Qwen2.5-VL-7B", 2200),
                            createCell("7B", 1300),
                            createCell("中文场景深度优化，复杂推理能力强", 2500),
                            createCell("关系趋势分析、个性化建议生成", 1646),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表13：端-云协同架构设计", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 微调策略")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "采用QLoRA轻量化微调，核心参数：可训练参数~0.5%，显存需求8-12GB，训练时间1-2天，单张RTX 4090即可完成。这一技术选择使初创团队无需大规模算力投入即可实现模型定制化。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.3 核心护城河——私有数据库")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "亲健明确将"私有数据库"而非"专利"定位为核心护城河。通过种子用户积累国内首个"双视角关系行为特征数据库"，其独特性体现在：双视角结构（双方独立记录，交叉验证）、时间序列深度（持续追踪关系发展全过程）、多模态特征（语音、文本、行为多维度）、中文语境（本土文化表达的情感模式）。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.4 数据安全与合规")] }),
            
            // 表14：合规框架
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2500, 3000, 3546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("法规", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("核心要求", 3000, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健应对措施", 3546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("《个人信息保护法》", 2500),
                            createCell("敏感信息需单独同意", 3000),
                            createCell("分层授权设计，一键撤回功能", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("《数据安全法》", 2500),
                            createCell("数据分类分级管理", 3000),
                            createCell("三级数据分类体系（原始/特征/洞察）", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("《生成式人工智能服务管理暂行办法》", 2500),
                            createCell("算法备案、安全评估", 3000),
                            createCell("上线前完成备案，输出标注"AI生成"", 3546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表14：合规框架与技术实现", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第六章 商业模式
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第六章 商业模式与盈利预测")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.1 收入结构")] }),
            
            // 表15：收入结构
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1600, 1600, 3200, 2646],
                rows: [
                    new TableRow({
                        children: [
                            createCell("收入类型", 1600, { bold: true, shading: "D5E8F0" }),
                            createCell("目标占比", 1600, { bold: true, shading: "D5E8F0" }),
                            createCell("核心产品", 3200, { bold: true, shading: "D5E8F0" }),
                            createCell("定价策略", 2646, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("C端订阅", 1600),
                            createCell("40%", 1600),
                            createCell("周报¥9.9、月报¥29.9、年费¥199", 3200),
                            createCell("价值阶梯设计，免费→低价→高价转化", 2646),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("增值服务", 1600),
                            createCell("20%", 1600),
                            createCell("专家咨询¥50-200/次、情感课程¥99/门", 3200),
                            createCell("平台撮合+质量管控，抽成20-30%", 2646),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("B端服务", 1600),
                            createCell("40%", 1600),
                            createCell("高校科研合作¥5-10万/年、企业EAP¥20-100/人/年", 3200),
                            createCell("科研合作建立背书，EAP服务规模化变现", 2646),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表15：三层次收入结构设计", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.2 成本结构")] }),
            
            // 表16：成本结构
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2500, 3000, 3546],
                rows: [
                    new TableRow({
                        children: [
                            createCell("成本类型", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("金额/单价", 3000, { bold: true, shading: "D5E8F0" }),
                            createCell("说明", 3546, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("固定成本", 2500),
                            createCell("¥454/年", 3000),
                            createCell("阿里云服务器¥99/年+小程序认证¥300/年", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("变动成本-单次AI报告", 2500),
                            createCell("¥0.001-0.0065", 3000),
                            createCell("基础版vs深度版token消耗差异", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("变动成本-月成本（1000用户）", 2500),
                            createCell("¥50-200", 3000),
                            createCell("日活60%，50%生成周报，20%生成月报", 3546),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("推广成本-CAC目标", 2500),
                            createCell("¥50-80", 3000),
                            createCell("朋友圈裂变¥5-10、班级群渗透¥10-15、宿舍地推¥15-20", 3546),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表16：成本结构精细化测算", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.3 分阶段盈利预测")] }),
            
            // 表17：财务预测
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1800, 2200, 2200, 2846],
                rows: [
                    new TableRow({
                        children: [
                            createCell("阶段", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("关键指标", 2200, { bold: true, shading: "D5E8F0" }),
                            createCell("财务结果", 2200, { bold: true, shading: "D5E8F0" }),
                            createCell("核心目标", 2846, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内验证期（1-2月）", 1800),
                            createCell("50对注册，2-3%付费转化", 2200),
                            createCell("净利润-¥22,000", 2200),
                            createCell("验证产品价值，获取用户行为数据", 2846),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内推广期（3-6月）", 1800),
                            createCell("400对注册，LTV/CAC=2.5", 2200),
                            createCell("6个月累计-¥30,000", 2200),
                            createCell("单校模型验证，优化转化漏斗", 2846),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("B端启动期（6-12月）", 1800),
                            createCell("3,000对，3所高校+5家企业", 2200),
                            createCell("年度净利润¥100,000", 2200),
                            createCell("整体盈亏平衡，B端收入启动", 2846),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表17：三阶段财务预测与里程碑", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第七章 运营计划
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第七章 运营计划：14天冷启动实验")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.1 MVP实验")] }),
            new Paragraph({
                children: [new TextRun({ 
                    text: "样本：30对真实情侣，为期14天手动打卡实验。验证指标："关系指数波动曲线"（每日关系健康评分的变化趋势）、"AI建议后的行为改变率"（用户实际执行改善任务的比例）。", 
                    size: 24 
                })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.2 渠道组合")] }),
            
            // 表18：渠道组合
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1600, 3200, 1000, 1200, 2046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("渠道", 1600, { bold: true, shading: "D5E8F0" }),
                            createCell("具体动作", 3200, { bold: true, shading: "D5E8F0" }),
                            createCell("预算", 1000, { bold: true, shading: "D5E8F0" }),
                            createCell("目标", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("效率特征", 2046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("朋友圈裂变", 1600),
                            createCell("转发产品海报，邀请成功双方各获7天周报免费体验", 3200),
                            createCell("¥0", 1000),
                            createCell("15对", 1200),
                            createCell("社交信任度高，病毒传播潜力大", 2046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("班级群渗透", 1600),
                            createCell("联系班级干部，以"班级情感建设"名义推广", 3200),
                            createCell("¥0", 1000),
                            createCell("15对", 1200),
                            createCell("转化率稳定，组织动员效应", 2046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("宿舍地推", 1600),
                            createCell("周末晚间扫楼，发放定制书签（带绑定码）", 3200),
                            createCell("¥200", 1000),
                            createCell("20对", 1200),
                            createCell("转化率高，人效低，适合初期验证", 2046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表18：零成本/低成本渠道组合", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.3 B端启动策略")] }),
            
            // 表19：高校合作
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 2500, 2000, 3146],
                rows: [
                    new TableRow({
                        children: [
                            createCell("层级", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("合作内容", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健收益", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("关键成功因素", 3146, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Level 1", 1400),
                            createCell("免费科研合作", 2500),
                            createCell("种子用户+学术信任", 2000),
                            createCell("产品专业性与研究价值证明", 3146),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Level 2", 1400),
                            createCell("数据合作", 2500),
                            createCell("学术背书+联合论文", 2000),
                            createCell("数据质量与合规保障", 3146),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Level 3", 1400),
                            createCell("联合发表", 2500),
                            createCell("品牌权威+招投标资质", 2000),
                            createCell("研究成果的学术影响力", 3146),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Level 4", 1400),
                            createCell("区域独家", 2500),
                            createCell("¥5-10万/年+竞争壁垒", 2000),
                            createCell("前期合作积累的信任与依赖", 3146),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表19：高校合作渐进路径", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.4 关键运营指标")] }),
            
            // 表20：关键指标
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 2200, 1600, 1400, 2446],
                rows: [
                    new TableRow({
                        children: [
                            createCell("维度", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("指标", 2200, { bold: true, shading: "D5E8F0" }),
                            createCell("目标值", 1600, { bold: true, shading: "D5E8F0" }),
                            createCell("监控频率", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("战略意义", 2446, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("北极星指标", 1400),
                            createCell("健康关系数（持续打卡7天以上）", 2200),
                            createCell("阶段增长", 1600),
                            createCell("每周", 1400),
                            createCell("反映产品核心价值的实际交付", 2446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("增长", 1400),
                            createCell("绑定成功率", 2200),
                            createCell(">70%", 1600),
                            createCell("每日", 1400),
                            createCell("双边产品激活的关键门槛", 2446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("活跃", 1400),
                            createCell("日活率", 2200),
                            createCell(">50%", 1600),
                            createCell("每日", 1400),
                            createCell("用户习惯养成的基础", 2446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("商业", 1400),
                            createCell("付费转化率", 2200),
                            createCell("2-3%", 1600),
                            createCell("每周", 1400),
                            createCell("商业模式可行性的关键验证", 2446),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表20：关键运营指标体系", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第八章 团队
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第八章 团队与组织架构")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("8.1 核心团队配置")] }),
            
            // 表21：团队配置
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1600, 1300, 2700, 3446],
                rows: [
                    new TableRow({
                        children: [
                            createCell("角色", 1600, { bold: true, shading: "D5E8F0" }),
                            createCell("股权占比", 1300, { bold: true, shading: "D5E8F0" }),
                            createCell("职责范围", 2700, { bold: true, shading: "D5E8F0" }),
                            createCell("关键任务", 3446, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("CEO/产品", 1600),
                            createCell("40%", 1300),
                            createCell("产品战略、融资对接", 2700),
                            createCell("B端合作谈判、融资对接、产品方向决策", 3446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("CTO/AI", 1600),
                            createCell("25%", 1300),
                            createCell("技术架构、AI集成", 2700),
                            createCell("隐私计算实现、模型优化、技术团队建设", 3446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("CMO/运营", 1600),
                            createCell("20%", 1300),
                            createCell("品牌建设、用户增长", 2700),
                            createCell("校内推广、内容营销、用户社区运营", 3446),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("COO/B端", 1600),
                            createCell("15%", 1300),
                            createCell("商务拓展、资源整合", 2700),
                            createCell("高校/企业合作、资源整合、运营效率优化", 3446),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表21：核心团队配置与分工", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("8.2 外部资源网络")] }),
            
            // 表22：外部资源
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1800, 2000, 3000, 2246],
                rows: [
                    new TableRow({
                        children: [
                            createCell("资源类型", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("合作对象", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("合作内容", 3000, { bold: true, shading: "D5E8F0" }),
                            createCell("当前进度", 2246, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("专业背书", 1800),
                            createCell("校心理中心", 2000),
                            createCell("联合研究、工具授权、用户推荐", 3000),
                            createCell("洽谈中", 2246),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("技术基础设施", 1800),
                            createCell("阿里云", 2000),
                            createCell("云服务器、AI大模型API、创业扶持", 3000),
                            createCell("已开通", 2246),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("服务供给", 1800),
                            createCell("认证情感咨询师", 2000),
                            createCell("在线咨询服务、课程内容", 3000),
                            createCell("初步接触", 2246),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表22：外部资源网络", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第九章 风险分析
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第九章 风险分析与应对")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("9.1 产品风险")] }),
            
            // 表23：产品风险
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2500, 3500, 3046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("风险", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("具体表现", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("应对措施", 3046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("用户隐私顾虑", 2500),
                            createCell("担心情感数据泄露，不敢真实记录", 3500),
                            createCell("隐私沙盒架构，原始数据本地处理，双方只看抽象洞察", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("伴侣关系破裂", 2500),
                            createCell("解绑行为可能引发冲突或负面情绪", 3500),
                            createCell("解绑需双方确认或7天冷静期，解绑后推送关怀内容", 3046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表23：产品风险与应对", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("9.2 商业风险")] }),
            
            // 表24：商业风险
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2500, 3500, 3046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("风险", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("具体表现", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("应对措施", 3046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("LTV<CAC", 2500),
                            createCell("用户获取成本高于生命周期价值", 3500),
                            createCell("B端收入补贴，多渠道获客，严控CAC在¥50-80", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("付费意愿不足", 2500),
                            createCell("免费用户转化付费的比例低于预期", 3500),
                            createCell("价值阶梯设计，免费试用→低价周报→年费路径", 3046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表24：商业风险与应对", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("9.3 竞争风险")] }),
            
            // 表25：竞争风险
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2500, 3500, 3046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("风险", 2500, { bold: true, shading: "D5E8F0" }),
                            createCell("具体表现", 3500, { bold: true, shading: "D5E8F0" }),
                            createCell("应对措施", 3046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("大厂入局", 2500),
                            createCell("互联网巨头推出类似产品", 3500),
                            createCell("速度窗口（6-12月建立数据壁垒）+核心架构专利保护", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("竞品抄袭功能", 2500),
                            createCell("竞争对手复制双视角或隐私沙盒", 3500),
                            createCell("双视角交叉验证算法与情感隐私沙盒机制已申请专利", 3046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("技术迭代", 2500),
                            createCell("大模型技术快速演进，现有方案落后", 3500),
                            createCell("持续优化AI层，数据壁垒+心理学量表独家授权", 3046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表25：竞争风险与应对", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第十章 融资规划
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第十章 融资规划")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("10.1 资金需求与用途")] }),
            
            // 表26：融资规划
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 1200, 1400, 1800, 2000, 1206],
                rows: [
                    new TableRow({
                        children: [
                            createCell("轮次", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("时间", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("金额", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("资金来源", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("核心用途", 2000, { bold: true, shading: "D5E8F0" }),
                            createCell("里程碑", 1206, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("种子轮", 1400),
                            createCell("当前", 1200),
                            createCell("¥5,000", 1400),
                            createCell("自筹+校内创业基金", 1800),
                            createCell("MVP开发、校内验证", 2000),
                            createCell("50-100对", 1206),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("天使轮", 1400),
                            createCell("6-12月", 1200),
                            createCell("¥50-100万", 1400),
                            createCell("天使投资人/校友基金", 1800),
                            createCell("5校扩张、团队建设", 2000),
                            createCell("单校模型", 1206),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("Pre-A轮", 1400),
                            createCell("12-18月", 1200),
                            createCell("¥300-500万", 1400),
                            createCell("VC机构", 1800),
                            createCell("全国市场覆盖、B端深度探索", 2000),
                            createCell("10万用户", 1206),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表26：三阶段融资规划", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("10.2 投资人沟通策略")] }),
            
            // 表27：投资人策略
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [2200, 2800, 4046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("投资人类型", 2200, { bold: true, shading: "D5E8F0" }),
                            createCell("核心关注点", 2800, { bold: true, shading: "D5E8F0" }),
                            createCell("亲健的故事", 4046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("财务投资人（VC）", 2200),
                            createCell("市场规模、增长潜力", 2800),
                            createCell(""情绪经济中的关系健康入口"——2.72万亿情绪消费市场中的垂直赛道领导者", 4046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("战略投资人（大厂）", 2200),
                            createCell("场景协同、生态价值", 2800),
                            createCell(""关系数据的战略价值"——亲密关系数据对社交、内容、消费场景的赋能潜力", 4046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("产业投资人", 2200),
                            createCell("专业壁垒、社会价值", 2800),
                            createCell(""数字化心理健康服务创新"——AI技术降低服务门槛，提升国民关系健康水平", 4046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表27：投资人沟通策略", size: 20, color: "666666" })] }),

            new Paragraph({ children: [new PageBreak()] }),

            // 第十一章 附录
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("第十一章 附录")] }),
            
            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("11.1 核心指标目标汇总")] }),
            
            // 表28：核心指标汇总
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1400, 900, 1200, 1200, 1100, 1200, 2046],
                rows: [
                    new TableRow({
                        children: [
                            createCell("阶段", 1400, { bold: true, shading: "D5E8F0" }),
                            createCell("时间", 900, { bold: true, shading: "D5E8F0" }),
                            createCell("注册关系", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("付费用户", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("月收入", 1100, { bold: true, shading: "D5E8F0" }),
                            createCell("净利润", 1200, { bold: true, shading: "D5E8F0" }),
                            createCell("关键里程碑", 2046, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内验证", 1400),
                            createCell("1-2月", 900),
                            createCell("50对", 1200),
                            createCell("4人", 1200),
                            createCell("¥100", 1100),
                            createCell("-¥22,000", 1200),
                            createCell("产品价值验证", 2046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("校内推广", 1400),
                            createCell("3-6月", 900),
                            createCell("400对", 1200),
                            createCell("32人", 1200),
                            createCell("¥800", 1100),
                            createCell("-¥20,000", 1200),
                            createCell("单校模型验证", 2046),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("B端启动", 1400),
                            createCell("6-12月", 900),
                            createCell("3,000对", 1200),
                            createCell("240人", 1200),
                            createCell("¥12,000+", 1100),
                            createCell("¥100,000", 1200),
                            createCell("整体盈亏平衡", 2046),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表28：核心指标目标汇总", size: 20, color: "666666" })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("11.2 支持材料清单")] }),
            
            // 表29：材料清单
            new Table({
                width: { size: 9046, type: WidthType.DXA },
                columnWidths: [1800, 4500, 2746],
                rows: [
                    new TableRow({
                        children: [
                            createCell("材料类型", 1800, { bold: true, shading: "D5E8F0" }),
                            createCell("具体内容", 4500, { bold: true, shading: "D5E8F0" }),
                            createCell("当前状态", 2746, { bold: true, shading: "D5E8F0" }),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("用户研究", 1800),
                            createCell("50人预调研原始数据与洞察报告", 4500),
                            createCell("已归档", 2746),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("竞品分析", 1800),
                            createCell("小恩爱、Between、Soul、Replika、壹心理深度研究", 4500),
                            createCell("已完成", 2746),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("产品设计", 1800),
                            createCell("产品原型（Figma）与交互流程图", 4500),
                            createCell("进行中", 2746),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("技术文档", 1800),
                            createCell("系统架构设计、数据库Schema、API接口规范", 4500),
                            createCell("初稿完成", 2746),
                        ]
                    }),
                    new TableRow({
                        children: [
                            createCell("财务模型", 1800),
                            createCell("LTV/CAC测算、敏感性分析、融资规划Excel", 4500),
                            createCell("已完成", 2746),
                        ]
                    }),
                ]
            }),
            new Paragraph({ children: [new TextRun({ text: "表29：支持材料清单", size: 20, color: "666666" })] }),

            // 结尾声明
            new Paragraph({ spacing: { before: 600 }, children: [] }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ 
                    text: "本商业计划书基于2024-2025年最新市场数据和行业研究编制，融合隐私沙盒架构、温和AI洞察、保守财务预测、B端双轮驱动四大优化，致力于成为中国青年亲密关系健康管理的首选平台。", 
                    size: 20, 
                    color: "666666",
                    italics: true
                })]
            }),
        ]
    }]
});

// 生成文档
Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("亲健商业计划书.docx", buffer);
    console.log("文档已生成: 亲健商业计划书.docx");
});
