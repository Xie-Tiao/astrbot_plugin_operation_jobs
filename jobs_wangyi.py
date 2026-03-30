import httpx
from datetime import datetime, timedelta

# 【核心】纯异步函数，严格对齐 jobs_tencent.py 风格
async def get_filtered_wangyi_jobs():
    API_URL = "https://hr.163.com/api/hr163/position/queryPage"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://hr.163.com/job-list.html",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://hr.163.com"
    }
    POST_DATA = {
        "currentPage": 1,
        "pageSize": 200,
        "postType": "08",
        "workType": "0",
        "cityIdList": [229, 2, 138],
        "lang": "zh"
    }

    # 计算近2天的时间阈值
    def get_valid_dates():
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        return [
            today.strftime("%Y-%m-%d"),
            yesterday.strftime("%Y-%m-%d")
        ]

    # 异步获取岗位全量列表
    async def fetch_job_list():
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    API_URL,
                    json=POST_DATA,
                    headers=HEADERS,
                    timeout=15
                )
                data = resp.json()
                if data.get("code") == 200:
                    return data.get("data", {}).get("list", [])
        except:
            pass
        return []

    # 主流程执行
    valid_dates = get_valid_dates()
    raw_jobs = await fetch_job_list()

    # 第一层筛选：近2天更新
    filtered = []
    for job in raw_jobs:
        update_time_stamp = job.get("updateTime", 0)
        if not update_time_stamp:
            continue
        update_time = datetime.fromtimestamp(update_time_stamp / 1000)
        update_date_str = update_time.strftime("%Y-%m-%d")
        if update_date_str in valid_dates:
            filtered.append(job)

    # 第二层筛选：排除硕士/年限
    keywords = ['硕士', '3年', '4年', '5年', '6年', '7年', '8年', '9年', '10年']
    final = []
    for job in filtered:
        job_id = job.get("id", "")
        requirement = job.get("requirement", "").replace("\r\n", " ").replace("\n", " ")
        if not any(k in requirement for k in keywords):
            final.append({
                "公司": "网易",
                "岗位名": job.get("name", ""),
                "工作地点": ",".join(job.get("workPlaceNameList", [])),
                "详情链接": f"https://hr.163.com/job-detail.html?id={job_id}&lang=zh" if job_id else "",
                "更新时间": datetime.fromtimestamp(job.get("updateTime", 0) / 1000).strftime("%Y年%m月%d日"),
                "岗位要求": requirement
            })

    return final