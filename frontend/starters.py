"""
Starter question definitions for the BedtimeNews chat interface.

This module contains predefined starter questions based on the most frequently
referenced topics across all indexed episodes (main, reference, business, commercial, opinion).
"""

from typing import List

import chainlit as cl


# Starter questions based on most common topics in the archive
STARTERS = [
    {
        "name": "local_debt",
        "question": "地方政府的债务问题有多严重？城投债违约风险有多大？",
        "label": "地方政府债务",
    },
    {
        "name": "real_estate",
        "question": "中国房地产市场为什么持续低迷？房产税会推行吗？",
        "label": "房地产与房产税",
    },
    {
        "name": "semiconductors",
        "question": "中国芯片产业能突破美国的技术封锁吗？",
        "label": "芯片产业发展",
    },
    {
        "name": "gaokao_inequality",
        "question": "高考制度是否公平？不同省份的录取分数线差异有多大？",
        "label": "高考平权",
    },
    {
        "name": "demographics_aging",
        "question": "中国人口负增长会对经济发展产生什么影响？",
        "label": "人口危机与老龄化",
    },
    {
        "name": "socialized_childcare",
        "question": "社会化抚养可行吗？如何解决育儿成本高的问题？",
        "label": "社会化抚养",
    },
    {
        "name": "us_china_trade",
        "question": "中美贸易战对中国经济造成了多大影响？",
        "label": "中美贸易战",
    },
    {
        "name": "taiwan_reunification",
        "question": "台湾问题会如何解决？和平统一的可能有多大？",
        "label": "台湾问题",
    },
    {
        "name": "soviet_structural_defects",
        "question": "苏联解体的根本原因是什么？对中国有什么启示？",
        "label": "苏联体制缺陷",
    },
    {
        "name": "belt_road",
        "question": "一带一路倡议的成效如何？是否存在债务陷阱风险？",
        "label": "一带一路",
    },
    {
        "name": "dongbei_decline",
        "question": "东北经济为什么衰退？振兴东北有什么出路？",
        "label": "东北经济",
    },
    {
        "name": "pension_reform",
        "question": "养老金缺口有多大？延迟退休能解决问题吗？",
        "label": "养老金改革",
    },
    {
        "name": "healthcare_reform",
        "question": "为什么看病贵看病难？医疗改革的方向是什么？",
        "label": "医疗改革",
    },
    {
        "name": "education_inequality",
        "question": "教育资源分配不均如何影响社会流动性？",
        "label": "教育公平",
    },
    {
        "name": "property_tax",
        "question": "房产税为什么一直推不动？开征房产税会有什么影响？",
        "label": "房产税政策",
    },
    {
        "name": "infrastructure_overcapacity",
        "question": "基础设施建设是否存在过度投资？回报率如何？",
        "label": "基建投资",
    },
    {
        "name": "soe_reform",
        "question": "国企改革取得了哪些成效？混合所有制改革成功吗？",
        "label": "国企改革",
    },
    {
        "name": "private_sector",
        "question": "为什么民营企业融资难？如何改善营商环境？",
        "label": "民营企业",
    },
    {
        "name": "urban_rural_gap",
        "question": "城乡收入差距有多大？如何实现共同富裕？",
        "label": "城乡差距",
    },
    {
        "name": "space_program",
        "question": "中国航天技术达到了什么水平？与SpaceX相比如何？",
        "label": "航天技术",
    },
    {
        "name": "ev_industry",
        "question": "中国新能源汽车产业有什么优势？能保持领先吗？",
        "label": "新能源汽车",
    },
    {
        "name": "ai_regulation",
        "question": "人工智能发展需要哪些监管？如何平衡创新与安全？",
        "label": "AI监管",
    },
    {
        "name": "hukou_reform",
        "question": "户籍制度改革进展如何？农民工能享受城市公共服务吗？",
        "label": "户籍制度",
    },
    {
        "name": "financial_risk",
        "question": "中国金融系统存在哪些风险？如何防范系统性危机？",
        "label": "金融风险",
    },
    {
        "name": "environmental_protection",
        "question": "碳中和目标能实现吗？环境保护与经济发展如何平衡？",
        "label": "环保与碳中和",
    },
    {
        "name": "rural_revitalization",
        "question": "乡村振兴战略的核心是什么？如何解决三农问题？",
        "label": "乡村振兴",
    },
    {
        "name": "india_competition",
        "question": "印度会成为中国的有力竞争对手吗？中印实力对比如何？",
        "label": "中印对比",
    },
    {
        "name": "russia_ukraine_war",
        "question": "俄乌战争对中国有什么影响？能从中吸取什么教训？",
        "label": "俄乌战争",
    },
    {
        "name": "korean_peninsula",
        "question": "朝鲜半岛局势会如何发展？对中国安全有何影响？",
        "label": "朝鲜半岛",
    },
    {
        "name": "youth_unemployment",
        "question": "为什么年轻人就业难？如何解决青年失业问题？",
        "label": "青年就业",
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
