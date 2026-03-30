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
    ) # type: ignore
    driver.set_page_load_timeout(60)

    # 工具函数
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]

    def convert_date(date_str: str) -> str:
        try:
            return date.fromisoformat(date_str).strftime("%Y年%m月%d日")
        except:
            return date_str

    # ===================== 核心流程 =====================
    valid_dates = get_valid_dates()
    
    # 1. 打开列表页，提取【所有岗位基础信息】（不打开详情）
    driver.get(BASE_URL)
    time.sleep(3)
    job_items = driver.find_elements(By.CLASS_NAME, "social_position_card__epffd")
    raw_jobs = []
    for item in job_items:
        try:
            job_name = item.find_element(By.CLASS_NAME, "PositionCard_text__2BdZa").text.strip()
            keyword_text = item.find_element(By.CLASS_NAME, "PositionCard_keyword__FFaH5").text.strip()
            city, _, update_time = [p.strip() for p in keyword_text.split("|")]
            detail_url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
            raw_jobs.append({
                "岗位名": job_name,
                "工作地点": city,
                "更新时间": convert_date(update_time),
                "详情链接": detail_url
            })
        except:
            continue

    # 2. 第一层筛选：仅保留近2天更新
    filtered_jobs = [j for j in raw_jobs if j["更新时间"] in valid_dates]

    # 3. 仅爬筛选后的岗位详情
    full_jobs = []
    main_handle = driver.current_window_handle
    for job in filtered_jobs:
        try:
            # 打开详情页
            driver.execute_script("window.open(arguments[0]);", job["详情链接"])
            time.sleep(2)
            driver.switch_to.window(driver.window_handles[-1])
            
            # 提取任职要求
            requirement = ""
            subtitles = driver.find_elements(By.CLASS_NAME, "detail_subtitle__gOlwP")
            contents = driver.find_elements(By.CLASS_NAME, "detail_phases__PyEga")
            for i, sub in enumerate(subtitles):
                if "任职要求" in sub.text and i < len(contents):
                    requirement = contents[i].text.strip()
                    break
            
            # 组装完整信息
            full_jobs.append({
                "公司": "大疆",
                "岗位名": job["岗位名"],
                "工作地点": job["工作地点"],
                "详情链接": job["详情链接"],
                "更新时间": job["更新时间"],
                "岗位要求": requirement
            })
            
            # 关闭详情页，切回主页面
            driver.close()
            driver.switch_to.window(main_handle)
        except:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(main_handle)
            continue

    # 4. 第二层筛选：排除硕士/年限
    final_jobs = [j for j in full_jobs if not any(k in j["岗位要求"] for k in EXCLUDE_KEYWORDS)]

    driver.quit()
    return final_jobs

# 运行
if __name__ == "__main__":
    result = get_filtered_dji_jobs()
    print(f"✅ 大疆筛选完成，符合条件岗位：{len(result)}")
    for job in result:
        print(job)