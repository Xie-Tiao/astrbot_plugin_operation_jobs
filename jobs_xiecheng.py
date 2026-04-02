# jobs_xiecheng.py
import asyncio
import httpx
import re
from datetime import date, timedelta

# 【纯异步封装函数】携程岗位筛选
async def get_filtered_ctrip_jobs():
    API_URL = "https://job.ctrip.com/api/hrrecruit/getJobAd"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://job.ctrip.com/",
        "Content-Type": "application/json",
        "Origin": "https://job.ctrip.com"
    }

    # -------------------------- 工具函数 --------------------------
    # 获取今日、昨日日期（携程格式：2026-04-02）
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")]

    # 清洗HTML标签 + 提取任职资格
    def parse_qualification(requirements_html):
        if not requirements_html:
            return ""
        text = re.sub(r'<[^>]+>', '', requirements_html)
        text = re.sub(r'\s+', ' ', text).strip()
        if "任职资格" in text:
            return text.split("任职资格", 1)[1].strip()
        elif "Qualifications" in text or "Requirements" in text:
            return text.split("Qualifications", 1)[-1].split("Requirements", 1)[-1].strip()
        return text

    # -------------------------- 异步请求函数 --------------------------
    async def fetch_job_list():
        try:
            PAYLOAD = {
                "condition": {
                    "fromId": [],
                    "keyword": "",
                    "kind": [],
                    "country": [],
                    "city": ["CO0009", "CO0010"], 
                    "bucode": [],
                    "jobFamilyCode": [],
                    "jobFamilyGroupCode": ["JFG_51", "Categroy_4"],
                    "category": 1
                },
                "pager": {
                    "index": "1",
                    "size": "200"
                },
                "head": {
                    "language": "zh_CN",
                    "version": "1"
                }
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    API_URL,
                    json=PAYLOAD,
                    headers=HEADERS,
                    timeout=15
                )
                data = resp.json()
                if data.get("retCode") == "201":
                    return data["retValue"].get("recruitJobAdList", [])
        except Exception:
            pass
        return []

    # -------------------------- 主筛选流程 --------------------------
    valid_dates = get_valid_dates()
    raw_jobs = await fetch_job_list()

    # 第一层筛选：仅保留【近2天发布】
    filtered = []
    for job in raw_jobs:
        publish_date = job.get("publishDate", "")
        if publish_date in valid_dates:
            filtered.append(job)

    # 组装完整岗位信息
    full_jobs = []
    for job in filtered:
        from_id = job.get("fromId", "")
        detail_url = f"https://job.ctrip.com/#/experienced/job-detail/{from_id}"
        requirement = parse_qualification(job.get("requirements", ""))
        
        full_jobs.append({
            "公司": "携程",
            "岗位名": job.get("jobTitle", ""),
            "工作地点": job.get("cityName", ""),
            "详情链接": detail_url,
            "更新时间": job.get("publishDate", ""),
            "岗位要求": requirement
        })

    # 第二层筛选：排除硕士、4年及以上工作年限
    exclude_keywords = ['硕士', '四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    final_jobs = [j for j in full_jobs if not any(k in j["岗位要求"] for k in exclude_keywords)]

    return final_jobs


# -------------------------- 测试运行 --------------------------
# if __name__ == "__main__":
#     async def test():
#         jobs = await get_filtered_ctrip_jobs()
#         print(f"✅ 筛选完成，共获取 {len(jobs)} 个符合条件的携程岗位")
#         for job in jobs:
#             print("-" * 80)
#             for k, v in job.items():
#                 print(f"{k}：{v}")

#     asyncio.run(test())