"""
Sample-question data for the BedtimeNews knowledge base.

Questions grouped by category, derived from real episodes across the archive
(高见 / 产经破壁机 / 讲点黑话 and others). The frontend flattens these, shuffles
them, and shows a random subset on each visit (the full question is the clickable
text). This module is plain data with no UI-framework dependency; the server
exposes it as JSON at /api/starters.
"""

from typing import TypedDict


class Topic(TypedDict):
    label: str  # short human-readable title (metadata; UI shows `question`)
    question: str  # the full question sent to the agent and shown as the link


class Category(TypedDict):
    name: str  # Chinese category name (organizational metadata)
    topics: list[Topic]


CATEGORIES: list[Category] = [
    {
        "name": "经济与产业",
        "topics": [
            {
                "label": "AI产业发展",
                "question": "DeepSeek为什么被称为大模型的安卓时刻？中国AI产业发展如何？",
            },
            {
                "label": "台积电与芯片产业",
                "question": "台积电缺电问题反映了什么？台湾半导体产业有哪些隐患？",
            },
            {
                "label": "英伟达与AI芯片",
                "question": "英伟达到巅峰了吗？2025年AI芯片产业会如何发展？",
            },
            {
                "label": "中国制造与成本优势",
                "question": "为什么中国打火机25年了还卖一块钱？低端制造业如何生存？",
            },
            {
                "label": "特斯拉估值",
                "question": "特斯拉市值为什么能突破万亿美元？凭什么这么贵？",
            },
            {
                "label": "黄金为何疯涨",
                "question": "黄金为什么疯涨？老铺黄金又凭什么卖这么贵？",
            },
            {
                "label": "拼多多与消费降级",
                "question": "拼多多等于消费降级吗？这种理解为什么是反的？",
            },
            {
                "label": "中欧班列",
                "question": "中欧班列在疫情期间为什么能逆势增长？它的经济账怎么算？",
            },
            {
                "label": "光刻机国产化",
                "question": "国产光刻机的进展到了哪一步？卡脖子问题能解决吗？",
            },
            {
                "label": "光伏产能过剩",
                "question": "光伏产业为什么陷入产能过剩和价格战？还有出路吗？",
            },
            {
                "label": "比亚迪与电动车出海",
                "question": "比亚迪凭什么成为新能源车之王？中国电动车出海面临哪些阻力？",
            },
            {
                "label": "宁德时代与动力电池",
                "question": "宁德时代是怎么称霸动力电池的？这条产业链有多重要？",
            },
            {
                "label": "中美贸易战",
                "question": "中美贸易战和关税博弈对中国经济意味着什么？",
            },
            {
                "label": "人民币国际化",
                "question": "人民币国际化和去美元化进展到哪一步了？",
            },
            {
                "label": "民营经济信心",
                "question": "民营经济信心为什么不足？提振民企需要解决什么？",
            },
        ],
    },
    {
        "name": "地方治理与财政",
        "topics": [
            {
                "label": "地方债务与城投",
                "question": "柳州城投债和轻轨烂尾反映了什么问题？地方财政有多难？",
            },
            {
                "label": "独山县与政绩工程",
                "question": "独山县烧掉400亿背后，地方政府举债搞政绩工程的激励机制是什么？",
            },
            {
                "label": "茅台与地方财政",
                "question": "茅台回购股票和城投债之间有什么联系？地方财政对茅台的依赖有多重？",
            },
            {
                "label": "深中通道与经济洼地",
                "question": "深中通道另一侧为什么是中国经济洼地？",
            },
            {
                "label": "丽江观光火车",
                "question": "丽江观光火车为什么停运？旅游交通项目为什么容易亏损？",
            },
            {
                "label": "高铁债务",
                "question": "中国高铁的巨额债务可持续吗？高铁的经济账该怎么算？",
            },
            {
                "label": "收缩型城市",
                "question": "鹤岗为什么成了收缩型城市的代表？人口流失的城市该怎么办？",
            },
            {
                "label": "土地财政",
                "question": "土地财政是怎么形成的？卖地收入下滑后地方政府怎么办？",
            },
            {
                "label": "公务员降薪",
                "question": "多地公务员降薪说明了什么？财政供养压力有多大？",
            },
            {
                "label": "专项债",
                "question": "地方专项债越发越多，钱都投到哪去了？有没有效益？",
            },
        ],
    },
    {
        "name": "国际政治与地缘",
        "topics": [
            {
                "label": "俄乌战争分析",
                "question": "从乌克兰没有五千亿到中导部署，俄乌战争告诉我们什么？",
            },
            {
                "label": "叙利亚与中东局势",
                "question": "叙利亚复兴党六十年兴亡史说明了什么？中东局势将如何发展？",
            },
            {
                "label": "阿根廷美元化",
                "question": "阿根廷美元化是不是新鲜的试验？米莱的改革到底想要什么？",
            },
            {
                "label": "朝鲜的转向",
                "question": "金正恩做出了一个违背祖宗的决定，朝鲜在改变什么？",
            },
            {
                "label": "孟加拉变天",
                "question": "孟加拉考公人掀桌、政权更迭，说明了什么深层问题？",
            },
            {
                "label": "墨西哥与禁毒",
                "question": "墨西哥新总统为什么不想再替美国扫毒了？",
            },
            {
                "label": "对华投资限制",
                "question": "美国限制对华投资的行政命令影响有多大？涉及哪些领域？",
            },
            {
                "label": "黑海舰队",
                "question": "黑海舰队为什么屡屡被乌克兰无人艇击中？",
            },
            {
                "label": "缅甸内战",
                "question": "缅甸内战为什么愈演愈烈？掸邦和果敢的局势是怎么回事？",
            },
            {
                "label": "加沙冲突",
                "question": "加沙冲突为什么持续不断？巴以问题的死结到底在哪？",
            },
            {
                "label": "台海局势",
                "question": "台海局势为什么持续紧张？两岸统一的难点在哪？",
            },
            {
                "label": "欧洲能源危机",
                "question": "俄乌冲突下的欧洲能源危机是怎么演变的？",
            },
        ],
    },
    {
        "name": "社会民生",
        "topics": [
            {
                "label": "人口危机",
                "question": "中国人口负增长会对经济发展产生什么影响？生育率3.0就能占稳土地吗？",
            },
            {
                "label": "无效内卷",
                "question": "为什么职场上总会出现无效内卷？根源在哪里？",
            },
            {
                "label": "编制与就业",
                "question": "政府送编制，学生为什么反而不敢要？",
            },
            {
                "label": "韩国医改",
                "question": "韩国13万医生对抗5000万人罢工，医改为什么这么难？",
            },
            {
                "label": "动态清零退出",
                "question": "健康码和动态清零政策是如何一步步退出的？",
            },
            {
                "label": "预制菜进校园",
                "question": "预制菜进校园为什么引发家长强烈反对？预制菜产业有什么隐患？",
            },
            {
                "label": "双减政策",
                "question": "双减政策为什么没能真正减轻教育内卷？教培行业经历了什么？",
            },
            {
                "label": "日本核污水",
                "question": "日本核污水排海为什么引发这么大争议？影响到底有多大？",
            },
            {
                "label": "医保改革",
                "question": "医保门诊统筹改革为什么让一些人感觉吃亏了？",
            },
            {
                "label": "天价彩礼",
                "question": "天价彩礼为什么屡禁不止？背后是怎样的婚育困境？",
            },
            {
                "label": "撤点并校",
                "question": "农村撤点并校为什么让上学变难了？乡村教育路在何方？",
            },
        ],
    },
    {
        "name": "企业与监管",
        "topics": [
            {
                "label": "审计独立与会计监管",
                "question": "普华永道事件后，上市公司到底怎么做账？审计独立性为什么这么难？",
            },
            {
                "label": "药品集采",
                "question": "药品集采是如何把药价打下来的？对医药行业意味着什么？",
            },
            {
                "label": "蚂蚁上市暂停",
                "question": "蚂蚁集团上市为什么被紧急叫停？金融科技监管收紧说明了什么？",
            },
            {
                "label": "医药反腐",
                "question": "医药行业反腐风暴是怎么回事？回扣和带金销售为什么屡禁不止？",
            },
            {
                "label": "平台反垄断",
                "question": "阿里被罚182亿之后，平台经济反垄断改变了什么？",
            },
        ],
    },
    {
        "name": "产业观察",
        "topics": [
            {
                "label": "跨境电商出海",
                "question": "SHEIN出海为什么成功？又为什么上市一波三折？",
            },
            {
                "label": "抖音电商全球化",
                "question": "TikTok电商狂飙，直播带货在美国行得通吗？",
            },
            {
                "label": "日产本田合并",
                "question": "日产和本田合并，负负就能得正吗？",
            },
            {
                "label": "短剧出海",
                "question": "微短剧为什么能在海外爆火？这门生意能持续吗？",
            },
        ],
    },
    {
        "name": "房地产",
        "topics": [
            {
                "label": "房地产走势",
                "question": "房价曲线像日本还是美国？深圳八卦岭房价反映了什么问题？",
            },
            {
                "label": "城市更新难题",
                "question": "老破小自拆自建，为什么谁来都没戏？城市更新面临什么困境？",
            },
            {
                "label": "房地产税",
                "question": "房地产税立法为什么推进这么难？开征会带来什么影响？",
            },
            {
                "label": "恒大爆雷",
                "question": "恒大是怎么一步步爆雷的？许家印的债务危机暴露了房地产什么问题？",
            },
            {
                "label": "保交楼与停贷",
                "question": "烂尾楼和停贷潮是怎么发生的？保交楼为什么这么难？",
            },
            {
                "label": "城中村改造",
                "question": "新一轮城中村改造能托起楼市吗？和棚改有什么不同？",
            },
        ],
    },
    {
        "name": "科技与前沿",
        "topics": [
            {
                "label": "星链军事潜力",
                "question": "SpaceX的军事潜力有多大？中国应该如何应对？",
            },
            {
                "label": "中国深空工程",
                "question": "中国工程师到月球修路，意味着中国航天到了什么阶段？",
            },
            {
                "label": "脑机接口",
                "question": "脑机接口技术现在发展到了哪一步？前景如何？",
            },
            {
                "label": "猪器官移植",
                "question": "中美猪器官移植竞赛，能解决中国的器官短缺问题吗？",
            },
            {
                "label": "自动驾驶竞争",
                "question": "特斯拉FSD自动驾驶来了，中国智能驾驶还有胜算吗？",
            },
            {
                "label": "LK-99室温超导",
                "question": "LK-99室温超导事件是怎么回事？为什么最后被证伪？",
            },
        ],
    },
]
