import asyncio
import json
import os
import sys

sys.path.insert(0, r"c:\Users\colour\Desktop\亲健web\backend")

from app.core.config import settings
from app.ai import client

# 1. 完整人物深度条件定义：林夏（伴侣）
PERSONA_LINXIA_CONDITIONS = {
    "person_info": {
        "name": "林夏",
        "relation_role": "同居伴侣（相处2年）",
        "age": 28,
        "occupation": "视觉设计师（近期面临大促项目交稿）",
        "living_region": "上海",
    },
    "psychological_profile": {
        "attachment_style": "轻度焦虑-回避混合型（Anxious-Avoidant）：高压下极易开启心理防御，表现为叹气、冷沉默与内耗，本能排斥他人过度追问与大道理",
        "control_need": "对居住环境整洁度有较高掌控需求，混乱的家务会加剧其失控感与无名火",
        "communication_taboo": "极度反感‘空洞打气’（如‘加油’‘放松点’）、追问细节（‘今天领导又怎么你了’）以及长篇大论的说教",
        "soothing_preference": "偏好‘低压力的物理照顾与非语言陪伴’（如温水、热毛巾、洗切好的水果、允许安静待在同一个空间）",
    },
    "historical_behavior_and_routine": {
        "recent_workload": "过去两周连续 8 个工作日加班至 21:30 以后，周六仍在居家改图",
        "energy_state": "严重睡眠剥夺，身体疲乏指数 9/10，注意力涣散",
        "historical_friction": "3天前的打卡记录中记录：‘看到洗碗槽里堆着锅，虽然没吵，但心里很窒息，感觉永远只有自己在操心家里的琐事’",
    },
    "emotional_trend_and_baseline": {
        "mood_score_trend": "从上周的 8.2（平静愉悦）断崖式下滑至近三天的 5.1（疲惫、委屈、易激惹）",
        "mood_stability": "波动加剧，晚间到家后情绪触底（sighs, social withdrawal）",
        "recent_open_loops": [
            "周三晚上曾因加班错过约定晚餐，回家后两人对话不超过三句，存在尚未化解的轻微疏离感",
            "家务隐性分工矛盾未闭环：林夏认为伴侣总等自己开口才动手，缺乏主动预见性"
        ]
    }
}

async def generate_shallow_response(user_query: str) -> str:
    """普通无画像、肤浅的通用 AI 回答"""
    messages = [
        {"role": "system", "content": "你是亲健助手，请回答用户关于亲密关系的提问。"},
        {"role": "user", "content": user_query}
    ]
    res = await client.chat.completions.create(
        model=settings.AI_TEXT_MODEL,
        messages=messages,
        temperature=0.7,
    )
    return res.choices[0].message.content

async def generate_deep_conditioned_response(user_query: str, conditions: dict) -> tuple[str, str]:
    """深度调用人物性格、行为历史、情绪走势、隐性矛盾后的专业分析与定制回复"""
    system_prompt = f"""你是亲健深度关系认知与行为干预专家系统。
你服务于真实亲密关系中的深度陪伴与协作，必须立足于第一性原理与该用户的全维度真实档案：

【深度学习档案与当前人物条件 (Context Pack)】
{json.dumps(conditions, ensure_ascii=False, indent=2)}

【推理与生成要求】
1. 严禁给出浮于表面的通用“鸡汤”或套路式共情（如单纯说“伴侣加班很辛苦，你要多理解她”）；
2. 必须精确调取并印证该人物目前的条件：
   - 结合她【轻度焦虑-回避依恋防御机制】与【高压下对追问/说教极度反感】的性格特质；
   - 结合她【近3天情绪基线从 8.2 跌至 5.1】的耗竭状态；
   - 结合【3天前洗碗槽堆锅的家务掌控感内耗】与【周三晚餐错过的隐性疏离未闭环】；
3. 输出分为两部分：
   【深度调性分析与决策依据】：向用户拆解林夏当前的真实心理防御层、为什么普通关心会失效、这次行动需要激活的心理机制；
   【高定制化执行方案与原话】：给出符合林夏习惯的物理照顾步骤与直接可用的原话（要求：低语言负荷、把家务主动做掉而不是问她要不要做、赋予她不说话的充分安全感）。
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    res = await client.chat.completions.create(
        model=settings.AI_TEXT_MODEL,
        messages=messages,
        temperature=0.7,
    )
    return res.choices[0].message.content

async def main():
    user_query = "林夏最近加班特别多，回家后经常叹气。我想关心但又怕说错话让她觉得更烦，我到底该怎么做、怎么开口比较好？"
    
    print("=" * 70)
    print("【测试场景】提问：林夏最近加班特别多，回家后经常叹气。我想关心但又怕说错话让她觉得更烦，我到底该怎么做、怎么开口比较好？")
    print("【大模型核心引擎】:", settings.AI_TEXT_MODEL)
    print("=" * 70)
    
    print("\n>>> 正在生成【对照组 1：传统无人物画像的普通/肤浅回答】...")
    shallow = await generate_shallow_response(user_query)
    
    print("\n>>> 正在生成【对照组 2：深度学习并调用人物性格、行为习惯、情绪走势与过往矛盾后的专业回答】...")
    deep = await generate_deep_conditioned_response(user_query, PERSONA_LINXIA_CONDITIONS)
    
    print("\n" + "=" * 70)
    print("【对照组 1：普通/肤浅回答】（未调用该人物历史条件）")
    print("-" * 70)
    print(shallow)
    print("=" * 70)
    
    print("\n" + "=" * 70)
    print("【对照组 2：深度调用林夏性格、行为习惯、情绪走势后的回答】")
    print("-" * 70)
    print(deep)
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
