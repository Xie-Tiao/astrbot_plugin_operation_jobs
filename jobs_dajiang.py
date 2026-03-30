# jobs_dajiang.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import date, timedelta
import time

def get_filtered_dji_jobs():
    # ===================== 核心配置 =====================
    BASE_URL = "https://we.dji.com/zh-CN/social?from=home_page&category=301_302&location=3100_4403&pageSize=100&page=1"
    EXCLUDE_KEYWORDS = ['硕士','3年','4年','5年','6年','7年','8年','9年','10年','三年','四年','五年']
    
    # ===================== 浏览器配置 =====================
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    )
    driver.set_page_load_timeout(60)
    all_jobs = []

    # 获取近2天日期（统一格式：YYYY年MM月DD日）
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [
            today.strftime("%Y年%m月%d日"),
            yesterday.strftime("%Y年%m月%d日")
        ]

    # 日期格式转换：2026-03-30 → 2026年03月30日
    def convert_date(date_str: str) -> str:
        try:
            return date.fromisoformat(date_str).strftime("%Y年%m月%d日")
        except:
            return date_str

    # 爬取岗位详情
    def crawl_job_detail(job_item):
        try:
            job_name = job_item.find_element(By.CLASS_NAME, "PositionCard_text__2BdZa").text.strip()
            keyword_text = job_item.find_element(By.CLASS_NAME, "PositionCard_keyword__FFaH5").text.strip()
            keyword_parts = [part.strip() for part in keyword_text.split("|")]
            city = keyword_parts[0]
            update_time = convert_date(keyword_parts[-1])  # 统一日期格式
            detail_url = job_item.find_element(By.TAG_NAME, "a").get_attribute("href")

            # 打开详情页
            main_handle = driver.current_window_handle
            driver.execute_script("window.open(arguments[0]);", detail_url)
            time.sleep(2)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)

            # 提取任职要求
            requirement = ""
            subtitles = driver.find_elements(By.CLASS_NAME, "detail_subtitle__gOlwP")
            contents = driver.find_elements(By.CLASS_NAME, "detail_phases__PyEga")
            for i, sub in enumerate(subtitles):
                if "任职要求" in sub.text and i < len(contents):
                    requirement = contents[i].text.strip()

            driver.close()
            driver.switch_to.window(main_handle)
            return {
                "公司": "大疆",
                "岗位名": job_name,
                "工作地点": city,
                "详情链接": detail_url,
                "更新时间": update_time, # 统一格式
                "岗位要求": requirement
            }
        except Exception:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            return None

    # ===================== 主爬取逻辑 =====================
    try:
        valid_dates = get_valid_dates()
        driver.get(BASE_URL)
        time.sleep(5)
        
        job_items = driver.find_elements(By.CLASS_NAME, "social_position_card__epffd")
        
        for item in job_items:
            job = crawl_job_detail(item)
            if job:
                all_jobs.append(job)

        # 双重筛选
        recent_jobs = [j for j in all_jobs if j["更新时间"] in valid_dates]
        final_jobs = [j for j in recent_jobs if not any(k in j["岗位要求"] for k in EXCLUDE_KEYWORDS)]
        
        return final_jobs
    finally:
        driver.quit()

# 运行并输出结果
if __name__ == "__main__":
    result = get_filtered_dji_jobs()
    print(f"\n✅ 大疆筛选完成，符合条件岗位：{len(result)}")
    for job in result:
        print(job)