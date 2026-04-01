# jobs_feizhu.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, timedelta, datetime
import time

def get_filtered_feizhu_jobs():
    # ===================== 核心配置 =====================
    TARGET_URL = "https://career.fliggy.com/off-campus/position-list?lang=zh"
    # 筛选条件：排除硕士 + 4年及以上工作经验
    EXCLUDE_KEYWORDS = ['硕士', '四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    
    # ===================== Edge 浏览器配置 =====================
    options = Options()
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage") # 强制使用磁盘(/tmp)代替物理内存(/dev/shm)
    options.add_argument('--blink-settings=imagesEnabled=false') # 不加载图片，极其省内存
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # 初始化驱动
    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    ) # type: ignore
    wait = WebDriverWait(driver, 30)
    driver.set_page_load_timeout(60)
    job_data = []
    stop_flag = False

    # ===================== 工具函数：判断是否近两天发布 =====================
    def is_recent_two_days(date_str):
        """解析岗位更新时间，判断是否在近两天内"""
        try:
            clean_date = date_str.replace("更新于 ", "").strip()
            job_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
            two_days_ago = date.today() - timedelta(days=2)
            return job_date > two_days_ago
        except Exception:
            return False

    # ===================== 1. 自动筛选（运营/游戏运营 + 杭沪深） =====================
    def auto_filter():
        driver.get(TARGET_URL)
        print("页面加载中...")
        time.sleep(6)

        # 展开分类
        print("正在展开 运营类...")
        operate_expand = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[aria-label="运营类"] span.next-tree-switcher')))
        driver.execute_script("arguments[0].click();", operate_expand)
        time.sleep(1)

        print("正在展开 游戏类...")
        game_expand = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[aria-label="游戏类"] span.next-tree-switcher')))
        driver.execute_script("arguments[0].click();", game_expand)
        time.sleep(1)

        # 勾选岗位类型
        print("勾选 内容运营...")
        content_label = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@aria-label="内容运营"]/parent::span/parent::label')))
        driver.execute_script("arguments[0].click();", content_label)
        time.sleep(1)

        print("勾选 游戏运营...")
        game_label = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@aria-label="游戏运营"]/parent::span/parent::label')))
        driver.execute_script("arguments[0].click();", game_label)
        time.sleep(1)

        # 勾选城市
        cities = ["杭州", "上海", "深圳"]
        for city in cities:
            print(f"勾选 {city}...")
            city_label = wait.until(EC.element_to_be_clickable((By.XPATH, f'//input[@aria-label="{city}"]/parent::span/parent::label')))
            driver.execute_script("arguments[0].click();", city_label)
            time.sleep(1)
        
        print("✅ 勾选完成！\n")
        time.sleep(5)

    # ===================== 2. 分页提取岗位 =====================
    def extract_jobs():
        nonlocal stop_flag
        main_handle = driver.current_window_handle
        page_num = 1

        while not stop_flag:
            print(f"\n📄 正在处理第 {page_num} 页岗位...")
            # 等待岗位列表加载
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "_2AOmjKmlEtuR_KEoehWYcN")))
            job_items = driver.find_elements(By.CLASS_NAME, "_2AOmjKmlEtuR_KEoehWYcN")

            # 遍历当前页岗位
            for idx, item in enumerate(job_items, 1):
                try:
                    # 提取岗位名
                    job_name = item.find_element(By.CLASS_NAME, "_3vj2eS7k7Mwpko5_6OSRu2").text.strip()
                    # 提取更新时间 + 城市
                    inner_info_parent = item.find_element(By.CLASS_NAME, "_2qoSPTANtUY2-c4vLhjKv6")
                    update_time = inner_info_parent.find_element(By.CLASS_NAME, "_3Jn5Z6PZA5H7Auzy0xlXu2").text.strip().replace("更新于 ", "")
                    address_parent = inner_info_parent.find_element(By.CLASS_NAME, "_3CJNtKfv5mLnNfeqL1jgRB")
                    city = address_parent.find_element(By.CLASS_NAME, "_3vj2eS7k7Mwpko5_6OSRu2").text.strip()

                    # 时间筛选
                    if not is_recent_two_days(update_time):
                        print(f"🛑 遇到非近两天岗位：{job_name}，终止提取！")
                        stop_flag = True
                        break

                    # 打开岗位详情
                    print(f"✅ 处理岗位 {idx}/{len(job_items)}：{job_name}")
                    driver.execute_script("arguments[0].click();", item)
                    time.sleep(3)
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    # 获取岗位要求
                    detail_url = driver.current_url
                    requirement = "无"
                    content_blocks = driver.find_elements(By.CLASS_NAME, "content-block")
                    if len(content_blocks) >= 3:
                        requirement = content_blocks[2].text.strip().replace("\n", "；")

                    # 关闭标签页
                    driver.close()
                    driver.switch_to.window(main_handle)

                    # 保存数据
                    job_data.append({
                        "公司": "飞猪",
                        "岗位名": job_name,
                        "更新时间": update_time,
                        "工作地点": city,
                        "详情链接": detail_url,
                        "岗位要求": requirement
                    })

                except Exception as e:
                    print(f"⚠️  岗位{idx}处理失败：{str(e)}")
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(main_handle)
                    continue

            if stop_flag:
                break

            # 翻页逻辑
            try:
                next_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.next-pagination-item.next-next")))
                if not next_btn.is_enabled():
                    print("📌 已到达最后一页！")
                    stop_flag = True
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                page_num += 1
                time.sleep(4)
            except Exception as e:
                print("📌 未找到下一页，终止翻页！")
                stop_flag = True
                break

    # ===================== 3. 执行主流程 =====================
    try:
        auto_filter()
        extract_jobs()
        final_jobs = [job for job in job_data if not any(keyword in job["岗位要求"] for keyword in EXCLUDE_KEYWORDS)]
        return final_jobs
    finally:
        driver.quit()
        print("\n🔌 浏览器已安全关闭，资源释放完成")

# ===================== 运行程序 =====================
# if __name__ == "__main__":
#     result = get_filtered_feizhu_jobs()
    
#     print("\n" + "="*60)
#     print(f"🎯 最终筛选完成！符合条件岗位：{len(result)} 个")
#     print("="*60)
    
#     for i, job in enumerate(result[:3], 1):
#         print(f"\n【第{i}个岗位】")
#         print(f"公司：{job['公司']}")
#         print(f"岗位名：{job['岗位名']}")
#         print(f"更新时间：{job['更新时间']}")
#         print(f"工作地点：{job['工作地点']}")
#         print(f"详情链接：{job['详情链接']}")
#         print(f"岗位要求：{job['岗位要求'][:150]}...")
#         print("-"*50)
    
#     print("\n✅ 执行完毕！")