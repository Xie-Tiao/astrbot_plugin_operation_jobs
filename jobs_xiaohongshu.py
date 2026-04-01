# jobs_xiaohongshu.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from datetime import date, timedelta
import time

def get_filtered_xhs_jobs():
    # ===================== 核心配置 =====================
    BASE_URL = "https://job.xiaohongshu.com/social/position?positionName=&jobTypes=om&workplaces=3100%2C4403%2C3301&page=1"
    EXCLUDE_KEYWORDS = ['硕士', '四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    
    # ===================== 浏览器配置 =====================
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") # 强制使用磁盘(/tmp)代替物理内存(/dev/shm)
    options.add_argument('--blink-settings=imagesEnabled=false') # 不加载图片，极其省内存
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    ) # type: ignore
    driver.set_page_load_timeout(60)

    # ===================== 工具函数 =====================
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [
            today.strftime("%Y年%m月%d日"),
            yesterday.strftime("%Y年%m月%d日")
        ]

    def convert_date(date_str: str) -> str:
        try:
            return date.fromisoformat(date_str).strftime("%Y年%m月%d日")
        except:
            return date_str

    # ===================== 核心流程 =====================
    valid_dates = get_valid_dates()
    job_list_collect = []
    page_num = 1 

    # 页面加载前注入拦截脚本
    def inject_api_interceptor(driver_instance):
        driver_instance.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                window.CAPTURE_API_DATA = null;
                // 拦截 Fetch
                const rawFetch = window.fetch;
                window.fetch = async (...args) => {
                    const resp = await rawFetch(...args);
                    if(args[0].includes('pageQueryPosition')){
                        window.CAPTURE_API_DATA = await resp.clone().json();
                    }
                    return resp;
                };
                // 拦截 XHR
                const rawXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function(){
                    const xhr = new rawXHR();
                    xhr.addEventListener('load', ()=>{
                        if(xhr.responseURL.includes('pageQueryPosition')){
                            try{ window.CAPTURE_API_DATA = JSON.parse(xhr.responseText); }catch{}
                        }
                    });
                    return xhr;
                };
            """
        })

    # ========== 多页抓取循环 ==========
    inject_api_interceptor(driver)  # 首次注入
    while True:
        print(f"[小红书] 正在抓取第 {page_num} 页...")
        
        # 第一页直接访问，后续页通过点击翻页
        if page_num == 1:
            driver.get(BASE_URL)
        time.sleep(3)

        # 获取当前页API数据
        api_data = driver.execute_script("return window.CAPTURE_API_DATA")
        if not api_data or not api_data.get("success"):
            print("[小红书] API数据获取失败，终止抓取")
            break

        job_list = api_data.get("data", {}).get("list", [])
        if not job_list:
            print("[小红书] 当前页无岗位数据，终止抓取")
            break

        has_expired = False  # 标记是否遇到过期岗位

        # 校验岗位日期+收集数据
        for item in job_list:
            try:
                publish_time = convert_date(item.get("publishTime", ""))
                
                # 遇到过期岗位 → 直接终止所有抓取
                if publish_time not in valid_dates:
                    print("[小红书] 遇到过期岗位，停止全部抓取")
                    has_expired = True
                    break
                
                # 收集有效岗位
                position_id = item.get("positionId", "")
                job_info = {
                    "公司": "小红书",
                    "岗位名": item.get("positionName", ""),
                    "工作地点": item.get("workplace", ""),
                    "详情链接": f"https://job.xiaohongshu.com/social/position/{position_id}",
                    "更新时间": publish_time,
                    "岗位要求": item.get("qualification", "")
                }
                job_list_collect.append(job_info)

            except Exception:
                continue

        # 如果有过期岗位，直接退出循环
        if has_expired:
            break

        # ========== 下一页翻页逻辑 ==========
        try:
            # 精准定位可点击的下一页按钮
            next_button = driver.find_element(
                By.XPATH, 
                "//li[@title='下一页' and @aria-disabled='false']"
            )
            next_button.click()
            page_num += 1
            # 重置接口捕获变量（避免上一页数据干扰）
            driver.execute_script("window.CAPTURE_API_DATA = null;")
            # 等待新页面接口加载完成
            inject_api_interceptor(driver)
            time.sleep(3)

        # 无下一页/按钮禁用，终止循环
        except NoSuchElementException:
            print("\n🏁 已到达最后一页，抓取结束！")
            break

    # 最终过滤：排除长年限、硕士
    result = [
        job for job in job_list_collect
        if not any(k in job["岗位要求"] for k in EXCLUDE_KEYWORDS)
    ]

    driver.quit()
    return result

# if __name__ == "__main__":
#     jobs = get_filtered_xhs_jobs()
#     print(f"\n✅ 小红书抓取完成 | 符合条件岗位：{len(jobs)} 个")
#     print("-" * 80)
#     for idx, job in enumerate(jobs, 1):
#         print(f"{idx}. {job['岗位名']} | {job['工作地点']} | {job['更新时间']}")
#         print(f"链接：{job['详情链接']}\n")