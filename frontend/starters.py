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
                "label": "比特币与加密货币",
                "question": "比特币为什么能涨到十万美元？去中心化如何创造价值共识？",
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
                "label": "氮化镓半导体",
                "question": "氮化镓半导体是怎么藏在手机充电器里、改变新能源车的？",
            },
            {
                "label": "国产大飞机",
                "question": "国产大飞机量产意味着什么？对中国航空工业有何影响？",
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
                "label": "苏州机场之难",
                "question": "苏州修一个机场为什么这么难？背后是怎样的行政与利益格局？",
            },
            {
                "label": "深中通道与经济洼地",
                "question": "深中通道另一侧为什么是中国经济洼地？",
            },
            {
                "label": "青浦华为城",
                "question": "青浦华为城是不是上海的西部大开发？会带来什么影响？",
            },
        ],
    },
    {
        "name": "国际政治与地缘",
        "topics": [
            {
                "label": "韩国政治危机",
                "question": "尹锡悦三小时政变：为什么韩国总统这个宝座比总统更危险？",
            },
            {
                "label": "俄乌战争分析",
                "question": "从乌克兰没有五千亿到中导部署，俄乌战争告诉我们什么？",
            },
            {
                "label": "叙利亚与中东局势",
                "question": "叙利亚复兴党六十年兴亡史说明了什么？中东局势将如何发展？",
            },
            {
                "label": "琉球问题与东亚地缘",
                "question": "为什么琉球王国覆灭对东亚地缘格局很重要？",
            },
            {
                "label": "委内瑞拉经济危机",
                "question": "委内瑞拉从没缝好的血管：资源陷阱如何摧毁一个国家？",
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
                "label": "印度的跨国追杀",
                "question": "印度为什么把异见者追杀到美国？反映了怎样的治理逻辑？",
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
                "label": "特朗普二进宫",
                "question": "特朗普二次上台，忠臣盈朝和所谓F计划是什么？",
            },
        ],
    },
    {
        "name": "社会民生",
        "topics": [
            {
                "label": "社会化抚养政策",
                "question": "社会化抚养可行吗？如果按照睡前消息的建议实施会面临哪些困难？",
            },
            {
                "label": "衡水模式与教育公平",
                "question": "衡水模式体现了中国教育哪些深层问题？高考制度是否公平？",
            },
            {
                "label": "公共事业定价",
                "question": "为什么广州水价调整会引发争议？公共事业定价机制有什么问题？",
            },
            {
                "label": "农村医疗保障",
                "question": "农民为什么退医保？农村医疗保障体系如何完善？",
            },
            {
                "label": "人口危机",
                "question": "中国人口负增长会对经济发展产生什么影响？生育率3.0就能占稳土地吗？",
            },
            {
                "label": "学历贬值",
                "question": "学历为什么在贬值？张雪峰又值多少钱？",
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
        ],
    },
    {
        "name": "企业与监管",
        "topics": [
            {
                "label": "波音与企业治理",
                "question": "波音百年毁于会计：企业治理出了什么问题？从会计造假看美国制造业衰落",
            },
            {
                "label": "审计独立与会计监管",
                "question": "普华永道事件后，上市公司到底怎么做账？审计独立性为什么这么难？",
            },
            {
                "label": "食品安全监管",
                "question": "从罐车运油到食品安全，第三方监管为什么总是失效？",
            },
            {
                "label": "税收监管",
                "question": "金税4期为什么还不够强？如何解决企业偷税漏税问题？",
            },
            {
                "label": "新公司法",
                "question": "新《公司法》如何拒绝无本万利？对创业者意味着什么？",
            },
            {
                "label": "中公教育",
                "question": "中公教育为什么有钱捐北大十亿、却没钱退学生学费？",
            },
            {
                "label": "商汤科技变局",
                "question": "商汤科技从不差钱到大换血，到底发生了什么？",
            },
            {
                "label": "柔性屏独角兽破产",
                "question": "柔性屏独角兽为什么会破产？天才创始人该负全责吗？",
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
                "label": "城市与商业分布",
                "question": "达美乐指数：为什么说中国城市只有两种？",
            },
            {
                "label": "泡泡玛特出海",
                "question": "泡泡玛特的盲盒为什么能征服东南亚？",
            },
            {
                "label": "情绪价值经济",
                "question": "Jellycat营收破十亿，成年人到底需要多少情绪价值？",
            },
            {
                "label": "胖东来不扩张",
                "question": "胖东来为什么坚持不扩张？这种模式可持续吗？",
            },
            {
                "label": "新消费革命",
                "question": "阿里卖掉银泰，新消费革命为什么失败了？",
            },
            {
                "label": "兰州拉面店",
                "question": "为什么兰州拉面店里总有一个写作业的小孩？",
            },
            {
                "label": "黑神话与文化产业",
                "question": "黑神话开了个好头，做艺术也能赚钱吗？",
            },
            {
                "label": "明星经济学",
                "question": "霉霉狂揽奖金的背后，是怎样的明星经济学？",
            },
            {
                "label": "俄罗斯商品馆",
                "question": "俄罗斯商品馆为什么快速火爆又迅速退潮？",
            },
            {
                "label": "日产本田合并",
                "question": "日产和本田合并，负负就能得正吗？",
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
                "label": "容积率放开",
                "question": "中国放开1.0容积率意味着什么？会改变住宅形态吗？",
            },
            {
                "label": "日本空置房",
                "question": "北海道的房子免费送都没人要，日本空置房问题有多严重？",
            },
        ],
    },
    {
        "name": "科技与前沿",
        "topics": [
            {
                "label": "SpaceX与中国航天",
                "question": "马斯克的星链和星舰对中国航天产业意味着什么？",
            },
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
                "label": "抗癌疫苗真伪",
                "question": "普京宣布的抗癌疫苗，是真突破还是一条广告？",
            },
            {
                "label": "自动驾驶竞争",
                "question": "特斯拉FSD自动驾驶来了，中国智能驾驶还有胜算吗？",
            },
            {
                "label": "无方向盘无人车",
                "question": "拆掉方向盘，马斯克的美国特色无人车有什么不同？",
            },
        ],
    },
]
