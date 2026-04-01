# jobs_bili.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import date, timedelta, datetime
import time

def get_filtered_bili_jobs():
    # ===================== 核心配置 =====================
    BASE_URL = "https://jobs.bilibili.com/social/positions?code=03&type=3&page=1"
    EXCLUDE_KEYWORDS = ['硕士','四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    
    # ===================== 浏览器配置 =====================
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") # 强制使用磁盘(/tmp)代替物理内存(/dev/shm)
    options.add_argument('--blink-settings=imagesEnabled=false') # 不加载图片，极其省内存
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    ) # type: ignore
    driver.set_page_load_timeout(60)

    # ===================== 工具函数 =====================
    def is_recent_two_days(date_str):
        """判断日期字符串是否在近两天内"""
        try:
            # 解析 "2026-03-23" 格式
            job_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            two_days_ago = date.today() - timedelta(days=2)
            return job_date >= two_days_ago
        except:
            return False

    # ===================== 核心流程 =====================
    driver.get(BASE_URL)
    time.sleep(3)
    
    # 获取所有岗位卡片
    job_cards = driver.find_elements(By.CLASS_NAME, "bili-item-card")
    print(f"📄 共找到 {len(job_cards)} 个岗位")

    raw_jobs = []
    main_handle = driver.current_window_handle

    # 1. 遍历卡片，逐个点击获取详情页URL和基础信息
    for idx, card in enumerate(job_cards):
        try:
            # --- 提取列表页基础信息 ---
            job_name = card.find_element(By.CLASS_NAME, "item-title").text.strip()
            
            # 提取日期：使用属性选择器定位特定的span
            # 格式: <span data-v-6f10636a="">2026-03-23 发布</span>
            date_text = ""
            try:
                # 尝试通过包含 "发布" 文本的 span 来定位
                date_elem = card.find_element(By.XPATH, ".//span[contains(text(), '发布')]")
                raw_date_str = date_elem.text.strip()
                # 提取 "2026-03-23" 部分
                date_text = raw_date_str.replace("发布", "").strip()
            except:
                pass

            # 先进行时间筛选，如果不是近两天的直接跳过，节省时间
            if date_text and not is_recent_two_days(date_text):
                print(f"⏭️  [{idx+1}/{len(job_cards)}] 跳过 {job_name} (日期: {date_text})")
                continue

            # --- 点击进入详情页获取URL ---
            print(f"🔍  [{idx+1}/{len(job_cards)}] 处理中: {job_name}")
            
            # 点击卡片（使用JS点击防止被遮挡）
            driver.execute_script("arguments[0].click();", card)
            time.sleep(2)

            # 切换到新标签页
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                detail_url = driver.current_url
                
                # 提取其他基础信息（地点、类别等）
                # 这里我们选择在详情页提取，信息更全
                location = "未知"
                category = "未知"
                job_type = "未知"
                
                try:
                    # 详情页顶部通常也有这些信息，或者我们可以信任之前的列表页
                    # 为了简单，这里主要是获取URL，其他信息如果需要可以在详情页重新解析
                    pass
                except:
                    pass

                raw_jobs.append({
                    "岗位名": job_name,
                    "发布时间": date_text,
                    "详情链接": detail_url
                })

                # 关闭详情页，切回列表
                driver.close()
                driver.switch_to.window(main_handle)
            else:
                driver.back()
                time.sleep(2)
                driver.switch_to.window(main_handle)

        except Exception as e:
            print(f"⚠️  处理第 {idx+1} 个岗位时出错: {str(e)}")
            # 确保切回主窗口
            if len(driver.window_handles) > 1:
                driver.close()
            driver.switch_to.window(main_handle)
            continue

    # 2. 爬取筛选后岗位的详细要求
    full_jobs = []
    for job in raw_jobs:
        try:
            print(f"📋  爬取详情: {job['岗位名']}")
            driver.get(job["详情链接"])
            time.sleep(2)
            
            # 提取职位描述
            desc_text = ""
            try:
                sub_title = driver.find_element(By.XPATH, "//p[@class='position-sub-title' and text()='职位描述']")
                desc_elem = sub_title.find_element(By.XPATH, "./following-sibling::p[@class='position-desc'][1]")
                desc_text = desc_elem.text.strip()
            except:
                pass
            
            # 拆分职责和要求
            responsibility = ""
            requirement = ""
            if "工作职责:" in desc_text:
                parts = desc_text.split("工作职责:")[1]
                if "工作要求:" in parts:
                    responsibility = parts.split("工作要求:")[0].strip().replace("\n", "；")
                    requirement = parts.split("工作要求:")[1].strip().replace("\n", "；")
                else:
                    responsibility = parts.strip().replace("\n", "；")
            elif "工作要求:" in desc_text:
                requirement = desc_text.split("工作要求:")[1].strip().replace("\n", "；")

            # 补充信息（重新在详情页获取地点等更稳妥）
            location = "未知"
            category = "未知"
            try:
                # 尝试从详情页的标签中获取
                tags = driver.find_elements(By.CLASS_NAME, "position-tag")
                if len(tags) >= 1:
                    location = tags[0].text.strip()
                if len(tags) >= 2:
                    category = tags[1].text.strip()
            except:
                pass

            full_jobs.append({
                "公司": "B站",
                "岗位名": job["岗位名"],
                "工作地点": location,
                "岗位类别": category,
                "详情链接": job["详情链接"],
                "发布时间": job["发布时间"],
                "工作职责": responsibility,
                "岗位要求": requirement
            })

        except Exception as e:
            print(f"⚠️  详情爬取失败 {job['岗位名']}: {str(e)}")
            continue

    # 3. 关键词排除筛选
    final_jobs = [j for j in full_jobs if not any(k in j["岗位要求"] for k in EXCLUDE_KEYWORDS)]

    driver.quit()
    return final_jobs

# 运行
# if __name__ == "__main__":
#     result = get_filtered_bili_jobs()
#     print(f"\n✅ B站筛选完成，符合条件岗位：{len(result)}")
#     print("="*80)
#     for job in result:
#         print(f"\n🔹 {job['岗位名']}")
#         print(f"   公司：{job['公司']}")
#         print(f"   地点：{job['工作地点']}")
#         print(f"   类别：{job['岗位类别']}")
#         print(f"   发布时间：{job['发布时间']}")
#         print(f"   详情链接：{job['详情链接']}")
#         print(f"   工作职责：{job['工作职责']}")
#         print(f"   岗位要求：{job['岗位要求']}")
#         print("-"*80)