"""
Starter question definitions for the BedtimeNews chat interface.

This module contains predefined starter questions based on the most frequently
referenced topics across all indexed episodes (main, reference, business, commercial, opinion).
"""

from typing import List

import chainlit as cl


# Starter questions based on most common topics in the archive
STARTERS = [
    # 经济与产业
    {
        "name": "ai_development",
        "question": "DeepSeek为什么被称为大模型的安卓时刻？中国AI产业发展如何？",
        "label": "AI产业发展",
    },
    {
        "name": "ev_industry_crisis",
        "question": "极越汽车倒闭背后，新能源汽车行业面临什么问题？",
        "label": "新能源汽车危机",
    },
    {
        "name": "bitcoin_crypto",
        "question": "比特币为什么能涨到十万美元？去中心化如何创造价值共识？",
        "label": "比特币与加密货币",
    },
    {
        "name": "semiconductor_taiwan",
        "question": "台积电缺电问题反映了什么？台湾半导体产业有哪些隐患？",
        "label": "台积电与芯片产业",
    },
    {
        "name": "nvidia_ai_chips",
        "question": "英伟达到巅峰了吗？2025年AI芯片产业会如何发展？",
        "label": "英伟达与AI芯片",
    },
    {
        "name": "spacex_starship",
        "question": "马斯克的星链和星舰对中国航天产业意味着什么？",
        "label": "SpaceX与中国航天",
    },
    {
        "name": "china_economy_lowend",
        "question": "为什么中国打火机25年了还卖一块钱？低端制造业如何生存？",
        "label": "中国制造与成本优势",
    },

    # 地方治理与财政
    {
        "name": "local_debt_luzhou",
        "question": "柳州城投债和轻轨烂尾反映了什么问题？地方财政有多难？",
        "label": "地方债务与城投",
    },
    {
        "name": "dushan_debt",
        "question": "独山县烧掉400亿背后，地方政府举债搞政绩工程的激励机制是什么？",
        "label": "独山县与地方政绩工程",
    },
    {
        "name": "maotai_finance",
        "question": "茅台回购股票和城投债之间有什么联系？地方财政对茅台的依赖有多重？",
        "label": "茅台与地方财政",
    },

    # 国际政治与地缘
    {
        "name": "korea_politics",
        "question": "尹锡悦三小时政变：为什么韩国总统这个宝座比总统更危险？",
        "label": "韩国政治危机",
    },
    {
        "name": "russia_ukraine_analysis",
        "question": "从乌克兰没有五千亿到中导部署，俄乌战争告诉我们什么？",
        "label": "俄乌战争分析",
    },
    {
        "name": "syria_history",
        "question": "叙利亚复兴党六十年兴亡史说明了什么？中东局势将如何发展？",
        "label": "叙利亚与中东局势",
    },
    {
        "name": "ryukyu_history",
        "question": "为什么琉球王国覆灭对东亚地缘格局很重要？",
        "label": "琉球问题与东亚地缘",
    },
    {
        "name": "venezuela_economy",
        "question": "委内瑞拉从没缝好的血管：资源陷阱如何摧毁一个国家？",
        "label": "委内瑞拉经济危机",
    },

    # 社会民生
    {
        "name": "socialized_childcare",
        "question": "社会化抚养可行吗？如果按照睡前消息的建议实施会面临哪些困难？",
        "label": "社会化抚养政策",
    },
    {
        "name": "education_hengshui",
        "question": "衡水模式体现了中国教育哪些深层问题？高考制度是否公平？",
        "label": "衡水模式与教育公平",
    },
    {
        "name": "water_price_guangzhou",
        "question": "为什么广州水价调整会引发争议？公共事业定价机制有什么问题？",
        "label": "公共事业定价",
    },
    {
        "name": "rural_healthcare",
        "question": "农民退医保反映了什么问题？农村医疗保障体系如何完善？",
        "label": "农村医疗保障",
    },
    {
        "name": "population_crisis",
        "question": "中国人口负增长会对经济发展产生什么影响？生育率3.0就能占稳土地吗？",
        "label": "人口危机",
    },

    # 企业与监管
    {
        "name": "boeing_accounting",
        "question": "波音百年毁于会计：企业治理出了什么问题？从会计造假看美国制造业衰落",
        "label": "波音与企业治理",
    },
    {
        "name": "pwc_accounting",
        "question": "普华永道事件后，上市公司怎么做账？审计独立性为什么这么难？",
        "label": "审计独立与会计监管",
    },
    {
        "name": "food_safety",
        "question": "从罐车运油到食品安全，第三方监管为什么总是失效？",
        "label": "食品安全监管",
    },
    {
        "name": "golden_tax",
        "question": "金税4期为什么还不够强？如何解决企业偷税漏税问题？",
        "label": "税收监管",
    },

    # 产业观察
    {
        "name": "shein_temu",
        "question": "SHEIN出海为什么成功？中国跨境电商如何征服全球？",
        "label": "跨境电商出海",
    },
    {
        "name": "douyin_ecommerce",
        "question": "TikTok电商狂飙，直播带货在美国行得通吗？",
        "label": "抖音电商全球化",
    },
    {
        "name": "logistics_distribition",
        "question": "达美乐指数：中国城市为什么只有两种？",
        "label": "城市与商业分布",
    },

    # 房地产
    {
        "name": "real_estate_crisis",
        "question": "房价曲线像日本还是美国？深圳八卦岭房价反映了什么问题？",
        "label": "房地产走势",
    },
    {
        "name": "urban_renovation",
        "question": "老破小自拆自建，谁来都没戏？城市更新面临什么困境？",
        "label": "城市更新难题",
    },
]


def create_starter_actions() -> List[cl.Action]:
    """
    Create Chainlit Action objects for all starter questions.

    Returns:
        List[cl.Action]: List of all starter action buttons (no random selection)
    """
    return [
        cl.Action(
            name=starter["name"],
            payload={"question": starter["question"]},
            label=starter["label"],
        )
        for starter in STARTERS
    ]
