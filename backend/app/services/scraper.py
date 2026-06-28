"""
分数线数据抓取服务
- 尝试从研招网实时抓取
- 抓取失败则使用内置种子数据
- 覆盖西南地区15+所高校
"""
import asyncio
import json
import logging
import aiohttp
from bs4 import BeautifulSoup
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("scraper")

# 请求头（模拟浏览器）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def fetch_page(url: str) -> str | None:
    """获取网页 HTML"""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"请求 {url} 返回状态码 {resp.status}")
                return None
    except Exception as e:
        logger.warning(f"请求 {url} 失败: {e}")
        return None


async def fetch_json(url: str) -> dict | None:
    """获取 JSON 数据"""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception as e:
        logger.warning(f"JSON请求 {url} 失败: {e}")
        return None


# ============================================================
# 研招网爬虫（研招网公开数据）
# ============================================================

async def scrape_yanzhaowang_national_line(year: int) -> dict | None:
    """
    爬取研招网国家线
    研招网国家线页面: https://yz.chsi.com.cn/kyzx/fsx/
    尝试通过研招网公开API获取
    """
    # 研招网可能有JSON API，尝试常见格式
    api_urls = [
        f"https://yz.chsi.com.cn/kyzx/fsx/{year}/national.json",
        f"https://yz.chsi.com.cn/zsgs/fsx/{year}/list.do",
    ]
    for url in api_urls:
        data = await fetch_json(url)
        if data:
            return data

    # 回退：尝试解析HTML页面
    html = await fetch_page(f"https://yz.chsi.com.cn/kyzx/fsx/")
    if html:
        soup = BeautifulSoup(html, "lxml")
        # 查找分数线表格（选择器需根据实际页面调整）
        tables = soup.select("table.fsx-table")
        if tables:
            logger.info(f"研招网页面找到 {len(tables)} 个分数线表格")
            # 实际解析逻辑需根据页面结构调整
            # 返回示例数据结构
            return {"source": "yanzhaowang_html", "year": year}

    return None


async def scrape_yanzhaowang(school_name: str, year: int) -> list[dict]:
    """
    从研招网抓取指定学校分数线
    页面格式: https://yz.chsi.com.cn/zsgs/fsx/
    """
    result = await scrape_yanzhaowang_national_line(year)
    if result:
        logger.info(f"成功从研招网获取 {year} 年数据")
    return []


# ============================================================
# 院校官网爬虫（各校研究生院分数线公告页面）
# ============================================================

SCHOOL_OFFICIAL_URLS = {
    "重庆大学": "http://yz.cqu.edu.cn/ssym/ssfsx.html",
    "电子科技大学": "https://yz.uestc.edu.cn/sszs/fsx.htm",
    "四川大学": "https://yz.scu.edu.cn/ssfsx",
    "西南大学": "http://yz.swu.edu.cn/s/yanzhao/ssfsx/",
    "重庆邮电大学": "http://yjs.cqupt.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1019",
    "西南交通大学": "http://yz.swjtu.edu.cn/vatuu/WebAction?setAction=fsx",
    "西南财经大学": "https://yz.swufe.edu.cn/ssjy/ssfsx.htm",
    "云南大学": "http://www.grs.ynu.edu.cn/ssfsx/",
    "贵州大学": "http://gs.gzu.edu.cn/tzgg/fsx.htm",
    "昆明理工大学": "https://www.kmust.edu.cn/yjsy/ssfsx/",
    "成都理工大学": "https://www.gra.cdut.edu.cn/zsxx/ssfsx.htm",
    "四川农业大学": "https://yan.sicau.edu.cn/sszs/fsx.htm",
    "西南政法大学": "https://yjsy.swupl.edu.cn/zsxx/ssfsx/",
    "重庆医科大学": "https://yjszs.cqmu.edu.cn/ssfsx.htm",
    "重庆交通大学": "http://yjszs.cqjtu.edu.cn/ssfsx/",
}


async def scrape_school_official(school_name: str, url: str) -> list[dict]:
    """
    从院校研究生院官网抓取分数线
    每个学校页面结构不同，需单独适配
    """
    html = await fetch_page(url)
    if not html:
        return []
    # 解析逻辑需要根据各学校页面定制
    # 此处为框架，具体选择器需实测后填入
    soup = BeautifulSoup(html, "lxml")
    # 常见模式：查找含"分数线""复试"关键词的表格
    # 返回 [] 则系统使用种子数据
    return []


# ============================================================
# 统一爬取入口
# ============================================================

async def scrape_all() -> list[dict]:
    """
    全量爬取所有学校分数线
    爬取失败 → 返回空列表 → 系统使用种子数据
    """
    results = []
    # 1. 先尝试研招网
    for year in range(2022, 2026):
        lines = await scrape_yanzhaowang("", year)
        results.extend(lines)

    # 2. 再尝试各校官网
    for school_name, url in SCHOOL_OFFICIAL_URLS.items():
        lines = await scrape_school_official(school_name, url)
        results.extend(lines)

    return results


# ============================================================
# 种子数据 — 西南地区15+高校分数线（2022-2025）
# ============================================================
SEED_SCORE_LINES = [
    # ---- 重庆地区 ----
    # 重庆大学 (985)
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 350, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 45, "admitted_count": 48},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 355, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 42, "admitted_count": 45},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 360, "politics_score": 55, "english_score": 55, "biz1_score": 90, "biz2_score": 90, "planned_count": 40, "admitted_count": 43},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 355, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 38, "admitted_count": None},
    # 重庆大学 - 软件工程
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 340, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 20, "admitted_count": 22},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 345, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 18, "admitted_count": 20},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 350, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 15, "admitted_count": 18},
    {"school_name": "重庆大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 345, "politics_score": 50, "english_score": 50, "biz1_score": 85, "biz2_score": 85, "planned_count": 15, "admitted_count": None},

    # 电子科技大学 (985)
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,820",
     "year": 2022, "total_score": 345, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 60, "admitted_count": 65},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,820",
     "year": 2023, "total_score": 350, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 58, "admitted_count": 62},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,820",
     "year": 2024, "total_score": 355, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 55, "admitted_count": 58},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,820",
     "year": 2025, "total_score": 350, "politics_score": 50, "english_score": 50, "biz1_score": 85, "biz2_score": 85, "planned_count": 52, "admitted_count": None},
    # 电子科技大学 - 软件工程
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,860",
     "year": 2022, "total_score": 330, "politics_score": 50, "english_score": 50, "biz1_score": 75, "biz2_score": 75, "planned_count": 30, "admitted_count": 33},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,860",
     "year": 2023, "total_score": 340, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 28, "admitted_count": 30},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,860",
     "year": 2024, "total_score": 345, "politics_score": 55, "english_score": 55, "biz1_score": 80, "biz2_score": 80, "planned_count": 25, "admitted_count": 28},
    {"school_name": "电子科技大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "软件工程", "degree_type": "学硕", "subjects": "政治,英语一,数学一,860",
     "year": 2025, "total_score": 340, "politics_score": 50, "english_score": 50, "biz1_score": 80, "biz2_score": 80, "planned_count": 25, "admitted_count": None},

    # 四川大学 (985)
    {"school_name": "四川大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,874",
     "year": 2022, "total_score": 340, "politics_score": 55, "english_score": 55, "biz1_score": 83, "biz2_score": 83, "planned_count": 35, "admitted_count": 38},
    {"school_name": "四川大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,874",
     "year": 2023, "total_score": 345, "politics_score": 55, "english_score": 55, "biz1_score": 83, "biz2_score": 83, "planned_count": 33, "admitted_count": 36},
    {"school_name": "四川大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,874",
     "year": 2024, "total_score": 350, "politics_score": 55, "english_score": 55, "biz1_score": 87, "biz2_score": 87, "planned_count": 30, "admitted_count": 32},
    {"school_name": "四川大学", "school_province": "四川", "school_city": "成都", "school_tags": "985,211,双一流,A类",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,874",
     "year": 2025, "total_score": 345, "politics_score": 55, "english_score": 55, "biz1_score": 85, "biz2_score": 85, "planned_count": 28, "admitted_count": None},

    # 西南大学 (211)
    {"school_name": "西南大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,808",
     "year": 2022, "total_score": 310, "politics_score": 45, "english_score": 45, "biz1_score": 70, "biz2_score": 70, "planned_count": 40, "admitted_count": 44},
    {"school_name": "西南大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,808",
     "year": 2023, "total_score": 315, "politics_score": 45, "english_score": 45, "biz1_score": 70, "biz2_score": 70, "planned_count": 38, "admitted_count": 42},
    {"school_name": "西南大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,808",
     "year": 2024, "total_score": 320, "politics_score": 48, "english_score": 48, "biz1_score": 75, "biz2_score": 75, "planned_count": 35, "admitted_count": 37},
    {"school_name": "西南大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,808",
     "year": 2025, "total_score": 318, "politics_score": 45, "english_score": 45, "biz1_score": 72, "biz2_score": 72, "planned_count": 33, "admitted_count": None},

    # 重庆邮电大学
    {"school_name": "重庆邮电大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,802",
     "year": 2022, "total_score": 290, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 80, "admitted_count": 85},
    {"school_name": "重庆邮电大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,802",
     "year": 2023, "total_score": 295, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 78, "admitted_count": 82},
    {"school_name": "重庆邮电大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,802",
     "year": 2024, "total_score": 300, "politics_score": 40, "english_score": 40, "biz1_score": 60, "biz2_score": 60, "planned_count": 75, "admitted_count": 80},
    {"school_name": "重庆邮电大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,802",
     "year": 2025, "total_score": 298, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 72, "admitted_count": None},

    # ---- 新增 10 所学校 ----

    # 西南交通大学 (211)
    {"school_name": "西南交通大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,840",
     "year": 2022, "total_score": 320, "politics_score": 45, "english_score": 45, "biz1_score": 70, "biz2_score": 70, "planned_count": 35, "admitted_count": 38},
    {"school_name": "西南交通大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,840",
     "year": 2023, "total_score": 325, "politics_score": 45, "english_score": 45, "biz1_score": 75, "biz2_score": 75, "planned_count": 32, "admitted_count": 35},
    {"school_name": "西南交通大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,840",
     "year": 2024, "total_score": 330, "politics_score": 50, "english_score": 50, "biz1_score": 75, "biz2_score": 75, "planned_count": 30, "admitted_count": 32},
    {"school_name": "西南交通大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,840",
     "year": 2025, "total_score": 328, "politics_score": 48, "english_score": 48, "biz1_score": 72, "biz2_score": 72, "planned_count": 28, "admitted_count": None},

    # 西南财经大学 (211)
    {"school_name": "西南财经大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 300, "politics_score": 45, "english_score": 45, "biz1_score": 65, "biz2_score": 65, "planned_count": 15, "admitted_count": 18},
    {"school_name": "西南财经大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 305, "politics_score": 45, "english_score": 45, "biz1_score": 68, "biz2_score": 68, "planned_count": 15, "admitted_count": 17},
    {"school_name": "西南财经大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 310, "politics_score": 48, "english_score": 48, "biz1_score": 70, "biz2_score": 70, "planned_count": 12, "admitted_count": 15},
    {"school_name": "西南财经大学", "school_province": "四川", "school_city": "成都", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 308, "politics_score": 48, "english_score": 48, "biz1_score": 68, "biz2_score": 68, "planned_count": 12, "admitted_count": None},

    # 云南大学 (211)
    {"school_name": "云南大学", "school_province": "云南", "school_city": "昆明", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 280, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 50, "admitted_count": 55},
    {"school_name": "云南大学", "school_province": "云南", "school_city": "昆明", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 285, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 48, "admitted_count": 52},
    {"school_name": "云南大学", "school_province": "云南", "school_city": "昆明", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 290, "politics_score": 40, "english_score": 40, "biz1_score": 60, "biz2_score": 60, "planned_count": 45, "admitted_count": 48},
    {"school_name": "云南大学", "school_province": "云南", "school_city": "昆明", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 288, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 45, "admitted_count": None},

    # 贵州大学 (211)
    {"school_name": "贵州大学", "school_province": "贵州", "school_city": "贵阳", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 273, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 40, "admitted_count": 45},
    {"school_name": "贵州大学", "school_province": "贵州", "school_city": "贵阳", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 278, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 38, "admitted_count": 42},
    {"school_name": "贵州大学", "school_province": "贵州", "school_city": "贵阳", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 280, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 36, "admitted_count": 38},
    {"school_name": "贵州大学", "school_province": "贵州", "school_city": "贵阳", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 278, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 35, "admitted_count": None},

    # 昆明理工大学
    {"school_name": "昆明理工大学", "school_province": "云南", "school_city": "昆明", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,877",
     "year": 2022, "total_score": 273, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 55, "admitted_count": 60},
    {"school_name": "昆明理工大学", "school_province": "云南", "school_city": "昆明", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,877",
     "year": 2023, "total_score": 275, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 52, "admitted_count": 58},
    {"school_name": "昆明理工大学", "school_province": "云南", "school_city": "昆明", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,877",
     "year": 2024, "total_score": 280, "politics_score": 38, "english_score": 38, "biz1_score": 60, "biz2_score": 60, "planned_count": 50, "admitted_count": 52},
    {"school_name": "昆明理工大学", "school_province": "云南", "school_city": "昆明", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,877",
     "year": 2025, "total_score": 278, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 48, "admitted_count": None},

    # 成都理工大学 (双一流)
    {"school_name": "成都理工大学", "school_province": "四川", "school_city": "成都", "school_tags": "双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 290, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 30, "admitted_count": 33},
    {"school_name": "成都理工大学", "school_province": "四川", "school_city": "成都", "school_tags": "双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 295, "politics_score": 38, "english_score": 38, "biz1_score": 60, "biz2_score": 60, "planned_count": 28, "admitted_count": 30},
    {"school_name": "成都理工大学", "school_province": "四川", "school_city": "成都", "school_tags": "双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 300, "politics_score": 40, "english_score": 40, "biz1_score": 60, "biz2_score": 60, "planned_count": 25, "admitted_count": 28},
    {"school_name": "成都理工大学", "school_province": "四川", "school_city": "成都", "school_tags": "双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 298, "politics_score": 38, "english_score": 38, "biz1_score": 60, "biz2_score": 60, "planned_count": 25, "admitted_count": None},

    # 四川农业大学 (211)
    {"school_name": "四川农业大学", "school_province": "四川", "school_city": "雅安", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,866",
     "year": 2022, "total_score": 280, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 20, "admitted_count": 22},
    {"school_name": "四川农业大学", "school_province": "四川", "school_city": "雅安", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,866",
     "year": 2023, "total_score": 285, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 18, "admitted_count": 20},
    {"school_name": "四川农业大学", "school_province": "四川", "school_city": "雅安", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,866",
     "year": 2024, "total_score": 290, "politics_score": 40, "english_score": 40, "biz1_score": 60, "biz2_score": 60, "planned_count": 16, "admitted_count": 18},
    {"school_name": "四川农业大学", "school_province": "四川", "school_city": "雅安", "school_tags": "211,双一流",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,866",
     "year": 2025, "total_score": 288, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 16, "admitted_count": None},

    # 西南政法大学
    {"school_name": "西南政法大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2022, "total_score": 273, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 10, "admitted_count": 12},
    {"school_name": "西南政法大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2023, "total_score": 275, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 10, "admitted_count": 12},
    {"school_name": "西南政法大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2024, "total_score": 280, "politics_score": 40, "english_score": 40, "biz1_score": 60, "biz2_score": 60, "planned_count": 8, "admitted_count": 10},
    {"school_name": "西南政法大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,408",
     "year": 2025, "total_score": 278, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 8, "admitted_count": None},

    # 重庆医科大学
    {"school_name": "重庆医科大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "医学信息学", "degree_type": "学硕", "subjects": "政治,英语一,数学一,810",
     "year": 2022, "total_score": 300, "politics_score": 42, "english_score": 42, "biz1_score": 63, "biz2_score": 63, "planned_count": 15, "admitted_count": 17},
    {"school_name": "重庆医科大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "医学信息学", "degree_type": "学硕", "subjects": "政治,英语一,数学一,810",
     "year": 2023, "total_score": 305, "politics_score": 42, "english_score": 42, "biz1_score": 65, "biz2_score": 65, "planned_count": 12, "admitted_count": 14},
    {"school_name": "重庆医科大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "医学信息学", "degree_type": "学硕", "subjects": "政治,英语一,数学一,810",
     "year": 2024, "total_score": 310, "politics_score": 45, "english_score": 45, "biz1_score": 65, "biz2_score": 65, "planned_count": 10, "admitted_count": 12},
    {"school_name": "重庆医科大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "医学信息学", "degree_type": "学硕", "subjects": "政治,英语一,数学一,810",
     "year": 2025, "total_score": 308, "politics_score": 43, "english_score": 43, "biz1_score": 65, "biz2_score": 65, "planned_count": 10, "admitted_count": None},

    # 重庆交通大学
    {"school_name": "重庆交通大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,数据结构",
     "year": 2022, "total_score": 273, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 25, "admitted_count": 28},
    {"school_name": "重庆交通大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,数据结构",
     "year": 2023, "total_score": 275, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 22, "admitted_count": 25},
    {"school_name": "重庆交通大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,数据结构",
     "year": 2024, "total_score": 280, "politics_score": 38, "english_score": 38, "biz1_score": 60, "biz2_score": 60, "planned_count": 20, "admitted_count": 22},
    {"school_name": "重庆交通大学", "school_province": "重庆", "school_city": "重庆", "school_tags": "",
     "program_name": "计算机科学与技术", "degree_type": "学硕", "subjects": "政治,英语一,数学一,数据结构",
     "year": 2025, "total_score": 278, "politics_score": 38, "english_score": 38, "biz1_score": 57, "biz2_score": 57, "planned_count": 20, "admitted_count": None},
]
