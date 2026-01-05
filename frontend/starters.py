"""
Starter question definitions for the BedtimeNews chat interface.

This module contains predefined starter questions organized by topic.
"""

import random
from typing import List

import chainlit as cl


# Starter question definitions
STARTERS = [
    {
        "name": "dushanxian_zhaiwu",
        "question": "独山县的债务总额是多少？利息水平如何？",
        "label": "独山县债务",
    },
    {
        "name": "shehuihua_fuyang",
        "question": "什么是社会化抚养？具体包括哪些内容？",
        "label": "社会化抚养",
    },
    {
        "name": "hengshui_moshi",
        "question": "衡水中学的作息时间是怎样安排的？",
        "label": "衡水模式",
    },
    {
        "name": "lianhuaqingwen",
        "question": "世界卫生组织真的推荐连花清瘟吗？",
        "label": "连花清瘟",
    },
    {
        "name": "ewu_zhanzheng",
        "question": "睡前消息为什么能准确预测俄乌战争走向？",
        "label": "俄乌战争",
    },
    {
        "name": "zhengwei_jituan",
        "question": "正威集团是如何超越华为成为广东第一民企的？",
        "label": "正威集团",
    },
    {
        "name": "tesila_vs_guochan",
        "question": "特斯拉和中国电动车品牌在技术和市场上有什么差异？",
        "label": "特斯拉vs国产",
    },
    {
        "name": "jianguan_shixiao",
        "question": "从食品安全到审计独立，第三方监管为什么总是失效？",
        "label": "监管失效",
    },
    {
        "name": "difang_rongzi",
        "question": "地方政府的融资平台和债务问题有哪些共性？",
        "label": "地方融资",
    },
    {
        "name": "zhengji_gongcheng",
        "question": "为什么地方政府热衷于举债搞政绩工程？背后的激励机制是什么？",
        "label": "政绩工程",
    },
    {
        "name": "jiaoyu_yu_renkou",
        "question": "教育资源分配不均和人口危机有什么关系？",
        "label": "教育与人口",
    },
    {
        "name": "yiling_he_zhengwei",
        "question": "以岭药业和正威集团在媒体营销上有什么相似之处？",
        "label": "以岭和正威",
    },
    {
        "name": "spacex_hangtian_geming",
        "question": "SpaceX的成功对传统航天工业体系意味着什么？",
        "label": "SpaceX航天革命",
    },
    {
        "name": "meiyuanhua",
        "question": "为什么新兴经济体总是面临美元化和本币主权的两难选择？",
        "label": "美元化",
    },
    {
        "name": "chengtou_wanghong_chengshi",
        "question": "城投债四大网红城市是哪些？",
        "label": "城投网红城市",
    },
    {
        "name": "renkou_weiji",
        "question": "为什么说中国面临人口危机？",
        "label": "人口危机",
    },
    {
        "name": "hanshujia_gaige",
        "question": "取消寒暑假和搞暑托班相比，哪个更合理？",
        "label": "寒暑假改革",
    },
    {
        "name": "shanhe_sisheng",
        "question": "山河四省指的是哪四个省？",
        "label": "山河四省",
    },
    {
        "name": "gaokao_pingquan",
        "question": "高考平权为什么说广东是突破口？",
        "label": "高考平权",
    },
    {
        "name": "yunnan_baiyao",
        "question": "云南白药的神话是从什么时代开始的？",
        "label": "云南白药",
    },
    {
        "name": "ejun_tuxi",
        "question": "俄罗斯的战略突袭为什么失败了？",
        "label": "俄军突袭",
    },
    {
        "name": "pujing_wupan",
        "question": "普京为什么会高估俄罗斯军队的实力？",
        "label": "普京误判",
    },
    {
        "name": "hanguo_jieyan",
        "question": "韩国国会为什么能这么快推翻戒严令？",
        "label": "韩国戒严",
    },
    {
        "name": "hanyi_bagong",
        "question": "韩国医生为什么集体罢工？",
        "label": "韩医罢工",
    },
    {
        "name": "xinglian_zhanzheng",
        "question": "星链在俄乌战争中发挥了什么作用？",
        "label": "星链战争",
    },
    {
        "name": "zhu_qiguan_yizhi",
        "question": "中国的猪器官移植技术达到什么水平？",
        "label": "猪器官移植",
    },
    {
        "name": "pinduoduo_moshi",
        "question": "拼多多如何利用中国制造业的效率优势？",
        "label": "拼多多模式",
    },
    {
        "name": "c919_dafeiji",
        "question": "国产大飞机C919量产有什么意义？",
        "label": "C919大飞机",
    },
    {
        "name": "dushan_biaozhi_gongcheng",
        "question": "独山县有哪些标志性的政绩工程？",
        "label": "独山标志工程",
    },
    {
        "name": "maotai_yuanshi",
        "question": "茅台院士问题和地方债有什么关系？",
        "label": "茅台院士",
    },
    {
        "name": "yanghang_renkou_baogao",
        "question": "央行人口报告的主要观点是什么？",
        "label": "央行人口报告",
    },
    {
        "name": "shanhe_daxue",
        "question": "为什么山河大学只靠民间热情建不起来？",
        "label": "山河大学",
    },
    {
        "name": "lianhua_shuangmang",
        "question": "连花清瘟研究有没有进行双盲实验？",
        "label": "连花双盲",
    },
    {
        "name": "yiling_yingxiao",
        "question": "以岭药业如何利用媒体进行营销？",
        "label": "以岭营销",
    },
    {
        "name": "wukelan_dikang",
        "question": "乌克兰如何顶住了俄罗斯的进攻？",
        "label": "乌克兰抵抗",
    },
    {
        "name": "zeliansiji",
        "question": "泽连斯基坚持留在基辅有什么意义？",
        "label": "泽连斯基",
    },
    {
        "name": "wangwenyin_chuanqi",
        "question": "王文银的个人经历是怎样的？",
        "label": "王文银传奇",
    },
    {
        "name": "zhengwei_gongchang",
        "question": "正威集团在各地的工厂运营情况如何？",
        "label": "正威工厂",
    },
    {
        "name": "milai_gaige",
        "question": "米莱的美元化政策有什么风险？",
        "label": "米莱改革",
    },
    {
        "name": "yilang_tizhi",
        "question": "伊朗的法基赫制度是如何运作的？",
        "label": "伊朗体制",
    },
    {
        "name": "masike_xinchou",
        "question": "马斯克为什么能获得史上最高薪酬？",
        "label": "马斯克薪酬",
    },
    {
        "name": "bajisitan_zhengju",
        "question": "巴基斯坦的政局为什么这么不稳定？",
        "label": "巴基斯坦政局",
    },
    {
        "name": "spacex_chengben",
        "question": "SpaceX为什么能实现这么低的发射成本？",
        "label": "SpaceX成本",
    },
    {
        "name": "youguan_jianguan",
        "question": "食用油运输罐的监管漏洞在哪里？",
        "label": "油罐监管",
    },
    {
        "name": "puhua_chouwen",
        "question": "普华永道的审计丑闻说明了什么问题？",
        "label": "普华丑闻",
    },
    {
        "name": "baijiu_neijuan",
        "question": "白酒行业为什么开始内卷？",
        "label": "白酒内卷",
    },
    {
        "name": "heilongjiang_renkou_liushi",
        "question": "黑龙江的人口流失有多严重？",
        "label": "黑龙江人口流失",
    },
    {
        "name": "wuren_jiashi",
        "question": "无人驾驶对哪些行业影响最大？",
        "label": "无人驾驶",
    },
    {
        "name": "tianmen_shengyu_jiujia",
        "question": "天门市的生育奇迹为什么被证实是造假？",
        "label": "天门生育造假",
    },
    {
        "name": "shenzhen_wanke_weiji",
        "question": "深圳国资为什么救不了万科的债务危机？",
        "label": "深圳万科危机",
    },
    {
        "name": "yindu_fanzhizhi_yao",
        "question": "印度仿制药为什么能占领欧美市场？",
        "label": "印度仿制药",
    },
    {
        "name": "tengxun_youqu_ip",
        "question": "腾讯为什么要收购《刺客信条》《黑魂》等游戏IP？",
        "label": "腾讯游戏收购",
    },
    {
        "name": "zhongguo_guangfu_channeng",
        "question": "中国光伏产能过剩对新能源发展有什么影响？",
        "label": "光伏产能过剩",
    },
    {
        "name": "tianjin_117_dasha",
        "question": "天津117大厦为什么建成后成了烂尾楼？",
        "label": "天津117大厦",
    },
    {
        "name": "heli_jingji_yu_laodong",
        "question": "河北经济为什么需要依赖外地劳工？",
        "label": "河北经济劳工",
    },
    {
        "name": "danmai_tuiling_nianling",
        "question": "丹麦为什么把退休年龄延长到70岁？",
        "label": "丹麦退休年龄",
    },
    {
        "name": "shenzhen_jichang_paiming",
        "question": "深圳机场是怎么超越香港机场成为第一的？",
        "label": "深圳机场排名",
    },
    {
        "name": "anheicha pianju",
        "question": "安化黑茶为什么会被用于诈骗老年人？",
        "label": "安化黑茶骗局",
    },
    {
        "name": "dunhua_guitang_dianying",
        "question": "电影《归唐》如何还原唐朝历史？",
        "label": "敦煌《归唐》电影",
    },
    {
        "name": "yindu_maopai_geming",
        "question": "印度毛派的土地革命战争为什么持续至今？",
        "label": "印度毛派革命",
    },
    {
        "name": "bidi_baxi_laodong",
        "question": "比亚迪在巴西为什么被指控奴役劳动？",
        "label": "比亚迪巴西劳工",
    },
    {
        "name": "wanling_dianche_luquan",
        "question": "电动自行车应该如何平衡路权和安全？",
        "label": "电动自行车路权",
    },
    {
        "name": "guinei_ximangdu_tiekuang",
        "question": "几内亚西芒杜铁矿对中国有什么战略意义？",
        "label": "几内亚铁矿",
    },
    {
        "name": "shuijing_shi_guoqi",
        "question": "水晶石公司从民企变成国企说明了什么？",
        "label": "水晶石国企",
    },
    {
        "name": "maersheng_jia_kaoche",
        "question": "马督工的家乡内蒙古宁城县为什么出现了\"县改村\"？",
        "label": "宁城县改村",
    },
    {
        "name": "yinwon_laodong_yu_jiaoyu",
        "question": "印尼爪哇岛的人口密度对教育有什么影响？",
        "label": "印尼爪哇人口",
    },
    {
        "name": "hengdian_duanju_chanye",
        "question": "横店短剧产业能否在其他城市复制？",
        "label": "横店短剧产业",
    },
]


def create_starter_actions() -> List[cl.Action]:
    """
    Create Chainlit Action objects for randomly selected starter questions.

    Returns:
        List[cl.Action]: List of 24 randomly selected action buttons
    """
    selected_starters = random.sample(STARTERS, 24)
    return [
        cl.Action(
            name=starter["name"],
            payload={"question": starter["question"]},
            label=starter["label"],
        )
        for starter in selected_starters
    ]
