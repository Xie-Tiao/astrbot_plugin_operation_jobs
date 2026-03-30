# jobs_tencent.py
import asyncio
import httpx
from datetime import date, timedelta

# 【关键】纯异步函数，可正常 await，无类型报错
async def get_filtered_tencent_jobs():
    API_URL = "https://careers.tencent.com/tencentcareer/api/post/Query"
    PARAMS = {
        "timestamp": str(int(asyncio.get_event_loop().time() * 1000)),
        "countryId": "",
        "cityId": "",
        "bgIds": "",
        "productId": "",
        "categoryId": "",
        "parentCategoryId": "",
        "attrId": 1,
        "keyword": "",
        "pageIndex": 1,
        "pageSize": 200,
        "language": "zh-cn",
        "area": "cn"
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://careers.tencent.com/"
    }

    # 获取今日/昨日日期
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [
            today.strftime("%Y年%m月%d日"),
            yesterday.strftime("%Y年%m月%d日")
        ]

    # 异步获取岗位列表
    async def fetch_job_list():
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(API_URL, params=PARAMS, headers=HEADERS, timeout=10)
                data = resp.json()
                if data.get("Code") == 200:
                    return data["Data"].get("Posts", [])
        except:
            pass
        return []

    # 异步获取岗位要求
    async def fetch_job_requirement(post_id):
        url = "https://careers.tencent.com/tencentcareer/api/post/ByPostId"
        params = {
            "timestamp": str(int(asyncio.get_event_loop().time() * 1000)),
            "postId": post_id,
            "language": "zh-cn"
        }
        try:
            await asyncio.sleep(0.2)
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=HEADERS, timeout=10)
                return resp.json()["Data"].get("Requirement", "").replace("\r\n", " ").replace("\n", " ")
        except:
            return ""

    # 主流程
    valid_dates = get_valid_dates()
    raw_jobs = await fetch_job_list()
    
    # 第一层筛选：运营 + 近2天更新
    filtered = []
    for job in raw_jobs:
        name = job.get("RecruitPostName", "")
        update_time = job.get("LastUpdateTime", "")
        if "运营" in name and update_time in valid_dates:
            filtered.append(job)

    # 组装完整信息
    full_jobs = []
    for job in filtered:
        req = await fetch_job_requirement(job.get("PostId", ""))
        full_jobs.append({
            "公司": "腾讯",
            "岗位名": job.get("RecruitPostName", ""),
            "工作地点": job.get("LocationName", ""),
            "详情链接": job.get("PostURL", ""),
            "更新时间": job.get("LastUpdateTime", ""),
            "岗位要求": req
        })

    # 第二层筛选：排除硕士/年限
    keywords = ['硕士', '三年', '3年','四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    final = [j for j in full_jobs if not any(k in j["岗位要求"] for k in keywords)]
    
    return final