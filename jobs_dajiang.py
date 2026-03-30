from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import date, timedelta
import time

def get_filtered_dji_jobs():
    # ===================== 核心配置 =====================
    # 大疆仅爬第一页
    BASE_URL = "https://we.dji.com/zh-CN/social?from=home_page&category=301_302&location=3100_4403&pageSize=100&page=1"
    # 排除关键词：硕士+工作年限
    EXCLUDE_KEYWORDS = ['硕士','3年','4年','5年','6年','7年','8年','9年','10年','三年','四年','五年']
    
    # ===================== 【你的代码风格】ARM Chromium 配置 =====================
    options = Options()
    # 必选参数（Docker+ARM 必备）
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # 【关键】连接本地 Docker 中的 seleniarm 浏览器（容器间通信地址）
    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    )
    driver.set_page_load_timeout(60)
    all_jobs = []

    # 获取近2天日期
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")]

    # 爬取岗位详情
    def crawl_job_detail(job_item):
        try:
            job_name = job_item.find_element(By.CLASS_NAME, "PositionCard_text__2BdZa").text.strip()
            keyword_text = job_item.find_element(By.CLASS_NAME, "PositionCard_keyword__FFaH5").text.strip()
            keyword_parts = [part.strip() for part in keyword_text.split("|")]
            city = keyword_parts[0]
            update_time = keyword_parts[-1]  # 直接获取日期：2026-03-18
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
                "岗位名": job_name,
                "工作地点": city,
                "详情链接": detail_url,
                "更新时间": update_time,
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
        
        # 获取岗位列表
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
    print(f"\n✅ 筛选完成，符合条件岗位：{len(result)}")
    for job in result:
        print(job)