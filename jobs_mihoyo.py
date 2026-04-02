# jobs_mihoyo.py
import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta

# 米哈游招聘筛选函数（单缓存 + 日期标签 + 当日多次请求）
async def get_filtered_mihoyo_jobs():
    # 接口配置
    LIST_API = "https://ats.openout.mihoyo.com/ats-portal/v1/job/list"
    DETAIL_API = "https://ats.openout.mihoyo.com/ats-portal/v1/job/info"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://jobs.mihoyo.com/",
        "Origin": "https://jobs.mihoyo.com",
        "Content-Type": "application/json;charset=UTF-8"
    }

    LIST_PARAMS = {
        "jobName": "",
        "competencyTypes": [5, 6, 8], # 运营类、市场&商务类、国际化类
        "channelDetailIds": [1, 2],
        "hireType": 0,
        "pageNo": 1,
        "pageSize": 1000
    }

    # 筛选规则
    EXCLUDE_KEYWORDS = ['硕士', '四年', '4年', '五年', '5年', '六年', '6年','七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']

    # 核心：单个缓存文件 + 岗位ID绑定日期
    # ===================== 固定缓存文件绝对路径 =====================
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CACHE_FILE = os.path.join(SCRIPT_DIR, "mihoyo_job_cache.json")
    TODAY = datetime.now().strftime("%Y-%m-%d")
    YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    RECENT_DAYS = [YESTERDAY, TODAY]  # 查询近两天

    # ===================== 缓存操作（存储：{岗位ID: 提取日期}） =====================
    def load_cache() -> dict:
        """加载缓存：返回 {job_id: date}"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache(cache_data: dict):
        """保存缓存"""
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    # ============================================================================

    # 获取岗位列表
    async def fetch_job_list():
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(LIST_API, json=LIST_PARAMS, headers=HEADERS, timeout=15)
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("data", {}).get("list", [])
        except:
            pass
        return []

    # 获取岗位详情
    async def fetch_job_detail(job_id):
        try:
            payload = {"id": job_id, "channelDetailIds": [1, 2]}
            async with httpx.AsyncClient() as client:
                resp = await client.post(DETAIL_API, json=payload, headers=HEADERS, timeout=10)
                data = resp.json()
                return data.get("data", {}) if data.get("code") == 0 else {}
        except:
            return {}

    # ===================== 主逻辑 =====================
    # 1. 获取线上符合基础条件的岗位（急聘 + 全职）
    raw_jobs = await fetch_job_list()
    online_valid_jobs = {}  # {job_id: job_info}
    for job in raw_jobs:
        if job.get("hurry") is True and job.get("jobNature") == "全职":
            online_valid_jobs[job["id"]] = job

    if not online_valid_jobs:
        return []

    # 2. 加载缓存，筛选出【近两天】的岗位
    cache = load_cache()
    recent_cached_ids = [jid for jid, date in cache.items() if date in RECENT_DAYS]

    # 3. 今日新增 = 线上有效岗位 - 历史缓存岗位（非今日）
    new_ids = [jid for jid in online_valid_jobs.keys() if jid not in cache]

    # 4. 最终返回：近两天所有岗位（缓存历史 + 最新新增）
    recent_all_ids = list(set(recent_cached_ids + new_ids))
    recent_all_jobs = [online_valid_jobs[jid] for jid in recent_all_ids if jid in online_valid_jobs]

    # 5. 深度筛选 + 构造结果
    final_jobs = []
    for job in recent_all_jobs:
        job_id = job["id"]
        detail = await fetch_job_detail(job_id)
        await asyncio.sleep(0.2)

        desc = detail.get("description", "").replace("\n", " ").strip()
        require = detail.get("jobRequire", "").replace("\n", " ").strip()
        full_text = f"{desc} {require}"

        # 排除关键词
        if not any(k in full_text for k in EXCLUDE_KEYWORDS):
            final_jobs.append({
                "公司": "米哈游",
                "岗位名": detail.get("title", job.get("title", "")),
                "工作地点": detail.get("addressDetailList", [{}])[0].get("addressDetail", ""),
                "详情链接": f"https://jobs.mihoyo.com/#/position/{job_id}",
                "更新时间": TODAY,  # 新增岗位打今日标签
                "岗位要求": full_text
            })

    # 6. 更新缓存：给今日新增岗位打上日期标签
    for jid in new_ids:
        cache[jid] = TODAY
    save_cache(cache)

    return final_jobs


# 测试入口
# if __name__ == "__main__":
#     async def test():
#         print("正在获取米哈游【近两天】新增岗位...")
#         jobs = await get_filtered_mihoyo_jobs()
#         print(f"\n【近两天】新增符合条件岗位：{len(jobs)} 个")
#         for job in jobs:
#             print("-" * 80)
#             print(job)

#     asyncio.run(test())