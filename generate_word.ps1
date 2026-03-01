# Create Word Application
$word = New-Object -ComObject Word.Application
$word.Visible = $false

# Create new document
$doc = $word.Documents.Add()
$selection = $word.Selection

# Set page margins (in points, 72 points = 1 inch)
$pageSetup = $doc.PageSetup
$pageSetup.LeftMargin = 72
$pageSetup.RightMargin = 72
$pageSetup.TopMargin = 72
$pageSetup.BottomMargin = 72

# Helper function to add text with formatting
function Add-Text {
    param(
        [string]$text,
        [int]$size = 12,
        [string]$font = "宋体",
        [bool]$bold = $false,
        [bool]$center = $false
    )
    $selection.Font.Name = $font
    $selection.Font.Size = $size
    $selection.Font.Bold = $bold
    if ($center) {
        $selection.ParagraphFormat.Alignment = 1  # wdAlignParagraphCenter
    } else {
        $selection.ParagraphFormat.Alignment = 0  # wdAlignParagraphLeft
    }
    $selection.TypeText($text)
}

function Add-NewLine {
    $selection.TypeParagraph()
}

# Cover page
Add-NewLine
Add-NewLine
Add-NewLine
Add-Text "亲健" 48 "黑体" $true $true
Add-NewLine
Add-NewLine
Add-Text "——青年亲密关系AI健康管理平台" 22 "黑体" $false $true
Add-NewLine
Add-NewLine
Add-Text "商业计划书" 24 "黑体" $true $true
Add-NewLine
Add-Text "（省赛一等奖优化版）" 16 "楷体" $false $true
Add-NewLine
Add-NewLine
Add-NewLine
Add-NewLine
Add-NewLine
Add-Text "2025年2月" 14 "宋体" $false $true

# Page break
$selection.InsertBreak(7)  # wdPageBreak

# Chapter 1
Add-Text "第一章 执行摘要" 18 "黑体" $true $true
Add-NewLine

# 1.1
Add-Text "1.1 项目定位" 14 "黑体" $true
Add-NewLine
Add-Text "1.1.1 核心定义" 12 "黑体" $true
Add-NewLine
Add-Text "亲健项目以"亲密关系健康管理"为核心定位，开创性地将人工智能技术与权威心理学理论深度融合，构建面向18-40岁青年群体的专业化服务平台。这一市场定位的精准性体现在三个维度：" 12 "宋体"
Add-NewLine
Add-Text "场景聚焦——深耕情侣、夫妻、挚友三类核心人际关系，形成差异化竞争壁垒；" 12 "宋体"
Add-NewLine
Add-Text "技术驱动——通过数据驱动的预防性干预，实现关系健康的主动管理；" 12 "宋体"
Add-NewLine
Add-Text "平台化设计——为后续B端服务拓展预留充足空间，使C端用户积累转化为企业级服务的核心资产。" 12 "宋体"
Add-NewLine

# 1.1.2
Add-Text "1.1.2 目标用户" 12 "黑体" $true
Add-NewLine
Add-Text "亲健的目标用户群体覆盖18-40岁青年，基于深刻的用户行为洞察进行精细化分层运营：" 12 "宋体"
Add-NewLine
Add-Text "18-25岁高校学生群体" 12 "宋体" $true
Add-Text "处于亲密关系探索期，对轻量化、游戏化的关系管理工具接受度高，适合以免费试用+社交裂变快速获取种子用户；" 12 "宋体"
Add-NewLine
Add-Text "26-35岁年轻职场人群" 12 "宋体" $true
Add-Text "面临工作压力与亲密关系维护的双重挑战，对高效、专业的关系改善方案付费意愿更强，适合以专业报告+专家咨询提升客单价；" 12 "宋体"
Add-NewLine
Add-Text "36-40岁已婚人群" 12 "宋体" $true
Add-Text "进入关系深度经营阶段，对夫妻沟通、育儿协作等场景的专业指导需求迫切，适合以家庭账户+育儿专题增强用户粘性。" 12 "宋体"
Add-NewLine

# 1.1.3
Add-Text "1.1.3 核心价值" 12 "黑体" $true
Add-NewLine
Add-Text "亲健的核心价值主张建立在"科学评估"与"个性化改善"两大支柱之上。科学性体现在：引入约翰·戈特曼（John Gottman）的亲密关系研究理论作为底层框架；采用双视角数据采集机制，打破传统单一方自我报告的局限性。个性化体现在：AI系统基于双视角数据为每对关系生成定制化的改善任务推送，形成从认知唤醒到行为改变的完整干预链条。" 12 "宋体"
Add-NewLine

# 1.2
Add-Text "1.2 核心理念" 14 "黑体" $true
Add-NewLine
Add-Text "1.2.1 AI增强真实关系" 12 "黑体" $true
Add-NewLine
Add-Text "2025年上半年全球AI陪伴应用收入达到8200万美元，但头部产品存在结构性困境：Character.AI付费率不足1%，Replika虽盈利却深陷"人与虚拟关系"的伦理争议。这些产品的共同特征是将AI定位为"关系替代者"，用户与虚拟角色建立情感连接，反而可能削弱真实人际关系的能力和质量。" 12 "宋体"
Add-NewLine
Add-Text "亲健选择差异化路径——"AI增强真实关系"，将技术能力聚焦于真实人际关系的诊断与改善支持。双视角数据验证机制确保AI的介入始终以促进真实互动为目标；隐私沙盒架构从技术上杜绝了原始数据的单方获取可能；改善任务系统推送的具体行动均需双方线下完成。" 12 "宋体"
Add-NewLine

# Table 1 - Privacy Sandbox
Add-Text "表1：隐私沙盒三层架构" 10 "宋体" $false $true
Add-NewLine

# Create table
$table1 = $doc.Tables.Add($selection.Range, 4, 4)
$table1.Style = "网格型"
$table1.AllowAutoFit = $false

# Header row
$table1.Cell(1,1).Range.Text = "层级"
$table1.Cell(1,2).Range.Text = "功能定位"
$table1.Cell(1,3).Range.Text = "数据内容"
$table1.Cell(1,4).Range.Text = "访问权限"

# Shade header
for ($col = 1; $col -le 4; $col++) {
    $table1.Cell(1,$col).Shading.BackgroundPatternColor = 14277081  # Light blue
    $table1.Cell(1,$col).Range.Font.Bold = $true
}

# Data rows
$table1.Cell(2,1).Range.Text = "Layer 1"
$table1.Cell(2,2).Range.Text = "原始数据层：本地存储，不上传"
$table1.Cell(2,3).Range.Text = "语音原始音频、详细文字记录、消费记录"
$table1.Cell(2,4).Range.Text = "仅用户本人"

$table1.Cell(3,1).Range.Text = "Layer 2"
$table1.Cell(3,2).Range.Text = "AI分析层：仅AI可见特征向量"
$table1.Cell(3,3).Range.Text = "语音情感特征向量、行为模式标签、关系健康评分"
$table1.Cell(3,4).Range.Text = "仅AI系统"

$table1.Cell(4,1).Range.Text = "Layer 3"
$table1.Cell(4,2).Range.Text = "洞察层：双方可见抽象洞察"
$table1.Cell(4,3).Range.Text = "情绪同步度75%、本周深度交流3次、改善建议"
$table1.Cell(4,4).Range.Text = "关系双方"

# Move selection after table
$selection.Collapse(0)
Add-NewLine
Add-NewLine

# 1.2.2
Add-Text "1.2.2 解决高期待-低能力的关系焦虑" 12 "黑体" $true
Add-NewLine
Add-Text "当代青年群体面临的"高期待-低能力"困境是亲健产品设计的核心问题导向。从社会文化维度来看，浪漫爱情理想的媒体传播与亲密关系教育的社会缺位形成张力；从代际比较维度来看，当代青年对情感满足、个人成长、平等对话等关系质量维度的要求显著提高，但实际的关系经营技能却未能同步发展。" 12 "宋体"
Add-NewLine

# 1.3
Add-Text "1.3 核心创新点" 14 "黑体" $true
Add-NewLine
Add-Text "1.3.1 双视角数据验证" 12 "黑体" $true
Add-NewLine
Add-Text "双视角数据验证是亲健最具技术壁垒的核心创新，其创新性体现在数据采集方法论的根本变革。传统的关系评估工具依赖单一主体自我报告，存在显著的主观偏差；亲健的双视角机制要求关系双方独立、同步完成每日打卡，AI系统对双方数据进行交叉比对，计算"情绪同步度"（双方情绪评分差的绝对值）、"互动平衡度"（双方主动性评分的比值）等衍生指标，识别关系投入的不对称性与互动模式。" 12 "宋体"
Add-NewLine

# Table 2 - Psychology Theory
Add-Text "表2：心理学理论底座与产品应用" 10 "宋体" $false $true
Add-NewLine

$table2 = $doc.Tables.Add($selection.Range, 5, 3)
$table2.Style = "网格型"
$table2.AllowAutoFit = $false

$table2.Cell(1,1).Range.Text = "理论来源"
$table2.Cell(1,2).Range.Text = "核心贡献"
$table2.Cell(1,3).Range.Text = "产品化应用"

for ($col = 1; $col -le 3; $col++) {
    $table2.Cell(1,$col).Shading.BackgroundPatternColor = 14277081
    $table2.Cell(1,$col).Range.Font.Bold = $true
}

$table2.Cell(2,1).Range.Text = '戈特曼"四骑士"理论'
$table2.Cell(2,2).Range.Text = "批评、蔑视、防御、stonewalling预测关系危机"
$table2.Cell(2,3).Range.Text = "AI风险识别特征与温和预警机制"

$table2.Cell(3,1).Range.Text = '戈特曼"5:1积极比例"'
$table2.Cell(3,2).Range.Text = "稳定关系需5次积极互动抵消1次消极互动"
$table2.Cell(3,3).Range.Text = ""互动平衡度"核心指标设计"

$table2.Cell(4,1).Range.Text = "依恋类型理论"
$table2.Cell(4,2).Range.Text = "安全型/焦虑型/回避型/恐惧型依恋模式"
$table2.Cell(4,3).Range.Text = "差异化改善建议推送"

$table2.Cell(5,1).Range.Text = "情绪聚焦疗法（EFT）"
$table2.Cell(5,2).Range.Text = "情绪调节与关系改变技术"
$table2.Cell(5,3).Range.Text = "改善任务内容设计"

$selection.Collapse(0)
Add-NewLine
Add-NewLine

# 1.4
Add-Text "1.4 发展阶段与目标" 14 "黑体" $true
Add-NewLine
Add-Text "表3：亲健四阶段发展目标与财务预测" 10 "宋体" $false $true
Add-NewLine

$table3 = $doc.Tables.Add($selection.Range, 5, 7)
$table3.Style = "网格型"
$table3.AllowAutoFit = $false

$headers = @("阶段", "时间", "注册关系", "付费用户", "月收入", "净利润", "关键里程碑")
for ($i = 0; $i -lt $headers.Count; $i++) {
    $table3.Cell(1,$i+1).Range.Text = $headers[$i]
    $table3.Cell(1,$i+1).Shading.BackgroundPatternColor = 14277081
    $table3.Cell(1,$i+1).Range.Font.Bold = $true
}

$table3.Cell(2,1).Range.Text = "校内验证期"
$table3.Cell(2,2).Range.Text = "1-2月"
$table3.Cell(2,3).Range.Text = "50-100对"
$table3.Cell(2,4).Range.Text = "4-8人"
$table3.Cell(2,5).Range.Text = "¥100-200"
$table3.Cell(2,6).Range.Text = "-¥22,000"
$table3.Cell(2,7).Range.Text = "产品价值验证"

$table3.Cell(3,1).Range.Text = "校内推广期"
$table3.Cell(3,2).Range.Text = "3-6月"
$table3.Cell(3,3).Range.Text = "400-500对"
$table3.Cell(3,4).Range.Text = "32-40人"
$table3.Cell(3,5).Range.Text = "¥800-1,000"
$table3.Cell(3,6).Range.Text = "-¥30,000"
$table3.Cell(3,7).Range.Text = "单校模型验证"

$table3.Cell(4,1).Range.Text = "B端启动期"
$table3.Cell(4,2).Range.Text = "6-12月"
$table3.Cell(4,3).Range.Text = "3,000对"
$table3.Cell(4,4).Range.Text = "240人"
$table3.Cell(4,5).Range.Text = "¥12,000+"
$table3.Cell(4,6).Range.Text = "¥100,000"
$table3.Cell(4,7).Range.Text = "整体盈亏平衡"

$table3.Cell(5,1).Range.Text = "规模化期"
$table3.Cell(5,2).Range.Text = "1-2年"
$table3.Cell(5,3).Range.Text = "50,000对"
$table3.Cell(5,4).Range.Text = "4,000人"
$table3.Cell(5,5).Range.Text = "¥200,000+"
$table3.Cell(5,6).Range.Text = "¥1,000,000+"
$table3.Cell(5,7).Range.Text = "全国市场覆盖"

$selection.Collapse(0)
Add-NewLine

# Save document
$outputPath = "C:\Users\colour\Desktop\亲健\亲健商业计划书.docx"
$doc.SaveAs([ref]$outputPath)
$doc.Close()
$word.Quit()

[System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null

Write-Host "文档已生成: 亲健商业计划书.docx"
