import requests
import time
from datetime import date, timedelta
from typing import List, Dict

def get_filtered_tencent_jobs() -> List[Dict]:
    """
    【终极优化版】腾讯岗位筛选
    执行顺序：拉取列表 → 双重前置筛选(运营+今日/昨日更新) → 获取岗位详情 → 关键词筛选 → 返回结果
    最终结果：仅保留【运营岗】+【近2天更新】+【无硕士/工作年限要求】的岗位
    """
    # ===================== 配置区 =====================
    # 固定数据源接口+参数
    API_URL = "https://careers.tencent.com/tencentcareer/api/post/Query"
    REQUEST_PARAMS = {
        "timestamp": str(int(time.time() * 1000)),
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

    # 筛选规则
    TARGET_JOB_TITLE = "运营"          # 仅保留岗位名含此关键词
    # 岗位要求包含以下关键词则删除
    FILTER_KEYWORDS = [
        '硕士', '三年', '3年', '四年', '4年', '五年', '5年',
        '六年', '6年', '七年', '7年', '八年', '8年',
        '九年', '9年', '十年', '10年'
    ]

    # 请求头
    REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://careers.tencent.com/",
        "Accept": "application/json, text/plain, */*"
    }

    # ===================== 工具函数：生成今日/昨日日期（匹配接口格式） =====================
    def _get_valid_dates() -> list:
        """
        生成今日、昨日的日期字符串，格式：2026年03月28日
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        # 格式化接口同款日期格式
        today_str = today.strftime("%Y年%m月%d日")
        yesterday_str = yesterday.strftime("%Y年%m月%d日")
        return [today_str, yesterday_str]

    # ===================== 步骤1：拉取原始岗位列表 =====================
    def _get_job_list() -> List[Dict]:
        try:
            resp = requests.get(API_URL, params=REQUEST_PARAMS, headers=REQUEST_HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("Code") == 200 and "Posts" in data.get("Data", {}):
                return data["Data"]["Posts"]
            return []
        except Exception as e:
            print(f"获取岗位列表失败：{str(e)}")
            return []

    # ===================== 步骤2：【核心前置筛选】双重条件：运营岗 + 近2天更新 =====================
    def _filter_operation_and_recent_jobs(raw_jobs: List[Dict]) -> List[Dict]:
        """
        提前筛选：仅保留 岗位名含运营 + 更新时间是今日/昨日 的岗位
        执行在获取详情前，极大提升效率
        """
        valid_dates = _get_valid_dates()
        filtered_jobs = []
        for job in raw_jobs:
            job_name = job.get("RecruitPostName", "").strip()
            update_time = job.get("LastUpdateTime", "").strip()
            
            # 双重条件：包含运营 + 日期是今天/昨天
            if TARGET_JOB_TITLE in job_name and update_time in valid_dates:
                filtered_jobs.append(job)
        return filtered_jobs

    # ===================== 步骤3：获取岗位详情（要求） =====================
    def _get_job_requirement(post_id: str) -> str:
        detail_url = "https://careers.tencent.com/tencentcareer/api/post/ByPostId"
        params = {"timestamp": str(int(time.time() * 1000)), "postId": post_id, "language": "zh-cn"}
        try:
            time.sleep(0.5)
            resp = requests.get(detail_url, params=params, headers=REQUEST_HEADERS, timeout=10)
            data = resp.json()
            requirement = data.get("Data", {}).get("Requirement", "")
            return requirement.replace("\r\n", " ").replace("\n", " ")
        except Exception as e:
            print(f"岗位{post_id}详情获取失败：{str(e)}")
            return ""

    # ===================== 主执行流程 =====================
    # 1. 获取原始岗位
    raw_jobs = _get_job_list()
    if not raw_jobs:
        print("未获取到任何岗位数据")
        return []
    print(f"✅ 拉取原始岗位总数：{len(raw_jobs)}")

    # 2. 【关键】前置双重筛选：运营 + 近2天更新
    valid_jobs = _filter_operation_and_recent_jobs(raw_jobs)
    valid_dates = _get_valid_dates()
    if not valid_jobs:
        print(f"❌ 未筛选到【运营】+【{valid_dates[1]} / {valid_dates[0]}】更新的岗位，程序终止")
        return []
    print(f"✅ 前置筛选后保留：{len(valid_jobs)} 个岗位（仅对这些岗位请求详情）")

    # 3. 获取岗位详情
    full_job_list = []
    total = len(valid_jobs)
    print(f"\n开始处理岗位详情...")
    for idx, job in enumerate(valid_jobs):
        job_info = {
            "岗位名": job.get("RecruitPostName", ""),
            "岗位类型": job.get("CategoryName", ""),
            "岗位职责": job.get("Responsibility", "").replace("\r\n", " ").replace("\n", " "),
            "岗位要求": _get_job_requirement(job.get("PostId", "")),
            "工作地点": job.get("LocationName", ""),
            "详情链接": job.get("PostURL", ""),
            "更新时间": job.get("LastUpdateTime", "")
        }
        full_job_list.append(job_info)
        print(f"已处理：{idx+1}/{total} | {job_info['岗位名']}")

    # 4. 二次筛选：排除硕士/工作年限关键词
    final_jobs = []
    for job in full_job_list:
        requirement_text = job["岗位要求"]
        if not any(keyword in requirement_text for keyword in FILTER_KEYWORDS):
            final_jobs.append(job)

    # ===================== 最终统计 =====================
    print(f"\n🎉 全部处理完成！")
    print(f"原始岗位：{len(raw_jobs)}")
    print(f"前置筛选(运营+近2天)：{len(valid_jobs)}")
    print(f"最终保留(无学历年限要求)：{len(final_jobs)}")

    return final_jobs

# ------------------- 调用示例 -------------------
if __name__ == "__main__":
    result_jobs = get_filtered_tencent_jobs()
    if result_jobs:
        print("\n📊 最终符合条件的岗位数据示例：")
        print(result_jobs[0])