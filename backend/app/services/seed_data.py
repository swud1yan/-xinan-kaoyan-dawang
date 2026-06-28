"""
Complete seed data: subject catalog, undergrad schools, 150 national schools
"""
# ============================================================
# 学科目录（一级→二级，涵盖所有门类）
# ============================================================
SUBJECT_CATALOG = [
    # 工学 (08)
    {"code": "08", "name": "工学", "level": 1, "parent_id": None},
    {"code": "0802", "name": "机械工程", "level": 2, "parent_code": "08"},
    {"code": "0805", "name": "材料科学与工程", "level": 2, "parent_code": "08"},
    {"code": "0807", "name": "动力工程及工程热物理", "level": 2, "parent_code": "08"},
    {"code": "0808", "name": "电气工程", "level": 2, "parent_code": "08"},
    {"code": "0809", "name": "电子科学与技术", "level": 2, "parent_code": "08"},
    {"code": "0810", "name": "信息与通信工程", "level": 2, "parent_code": "08"},
    {"code": "0811", "name": "控制科学与工程", "level": 2, "parent_code": "08"},
    {"code": "0812", "name": "计算机科学与技术", "level": 2, "parent_code": "08"},
    {"code": "0813", "name": "建筑学", "level": 2, "parent_code": "08"},
    {"code": "0814", "name": "土木工程", "level": 2, "parent_code": "08"},
    {"code": "0817", "name": "化学工程与技术", "level": 2, "parent_code": "08"},
    {"code": "0823", "name": "交通运输工程", "level": 2, "parent_code": "08"},
    {"code": "0825", "name": "航空宇航科学与技术", "level": 2, "parent_code": "08"},
    {"code": "0830", "name": "环境科学与工程", "level": 2, "parent_code": "08"},
    {"code": "0831", "name": "生物医学工程", "level": 2, "parent_code": "08"},
    {"code": "0835", "name": "软件工程", "level": 2, "parent_code": "08"},
    {"code": "0839", "name": "网络空间安全", "level": 2, "parent_code": "08"},
    {"code": "0854", "name": "电子信息", "level": 2, "parent_code": "08"},
    {"code": "0855", "name": "智能制造工程", "level": 2, "parent_code": "08"},
    {"code": "0858", "name": "能源动力", "level": 2, "parent_code": "08"},
    # 理学 (07)
    {"code": "07", "name": "理学", "level": 1, "parent_id": None},
    {"code": "0701", "name": "数学", "level": 2, "parent_code": "07"},
    {"code": "0702", "name": "物理学", "level": 2, "parent_code": "07"},
    {"code": "0703", "name": "化学", "level": 2, "parent_code": "07"},
    {"code": "0710", "name": "生物学", "level": 2, "parent_code": "07"},
    {"code": "0713", "name": "生态学", "level": 2, "parent_code": "07"},
    {"code": "0714", "name": "统计学", "level": 2, "parent_code": "07"},
    # 文学 (05)
    {"code": "05", "name": "文学", "level": 1, "parent_id": None},
    {"code": "0501", "name": "中国语言文学", "level": 2, "parent_code": "05"},
    {"code": "0502", "name": "外国语言文学", "level": 2, "parent_code": "05"},
    {"code": "0503", "name": "新闻传播学", "level": 2, "parent_code": "05"},
    # 管理学 (12)
    {"code": "12", "name": "管理学", "level": 1, "parent_id": None},
    {"code": "1201", "name": "管理科学与工程", "level": 2, "parent_code": "12"},
    {"code": "1202", "name": "工商管理", "level": 2, "parent_code": "12"},
    {"code": "1204", "name": "公共管理", "level": 2, "parent_code": "12"},
    {"code": "1205", "name": "图书情报与档案管理", "level": 2, "parent_code": "12"},
    # 经济学 (02)
    {"code": "02", "name": "经济学", "level": 1, "parent_id": None},
    {"code": "0201", "name": "理论经济学", "level": 2, "parent_code": "02"},
    {"code": "0202", "name": "应用经济学", "level": 2, "parent_code": "02"},
    {"code": "0251", "name": "金融", "level": 2, "parent_code": "02"},
    # 法学 (03)
    {"code": "03", "name": "法学", "level": 1, "parent_id": None},
    {"code": "0301", "name": "法学", "level": 2, "parent_code": "03"},
    {"code": "0302", "name": "政治学", "level": 2, "parent_code": "03"},
    {"code": "0303", "name": "社会学", "level": 2, "parent_code": "03"},
    {"code": "0305", "name": "马克思主义理论", "level": 2, "parent_code": "03"},
    # 教育学 (04)
    {"code": "04", "name": "教育学", "level": 1, "parent_id": None},
    {"code": "0401", "name": "教育学", "level": 2, "parent_code": "04"},
    {"code": "0402", "name": "心理学", "level": 2, "parent_code": "04"},
    {"code": "0403", "name": "体育学", "level": 2, "parent_code": "04"},
    # 农学 (09)
    {"code": "09", "name": "农学", "level": 1, "parent_id": None},
    {"code": "0901", "name": "作物学", "level": 2, "parent_code": "09"},
    {"code": "0902", "name": "园艺学", "level": 2, "parent_code": "09"},
    {"code": "0905", "name": "畜牧学", "level": 2, "parent_code": "09"},
    {"code": "0906", "name": "兽医学", "level": 2, "parent_code": "09"},
    # 医学 (10)
    {"code": "10", "name": "医学", "level": 1, "parent_id": None},
    {"code": "1001", "name": "基础医学", "level": 2, "parent_code": "10"},
    {"code": "1002", "name": "临床医学", "level": 2, "parent_code": "10"},
    {"code": "1003", "name": "口腔医学", "level": 2, "parent_code": "10"},
    {"code": "1004", "name": "公共卫生与预防医学", "level": 2, "parent_code": "10"},
    {"code": "1005", "name": "中医学", "level": 2, "parent_code": "10"},
    {"code": "1007", "name": "药学", "level": 2, "parent_code": "10"},
    {"code": "1011", "name": "护理学", "level": 2, "parent_code": "10"},
    # 艺术学 (13)
    {"code": "13", "name": "艺术学", "level": 1, "parent_id": None},
    {"code": "1301", "name": "艺术学理论", "level": 2, "parent_code": "13"},
    {"code": "1302", "name": "音乐与舞蹈学", "level": 2, "parent_code": "13"},
    {"code": "1303", "name": "美术学", "level": 2, "parent_code": "13"},
    {"code": "1305", "name": "设计学", "level": 2, "parent_code": "13"},
]

# Build parent/child relationships
LEVEL1_CODES = {}
LEVEL2_ITEMS = {}
for item in SUBJECT_CATALOG:
    if item["level"] == 1:
        LEVEL1_CODES[item["code"]] = item["name"]
        LEVEL2_ITEMS[item["code"]] = []
for item in SUBJECT_CATALOG:
    if item["level"] == 2 and item.get("parent_code"):
        pc = item["parent_code"]
        if pc in LEVEL2_ITEMS:
            LEVEL2_ITEMS[pc].append(item)

# ============================================================
# 云贵川渝本科院校
# ============================================================
UNDERGRAD_SCHOOLS = [
    # 重庆
    {"name": "重庆大学", "province": "重庆", "city": "重庆", "type": "综合"},
    {"name": "西南大学", "province": "重庆", "city": "重庆", "type": "综合"},
    {"name": "西南政法大学", "province": "重庆", "city": "重庆", "type": "政法"},
    {"name": "重庆邮电大学", "province": "重庆", "city": "重庆", "type": "理工"},
    {"name": "重庆交通大学", "province": "重庆", "city": "重庆", "type": "理工"},
    {"name": "重庆医科大学", "province": "重庆", "city": "重庆", "type": "医药"},
    {"name": "重庆师范大学", "province": "重庆", "city": "重庆", "type": "师范"},
    {"name": "重庆工商大学", "province": "重庆", "city": "重庆", "type": "财经"},
    {"name": "重庆理工大学", "province": "重庆", "city": "重庆", "type": "理工"},
    {"name": "四川外国语大学", "province": "重庆", "city": "重庆", "type": "语言"},
    {"name": "四川美术学院", "province": "重庆", "city": "重庆", "type": "艺术"},
    # 四川
    {"name": "四川大学", "province": "四川", "city": "成都", "type": "综合"},
    {"name": "电子科技大学", "province": "四川", "city": "成都", "type": "理工"},
    {"name": "西南交通大学", "province": "四川", "city": "成都", "type": "理工"},
    {"name": "西南财经大学", "province": "四川", "city": "成都", "type": "财经"},
    {"name": "四川农业大学", "province": "四川", "city": "雅安", "type": "农林"},
    {"name": "成都理工大学", "province": "四川", "city": "成都", "type": "理工"},
    {"name": "西南石油大学", "province": "四川", "city": "成都", "type": "理工"},
    {"name": "成都信息工程大学", "province": "四川", "city": "成都", "type": "理工"},
    {"name": "西华大学", "province": "四川", "city": "成都", "type": "综合"},
    {"name": "四川师范大学", "province": "四川", "city": "成都", "type": "师范"},
    {"name": "西华师范大学", "province": "四川", "city": "南充", "type": "师范"},
    {"name": "西南科技大学", "province": "四川", "city": "绵阳", "type": "理工"},
    {"name": "成都中医药大学", "province": "四川", "city": "成都", "type": "医药"},
    {"name": "西南医科大学", "province": "四川", "city": "泸州", "type": "医药"},
    # 云南
    {"name": "云南大学", "province": "云南", "city": "昆明", "type": "综合"},
    {"name": "昆明理工大学", "province": "云南", "city": "昆明", "type": "理工"},
    {"name": "云南师范大学", "province": "云南", "city": "昆明", "type": "师范"},
    {"name": "云南财经大学", "province": "云南", "city": "昆明", "type": "财经"},
    {"name": "云南农业大学", "province": "云南", "city": "昆明", "type": "农林"},
    {"name": "云南民族大学", "province": "云南", "city": "昆明", "type": "民族"},
    {"name": "昆明医科大学", "province": "云南", "city": "昆明", "type": "医药"},
    # 贵州
    {"name": "贵州大学", "province": "贵州", "city": "贵阳", "type": "综合"},
    {"name": "贵州师范大学", "province": "贵州", "city": "贵阳", "type": "师范"},
    {"name": "贵州财经大学", "province": "贵州", "city": "贵阳", "type": "财经"},
    {"name": "贵州医科大学", "province": "贵州", "city": "贵阳", "type": "医药"},
    {"name": "遵义医科大学", "province": "贵州", "city": "遵义", "type": "医药"},
    {"name": "贵州民族大学", "province": "贵州", "city": "贵阳", "type": "民族"},
]
